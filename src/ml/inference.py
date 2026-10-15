"""inference.py - satu jalur praproses & prediksi untuk aplikasi, evaluasi, dan LIME."""
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Tuple

from lime.lime_text import LimeTextExplainer
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from src.core.config import settings
from src.utils.input_validation import (
    MAX_CHARS, MIN_WORDS, check_basic, looks_indonesian, normalize_input,
)
from src.utils.political_guardrail import check_political_domain

log = logging.getLogger("hoax.inference")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
  sys.path.insert(0, ROOT_DIR)

try:
  import text_pipeline as tp
  assert tp.PIPELINE_VERSION == "tp-1.6", (
      f"text_pipeline versi {tp.PIPELINE_VERSION}, diharapkan tp-1.6")
except Exception as e:
  raise ImportError(f"Gagal memuat text_pipeline.py tp-1.6: {e}")

# ── Konfigurasi keputusan (nilai awal; pilih aturan di set kalibrasi) ────────
DECISION_RULE = "unanimous"   # "unanimous" | "majority" | "mean"
SEEDS = [42, 123, 999]
LIME_NUM_SAMPLES = 100        # sedikit -> penjelasan bisa tidak stabil; uji stabilitas
LABEL_HOAX = "BERPOLA HOAKS"
LABEL_NOT = "TIDAK BERPOLA HOAKS"
LABEL_AMBIGU = "PERLU VERIFIKASI (AMBIGU)"
NOTE = ("Hasil menunjukkan kemiripan pola teks dengan korpus hoaks, bukan "
        "pemeriksaan fakta. Periksa teks yang dinilai dan sumber aslinya.")


class Clf(nn.Module):
  """Identik dengan colab_02_indobert.py (layer 0-7 beku, 8-11 + head dilatih)."""

  def __init__(self, model_name="indobenchmark/indobert-base-p1",
               freeze_layers=8, dropout_rate=0.3):
    super().__init__()
    self.bert = AutoModel.from_pretrained(model_name)
    for p in self.bert.embeddings.parameters():
      p.requires_grad = False
    for i in range(freeze_layers):
      for p in self.bert.encoder.layer[i].parameters():
        p.requires_grad = False
    self.drop = nn.Dropout(dropout_rate)
    self.head = nn.Linear(self.bert.config.hidden_size, 2)

  def forward(self, ids, am):
    cls_token = self.bert(input_ids=ids, attention_mask=am).last_hidden_state[:, 0, :]
    return self.head(self.drop(cls_token))


_CRITICAL_MISSING = re.compile(r"^(head\.|bert\.encoder\.layer\.(8|9|10|11)\.)")


