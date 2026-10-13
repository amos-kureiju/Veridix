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
from src.utils.political_guardrail import check_political_domain

# ── 1. IMPORT MODUL PIPELINE RESMI (tp-1.6) ──────────────────────────────────
# Resolusi path agar text_pipeline.py bisa dimuat dari root proyek
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
  sys.path.insert(0, ROOT_DIR)

try:
  import text_pipeline as tp

  assert (
      tp.PIPELINE_VERSION == "tp-1.6"
  ), f"text_pipeline versi {tp.PIPELINE_VERSION}, diharapkan tp-1.6"
except Exception as e:
  raise ImportError(
      f"Gagal memuat modul text_pipeline.py versi tp-1.6: {e}. Pastikan file ada"
      " di root proyek."
  )


# ── 2. ARSITEKTUR MODEL RESMI SESUAI COLAB 02 ───────────────────────────────
class Clf(nn.Module):
  """Arsitektur klasifikasi IndoBERT identik dengan colab_02_indobert.py.

  Embedding dan layer 0-7 dibekukan, layer 8-11 + Classification Head
  terlatih.
  """

  def __init__(
      self,
      model_name: str = "indobenchmark/indobert-base-p1",
      freeze_layers: int = 8,
      dropout_rate: float = 0.3,
  ):
    super().__init__()
    self.bert = AutoModel.from_pretrained(model_name)

    # Bekukan embeddings dan layer 0-7
    for p in self.bert.embeddings.parameters():
      p.requires_grad = False
    for i in range(freeze_layers):
      for p in self.bert.encoder.layer[i].parameters():
        p.requires_grad = False

    self.drop = nn.Dropout(dropout_rate)
    self.head = nn.Linear(self.bert.config.hidden_size, 2)

  def forward(self, ids, am):
    cls_token = self.bert(input_ids=ids, attention_mask=am).last_hidden_state[
        :, 0, :
    ]
    return self.head(self.drop(cls_token))