class HoaxPredictor:

  def __init__(self):
    self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    self.model_name = getattr(settings, "MODEL_NAME_OR_PATH",
                              "indobenchmark/indobert-base-p1")
    self.max_len = 128
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
    self.models: List[nn.Module] = []
    self.loaded_seeds: List[int] = []
    self._load_ensemble_checkpoints()
    self.explainer = LimeTextExplainer(
        class_names=["TIDAK_HOAKS", "HOAKS"], split_expression=r"\W+",
        random_state=42)

  # ── Pemuatan model ────────────────────────────────────────────────────────
  def _resolve_checkpoint_paths(self) -> List[Tuple[int, str]]:
    dirs = [os.path.join(ROOT_DIR, "saved_models", "indobert_ce_final"),
            os.path.join(ROOT_DIR, "saved_models"), ROOT_DIR]
    found = []
    for sd in SEEDS:
      for d in dirs:
        p = os.path.join(d, f"ckpt_ce_{sd}.pt")
        if os.path.exists(p):
          found.append((sd, p))
          break
    return found

  def _load_ensemble_checkpoints(self):
    ckpts = self._resolve_checkpoint_paths()
    got = [s for s, _ in ckpts]
    if got != SEEDS:  # jangan diam-diam jalan dengan <3 seed
      raise FileNotFoundError(f"Seed ditemukan {got}, diharapkan {SEEDS}.")
    for seed, path in ckpts:
      m = Clf(model_name=self.model_name).to(self.device)
      state = torch.load(path, map_location=self.device)
      missing, unexpected = m.load_state_dict(state, strict=False)
      bad = [k for k in missing if _CRITICAL_MISSING.match(k)]
      if bad:  # bobot terlatih tidak termuat -> model acak, harus gagal keras
        raise RuntimeError(f"Seed {seed}: bobot terlatih hilang: {bad[:3]}")
      if unexpected:
        log.warning("Seed %s: kunci tak dikenal %s", seed, unexpected[:3])
      m.eval()
      self.models.append(m)
      self.loaded_seeds.append(seed)
    log.info("Konsensus %d seed aktif di %s", len(self.models), self.device)

  # ── Praproses (SATU jalur) ────────────────────────────────────────────────
  def clean_ocr_noise(self, text: str) -> str:
    s = str(text or "")
    s = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", s)          # "pe-\nmerintah"
    # "me- netapkan" (baris sudah digabung spasi): sambung jika lanjutan huruf kecil.
    # Pada eksperimen n=472, penyambungan tanda hubung mengembalikan akurasi ke acuan;
    # tetap verifikasi pada val sebelum dianggap aman untuk teks yang diketik pengguna.
    s = re.sub(r"(?<=\w)-\s+(?=[a-z])", "", s)
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

  def preprocess_pipeline(self, text: str) -> str:
    s = self.clean_ocr_noise(text)
    s = tp.clean(s)
    s = tp.norm_title(s, unwrap=True)
    s = tp.ensure_end(s)
    return tp.cap_sentences(s, max_words=60)

  # ── Inferensi (SATU fungsi untuk prediksi utama dan LIME) ─────────────────
  def seed_probs(self, texts: List[str]) -> np.ndarray:
    """Return array (n_seed, n_teks, 2): P[tidak hoaks, hoaks] per seed."""
    out = []
    for m in self.models:
      chunks = []
      for i in range(0, len(texts), 32):
        enc = self.tokenizer([str(t) for t in texts[i:i + 32]],
                             max_length=self.max_len, padding="max_length",
                             truncation=True, return_tensors="pt")
        with torch.no_grad():
          logits = m(enc["input_ids"].to(self.device),
                     enc["attention_mask"].to(self.device))
        chunks.append(F.softmax(logits, dim=1).cpu().numpy())
      out.append(np.concatenate(chunks, axis=0))
    return np.stack(out, axis=0)

  def _predict_proba_batch(self, texts: List[str]) -> np.ndarray:
    return self.seed_probs(texts).mean(axis=0)

  # ── Hasil terstruktur ─────────────────────────────────────────────────────
  def _result(self, status, prediction, t0, text, processed="", warning=None,
              is_political=None, entities=None, extra=None):
    r = {
        "status": status,  # dinilai | ambigu | di_luar_domain | ditolak
        "success": status in ("dinilai", "ambigu"),
        "prediction": prediction,
        "is_political": is_political,
        "domain_warning": warning,
        "inference_time_seconds": round(time.time() - t0, 2),
        "extracted_text": text if isinstance(text, str) else "",
        "processed_text": processed,
        "entities_detected": entities or [],
        "note": NOTE,
        "consensus_details": None,
        "explanation_available": False,
        "explanation": {"hoax_probability": None, "tokens": [],
                        "top_hoax_words": [], "top_fact_words": []},
    }
    if extra:
      r.update(extra)
    return r

  def predict_and_explain(self, text: str, explain: bool = True) -> Dict[str, Any]:
    t0 = time.time()
    raw = text if isinstance(text, str) else ""

    def reject(msg, processed="", status="ditolak", **kw):
      return self._result(status, "TIDAK DAPAT DINILAI", t0, raw, processed,
                          warning=msg, **kw)

    if len(raw) > MAX_CHARS:
      return reject(f"Teks terlalu panjang (>{MAX_CHARS} karakter).")

    norm, info = normalize_input(raw)
    ok, why = check_basic(norm)
    if not ok:
      return reject(why, extra={"input_flags": info})

    processed = self.preprocess_pipeline(norm)
    n_words = len(processed.split())
    if n_words < MIN_WORDS:
      return reject(f"Teks terlalu pendek ({n_words} kata; minimal {MIN_WORDS}).",
                    processed, extra={"input_flags": info})

    indo, ratio = looks_indonesian(processed)
    if not indo:
      return reject("Teks tampaknya bukan bahasa Indonesia (heuristik).",
                    processed, extra={"input_flags": info})

    is_pol, entities = check_political_domain(norm)
    if not is_pol:
      return self._result(
          "di_luar_domain", "DI LUAR DOMAIN", t0, raw, processed,
          warning="Tidak terdeteksi istilah politik; model hanya dilatih pada "
                  "korpus politik sehingga vonis tidak diberikan.",
          is_political=False, entities=entities, extra={"input_flags": info})

    sp = self.seed_probs([processed])[:, 0, :]            # (n_seed, 2)
    hoax_each = sp[:, 1]
    votes = (hoax_each >= 0.5).astype(int)
    mean_hoax = float(hoax_each.mean())
    n_hoax = int(votes.sum())
    unanimous = len(set(votes.tolist())) == 1

    if DECISION_RULE == "unanimous":
      verdict = None if not unanimous else int(votes[0])
    elif DECISION_RULE == "majority":
      verdict = int(n_hoax > len(votes) / 2)
    else:
      verdict = int(mean_hoax >= 0.5)

    if verdict is None:
      status, prediction = "ambigu", LABEL_AMBIGU
    else:
      status = "dinilai"
      prediction = LABEL_HOAX if verdict == 1 else LABEL_NOT

    # Probabilitas model ekstrem walau salah: tampilkan kesepakatan, bukan "keyakinan".
    consensus = {
        "rule": DECISION_RULE,
        "loaded_seeds": self.loaded_seeds,
        "individual_hoax_probs": [round(float(p), 4) for p in hoax_each],
        "votes_hoax": f"{n_hoax}/{len(votes)}",
        "is_unanimous": unanimous,
        "mean_hoax_probability": round(mean_hoax, 4),
        "variance": round(float(np.var(hoax_each)), 6),
    }
    res = self._result(status, prediction, t0, raw, processed,
                       is_political=True, entities=entities,
                       extra={"consensus_details": consensus, "input_flags": info})
    res["explanation"]["hoax_probability"] = round(mean_hoax, 4)

    if explain:
      try:
        exp = self.explainer.explain_instance(
            processed, self._predict_proba_batch,
            num_features=min(8, n_words), num_samples=LIME_NUM_SAMPLES)
        lime_list = exp.as_list(label=1)
        res["explanation"]["tokens"] = [
            {"word": str(w), "weight": round(float(s), 4),
             "influence": "KE_HOAKS" if s > 0 else "KE_TIDAK_HOAKS"}
            for w, s in lime_list]
        res["explanation"]["top_hoax_words"] = [
            {"word": str(w), "score": round(float(s), 4)}
            for w, s in lime_list if s > 0][:5]
        res["explanation"]["top_fact_words"] = [
            {"word": str(w), "score": round(abs(float(s)), 4)}
            for w, s in lime_list if s <= 0][:5]
        res["explanation_available"] = True
      except Exception:
        log.exception("LIME gagal untuk teks (panjang %d)", len(processed))
    res["inference_time_seconds"] = round(time.time() - t0, 2)
    return res


predictor = HoaxPredictor()