# ── 3. PREDICTOR DENGAN KONSENSUS 3 SEED & LIME ───────────────────────────────
class HoaxPredictor:

  def __init__(self):
    self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    self.model_name = getattr(
        settings, "MODEL_NAME_OR_PATH", "indobenchmark/indobert-base-p1"
    )
    self.max_len = 128  # Sesuai konfigurasi terkunci Colab 02

    print(
        f"--> [AI Core] Inisialisasi Tokenizer IndoBERT: {self.model_name}..."
    )
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    # 1. Muat Ansambel Model (3 Seed: 42, 123, 999)
    self.models: List[nn.Module] = []
    self.loaded_seeds: List[int] = []
    self._load_ensemble_checkpoints()

    # 2. Inisialisasi Mesin LIME
    print(
        "--> [AI Core] Menginisialisasi Mesin LIME Text Explainer"
        " (Reproducible)..."
    )
    self.explainer = LimeTextExplainer(
        class_names=["FAKTA", "HOAKS"],
        split_expression=r"\W+",
        random_state=42,
    )

  def _resolve_checkpoint_paths(self) -> List[Tuple[int, str]]:
    """Mencari lokasi ketiga file checkpoint ckpt_ce_*.pt di saved_models/ atau root."""
    seeds = [42, 123, 999]
    found = []

    search_dirs = [
        os.path.join(ROOT_DIR, "saved_models", "indobert_ce_final"),
        os.path.join(ROOT_DIR, "saved_models"),
        ROOT_DIR,
    ]

    for sd in seeds:
      filename = f"ckpt_ce_{sd}.pt"
      for d in search_dirs:
        p = os.path.join(d, filename)
        if os.path.exists(p):
          found.append((sd, p))
          break

    return found

  def _load_ensemble_checkpoints(self):
    """Memuat bobot checkpoint parsial menggunakan strict=False."""
    ckpt_list = self._resolve_checkpoint_paths()

    if not ckpt_list:
      raise FileNotFoundError(
          "Tidak ditemukan berkas checkpoint ckpt_ce_*.pt di root maupun di"
          " saved_models/indobert_ce_final/!"
      )

    print(
        f"--> [AI Core] Menemukan {len(ckpt_list)} checkpoint model untuk"
        " konsensus ansambel:"
    )
    for seed, path in ckpt_list:
      print(f"    - Memuat seed {seed} dari: {path}")
      m = Clf(model_name=self.model_name).to(self.device)
      state_dict = torch.load(path, map_location=self.device)

      # strict=False wajib digunakan karena checkpoint hanya menyimpan layer 8-11 + head
      missing, unexpected = m.load_state_dict(state_dict, strict=False)
      if unexpected:
        print(f"      [Peringatan] Kunci tensor tak dikenal: {unexpected[:3]}")

      m.eval()
      self.models.append(m)
      self.loaded_seeds.append(seed)

    print(
        f"✅ [AI Core] Berhasil mengaktifkan konsensus {len(self.models)} seed"
        f" IndoBERT di perangkat: {self.device}"
    )

  def clean_ocr_noise(self, text: str) -> str:
    """Standardisasi pembersihan derau khas hasil ekstraksi PaddleOCR."""
    if not text:
      return ""

    s = str(text)
    # 1. Sambungkan kata yang terpotong tanda hubung di ujung baris: "pe- merintah" -> "pemerintah"
    s = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", s)

    # 2. Ganti pemisah baris dan tab acak menjadi satu spasi
    s = re.sub(r"[\r\n\t]+", " ", s)

    # 3. Hilangkan karakter derau non-standar/glitch OCR
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", s)

    # 4. Rapikan spasi ganda
    s = re.sub(r"\s+", " ", s).strip()
    return s

  def preprocess_pipeline(self, text: str) -> str:
    """Pra-pemrosesan teks terpadu menggunakan modul resmi text_pipeline.py (tp-1.6)."""
    # 1. Bersihkan derau OCR dasar
    s = self.clean_ocr_noise(text)

    # 2. Terapkan pembersihan resmi pipeline
    s = tp.clean(s)

    # 3. Normalisasi deskriptor editorial Mafindo & tanda kutip pembungkus
    s = tp.norm_title(s, unwrap=True)

    # 4. Pastikan teks diakhiri tanda baca titik baku
    s = tp.ensure_end(s)

    # 5. Pembatasan panjang kalimat setara ambang latihan (maksimal 60 kata)
    s = tp.cap_sentences(s, max_words=60)
    return s

  def _predict_proba_batch(self, texts: List[str]) -> np.ndarray:
    """Fungsi batch inferensi konsensus ansambel untuk kalkulasi LIME."""
    batch_size = 32
    n_samples = len(texts)
    ensemble_probs = np.zeros((n_samples, 2), dtype=np.float32)

    for i in range(0, n_samples, batch_size):
      batch_texts = [str(t) for t in texts[i : i + batch_size]]

      enc = self.tokenizer(
          batch_texts,
          max_length=self.max_len,
          padding="max_length",
          truncation=True,
          return_tensors="pt",
      )
      ids = enc["input_ids"].to(self.device)
      am = enc["attention_mask"].to(self.device)

      # Rata-ratakan probabilitas dari seluruh model seed yang aktif
      batch_model_probs = []
      with torch.no_grad():
        for m in self.models:
          logits = m(ids, am)
          probs = F.softmax(logits, dim=1).cpu().numpy()
          batch_model_probs.append(probs)

      # Rerata lintas model
      avg_batch_prob = np.mean(batch_model_probs, axis=0)
      ensemble_probs[i : i + batch_size] = avg_batch_prob

    return ensemble_probs

  def predict_and_explain(self, text: str) -> Dict[str, Any]:
    """Eksekusi inferensi lengkap: Guardrail -> Pipeline tp-1.6 -> Triangulasi 3 Seed -> LIME."""
    start_time = time.time()

    # 1. Guardrail Domain Politik
    is_political, entities = check_political_domain(text)

    # 2. Pra-pemrosesan Terpadu sesuai Standar Pelatihan tp-1.6
    processed_text = self.preprocess_pipeline(text)

    # 3. Inferensi Multi-Seed (Kalkulasi Konsensus)
    enc = self.tokenizer(
        [processed_text],
        max_length=self.max_len,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    ids = enc["input_ids"].to(self.device)
    am = enc["attention_mask"].to(self.device)

    seed_probs = []
    with torch.no_grad():
      for m in self.models:
        logits = m(ids, am)
        prob = F.softmax(logits, dim=1).cpu().numpy()[0]
        seed_probs.append(prob)

    # Rata-rata probabilitas ansambel konsensus
    avg_prob = np.mean(seed_probs, axis=0)
    hoax_prob = float(avg_prob[1])
    fact_prob = float(avg_prob[0])

    pred_label = 1 if hoax_prob >= 0.5 else 0
    prediction = "HOAX" if pred_label == 1 else "FACT"
    confidence = hoax_prob if pred_label == 1 else fact_prob

    # Periksa kesepakatan antar-seed (Consensus Agreement)
    seed_votes = [1 if p[1] >= 0.5 else 0 for p in seed_probs]
    unanimous = len(set(seed_votes)) == 1

    # 4. Penjelasan LIME Text Explainer (50-100 Sampel Perturbasi)
    exp = self.explainer.explain_instance(
        processed_text,
        self._predict_proba_batch,
        num_features=8,
        num_samples=100,
    )

    lime_list = exp.as_list(label=1)
    tokens_explanation = [
        {
            "word": str(w),
            "weight": round(float(sc), 4),
            "influence": "HOAX" if sc > 0 else "FACT",
        }
        for w, sc in lime_list
    ]

    top_hoax = [
        {"word": str(w), "score": round(float(sc), 4)}
        for w, sc in lime_list
        if sc > 0
    ][:5]
    top_fact = [
        {"word": str(w), "score": round(abs(float(sc)), 4)}
        for w, sc in lime_list
        if sc <= 0
    ][:5]

    elapsed_time = round(time.time() - start_time, 2)

    return {
        "is_political": is_political,
        "prediction": prediction,
        "confidence_score": round(confidence, 4),
        "consensus_details": {
            "loaded_seeds": self.loaded_seeds,
            "individual_hoax_probs": [round(float(p[1]), 4) for p in seed_probs],
            "is_unanimous": unanimous,
            "variance": round(float(np.var([p[1] for p in seed_probs])), 6),
        },
        "domain_warning": (
            None
            if is_political
            else (
                "Peringatan: Teks terdeteksi di luar domain politik Indonesia."
                " Model dilatih khusus pada korpus klaim politik."
            )
        ),
        "inference_time_seconds": elapsed_time,
        "extracted_text": text,
        "processed_text": processed_text,
        "entities_detected": entities,
        "explanation": {
            "hoax_probability": round(hoax_prob, 4),
            "fact_probability": round(fact_prob, 4),
            "tokens": tokens_explanation,
            "top_hoax_words": top_hoax,
            "top_fact_words": top_fact,
        },
    }


# Inisialisasi instance tunggal untuk FastAPI
predictor = HoaxPredictor()