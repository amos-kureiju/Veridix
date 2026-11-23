"""
src/ml/inference.py — jalur inferensi aplikasi (versi final yang dapat diuji).

Struktur:
  Penilai            : orkestrasi murni Python (validasi -> domain -> praproses -> suara per seed -> keputusan -> LIME).
                       Tidak butuh torch, jadi dapat diuji dengan backend tiruan.
  BackendIndoBERT    : satu model dasar + tiga keadaan terlatih (layer 8-11, pooler, kepala) yang ditukar per seed.
                       Memuat hanya SATU salinan model dasar (memuat tiga sekaligus pernah menyebabkan 'bad allocation'). """
import hashlib
import json
import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.utils.input_validation import validate_input_text  # noqa: E402
from src.utils.political_guardrail import check_political_domain  # noqa: E402
from src.utils.praproses import praproses, MAX_WORDS, sambung_tanda_hubung  # noqa: E402
import text_pipeline as tp  # noqa: E402

MODEL_NAME = "indobenchmark/indobert-base-p1"
SEEDS = [42, 123, 999]
MAX_LEN, BATCH = 128, 32
DOCUMENT_CPU_BATCH = 4  # Batasi memori aktivasi saat LIME menilai banyak variasi segmen.

# Dicatat dari keluaran Anda sendiri (verifikasi_ckpt_lokal.py dan log pembekuan).
EXPECTED_SHA256 = {
    42: "308b3e399eb5a5d7cd8c610c6c4c4805d07912fe003009300670b0ccd7dd750f",
    123: "afc650aa29e8e07312a960aebef10af3d2f15bb4f970296b40ed2fcd26bee733",
    999: "7883c1b70656d0bbf5bf9a41aa9825577ff419ed7b4ca45610a82e8246c76ed3",
}
EXPECTED_PIPELINE_SHA256 = "83dd3ee5188e3bc8c6faee3be50083eb2054be57102bb7abd43e71b52d3b2581"
EXPECTED_BASE_REVISION = "c2cd0b51ddce6580eb35263b39b0a1e5fb0a39e2"

DECISION_RULE = os.environ.get("VERIDIX_DECISION_RULE", "unanimous")   # unanimous | majority
LIME_NUM_SAMPLES = int(os.environ.get("VERIDIX_LIME_SAMPLES", "200"))
_DOCUMENT_LIME_POLICY = "segment-source-v1"

DISCLAIMER = ("Sistem mendeteksi kemiripan pola penulisan klaim yang pernah dilabeli hoaks oleh pemeriksa fakta; "
              "ia bukan pemverifikasi kebenaran. Hasil pada teks hasil OCR yang berderau kurang andal.")
LIME_CATATAN = ("Penjelasan LIME bersifat indikatif: ia menunjukkan kata yang memengaruhi keluaran model, "
                "bukan bukti bahwa kata itu benar atau salah.")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest().lower()


def _load_pretrained(loader, **kwargs):
    """Utamakan cache revisi beku; unduh revisi yang sama bila cache belum lengkap."""
    try:
        return loader.from_pretrained(
            MODEL_NAME, revision=EXPECTED_BASE_REVISION, local_files_only=True, **kwargs
        )
    except OSError:
        return loader.from_pretrained(
            MODEL_NAME, revision=EXPECTED_BASE_REVISION, local_files_only=False, **kwargs
        )


def putuskan(votes_hoax: int, n: int, rule: str = DECISION_RULE):
    """Kembalikan (status, label)."""
    if rule == "unanimous":
        if votes_hoax == n:
            return "dinilai", "BERPOLA HOAKS"
        if votes_hoax == 0:
            return "dinilai", "TIDAK BERPOLA HOAKS"
        return "ambigu", "PERLU VERIFIKASI (SEED TIDAK SEPAKAT)"
    if rule == "majority":
        return "dinilai", ("BERPOLA HOAKS" if votes_hoax * 2 > n else "TIDAK BERPOLA HOAKS")
    raise ValueError(f"aturan keputusan tidak dikenal: {rule}")


def validate_claim_result(result: dict) -> None:
    """Periksa kontrak klaim yang dipakai API dan evaluator penelitian."""
    if not isinstance(result, dict):
        raise ValueError("Keluaran inferensi bukan objek.")

    latency = result.get("latency_seconds")
    if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
        raise ValueError("Latensi inferensi tidak sah.")

    process_status = result.get("status")
    if process_status in ("ditolak", "di_luar_domain"):
        reason = result.get("reason")
        if (
            result.get("success") is not False
            or not isinstance(reason, str)
            or not reason.strip()
            or any(result.get(field) is not None for field in ("votes_hoax", "seed_decisions", "agreement_ratio"))
        ):
            raise ValueError("Keluaran penolakan inferensi tidak sah.")
        return

    if process_status not in ("dinilai", "ambigu") or result.get("success") is not True:
        raise ValueError("Status hasil inferensi tidak sah.")

    decisions = result.get("seed_decisions")
    if (
        not isinstance(decisions, dict)
        or decisions.keys() != set(SEEDS)
        or any(type(seed) is not int or type(vote) is not int or vote not in (0, 1) for seed, vote in decisions.items())
    ):
        raise ValueError("Keputusan per seed tidak sah.")

    votes = sum(decisions.values())
    n = len(SEEDS)
    if (process_status, result.get("label")) != putuskan(votes, n, result.get("decision_rule")):
        raise ValueError("Status atau label tidak sesuai aturan voting.")

    agreement = result.get("agreement_ratio")
    if (
        result.get("votes_hoax") != f"{votes}/{n}"
        or type(agreement) not in (int, float)
        or agreement != max(votes, n - votes) / n
    ):
        raise ValueError("Jumlah suara atau rasio kesepakatan tidak sesuai keputusan seed.")


def _pemotongan_kata(text: str, sambung: bool) -> Optional[bool]:
    """Diagnostik batas kata setelah pembersihan, tanpa mengubah masukan model."""
    try:
        cleaned = tp.clean(text)
        if sambung:
            cleaned = sambung_tanda_hubung(cleaned)
        if not cleaned:
            return False
        return len(tp.ensure_end(cleaned).split()) > MAX_WORDS
    except Exception:
        return None


class Penilai:
    """Orkestrasi murni Python. backend.seed_probs_each(list[str]) -> array (n_teks, n_seed) berisi P(hoaks)."""

    def __init__(self, backend, decision_rule: str = DECISION_RULE, sambung_tanda_hubung: bool = False):
        self.backend = backend
        self.rule = decision_rule
        self.sambung = sambung_tanda_hubung
        self._explainer = None

    # -- hasil penolakan yang seragam -------------------------------------------------
    def _tolak(self, status, label, reason, t0, **extra):
        d = {"success": False, "status": status, "label": label, "reason": reason,
             "disclaimer": DISCLAIMER, "latency_seconds": round(time.time() - t0, 3)}
        d.update(extra)
        return d

    def _mean_probs(self, texts) -> np.ndarray:
        p = self.backend.seed_probs_each(list(texts)).mean(axis=1)
        return np.column_stack([1.0 - p, p])

    def _document_token_count(self, text: str) -> int:
        count = self.backend.count_tokens(text)
        if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or not 1 <= count <= MAX_LEN:
            raise ValueError("Jumlah token segmen tidak valid.")
        return int(count)

    def _mean_document_probs(self, texts) -> np.ndarray:
        variants = list(texts)
        counts = [self._document_token_count(text) for text in variants]
        scores = np.asarray(self.backend.seed_probs_each_untruncated(variants, counts))
        n_seeds = len(self.backend.seeds)
        if (
            not n_seeds or scores.shape != (len(variants), n_seeds)
            or scores.dtype.kind not in "iuf"
            or not np.all(np.isfinite(scores) & (scores >= 0) & (scores <= 1))
        ):
            raise ValueError("Skor model untuk penjelasan segmen tidak valid.")
        p = scores.mean(axis=1)
        return np.column_stack([1.0 - p, p])

    @staticmethod
    def _empty_lime() -> Dict[str, Any]:
        return {"explanation_available": False, "tokens": [], "catatan": LIME_CATATAN,
                "num_samples": LIME_NUM_SAMPLES}

    def _lime(self, text: str, *, document: bool = False) -> Dict[str, Any]:
        out = self._empty_lime()
        try:
            # Segmen memakai RNG sendiri agar permintaan naskah tidak mengubah urutan sampel jalur singkat.
            explainer = None if document else self._explainer
            if explainer is None:
                from lime.lime_text import LimeTextExplainer
                explainer = LimeTextExplainer(class_names=["TIDAK_HOAKS", "HOAKS"], split_expression=r"\W+",
                                              random_state=42)
                if not document:
                    self._explainer = explainer
            n_uniq = len(set(text.lower().split()))
            mean_probs = self._mean_document_probs if document else self._mean_probs
            exp = explainer.explain_instance(text, mean_probs, labels=(1,), num_features=max(1, min(8, n_uniq)),
                                             num_samples=LIME_NUM_SAMPLES)
            weights = exp.as_list(label=1)
            if document and (
                not weights or any(
                    not isinstance(word, str) or not word.strip()
                    or isinstance(weight, (bool, np.bool_)) or not np.isfinite(weight)
                    for word, weight in weights
                )
            ):
                raise ValueError("Bobot penjelasan segmen tidak valid.")
            tokens = [{"word": str(w), "weight": round(float(s), 4),
                       "influence": "KE_HOAKS" if s > 0 else "KE_TIDAK_HOAKS"} for w, s in weights]
            out["tokens"] = tokens
            out["top_hoax_words"] = [{"word": t["word"], "score": t["weight"]} for t in tokens if t["weight"] > 0]
            out["top_fact_words"] = [{"word": t["word"], "score": abs(t["weight"])} for t in tokens if t["weight"] < 0]
            out["teks_dijelaskan"] = text
            out["diagnostik"] = self._diagnostik_lime(exp)
            out["explanation_available"] = True
        except Exception as e:  # penjelasan gagal tidak boleh menggagalkan vonis
            out["error"] = "Penjelasan segmen gagal dibuat." if document else f"{type(e).__name__}: {e}"
        return out

    @staticmethod
    def _diagnostik_lime(exp) -> Dict[str, Any]:
        """Ukuran kesetiaan lokal LIME. Nilai tidak tersedia = None (bukan 0)."""
        def _ambil(fn):
            try:
                v = fn()
                if v is None:
                    return None
                v = float(v)
                # NaN/Inf bukan angka JSON yang valid: tidak tersedia = None, bukan 0
                return round(v, 5) if np.isfinite(v) else None
            except Exception:
                return None

        def _score():
            s = getattr(exp, "score", None)
            return s.get(1) if isinstance(s, dict) else s

        return {
            "local_r2": _ambil(_score),                                   # kecocokan model linear lokal (bukan akurasi)
            "intercept": _ambil(lambda: exp.intercept[1]),
            "local_prediction": _ambil(lambda: exp.local_pred[0]),        # prediksi pendekatan lokal untuk teks asli
        }

    def siapkan_teks(self, text: Any) -> Optional[str]:
        """Teks praproses sebelum batas tokenizer; None bila tidak layak."""
        v = validate_input_text(text)
        if not v["ok"]:
            return None
        x = praproses(v["text"], self.sambung)
        return x if x and len(x.split()) >= 10 else None

    def explain_text(self, text: Any) -> Dict[str, Any]:
        x = self.siapkan_teks(text)
        if x is None:
            return {**self._empty_lime(), "error": "Teks tidak layak untuk dijelaskan."}
        return self._lime(x)

    def document_model_identity(self) -> Optional[str]:
        """Ikat penjelasan sesi ke konfigurasi dan checkpoint aktif yang terverifikasi."""
        audit = getattr(self.backend, "audit", None)
        if not isinstance(audit, dict) or getattr(self.backend, "allow_unverified", True):
            return None
        if (
            list(self.backend.seeds) != SEEDS
            or audit.get("base_revision") != EXPECTED_BASE_REVISION
            or audit.get("text_pipeline_sha256") != EXPECTED_PIPELINE_SHA256
            or any(audit.get(f"sha256_seed_{seed}") != EXPECTED_SHA256[seed] for seed in SEEDS)
        ):
            return None
        identity = {
            "policy": _DOCUMENT_LIME_POLICY,
            "model": MODEL_NAME,
            "base_revision": audit["base_revision"],
            "pipeline_sha256": audit["text_pipeline_sha256"],
            "checkpoint_sha256": [audit[f"sha256_seed_{seed}"] for seed in SEEDS],
            "rule": self.rule,
            "max_len": MAX_LEN,
            "max_words": MAX_WORDS,
            "lime_samples": LIME_NUM_SAMPLES,
            "cpu_batch": DOCUMENT_CPU_BATCH,
        }
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()

    def explain_document_segment(self, text: str, token_count: int) -> Dict[str, Any]:
        """Jelaskan teks sumber yang sudah dinilai tanpa praproses atau pemotongan tambahan."""
        unavailable = {**self._empty_lime(), "error": "Teks segmen tidak cocok dengan tokenisasi model."}
        if not isinstance(text, str) or not 1 <= len(text.split()) <= MAX_WORDS or type(token_count) is not int:
            return unavailable
        try:
            measured = self._document_token_count(text)
            if measured != token_count or measured <= self._document_token_count(""):
                return unavailable
        except Exception:
            return unavailable
        return self._lime(text, document=True)

    def nilai(self, text: Any, explain: bool = False, debug: bool = False) -> Dict[str, Any]:
        t0 = time.time()
        v = validate_input_text(text)
        if not v["ok"]:
            return self._tolak("ditolak", "TIDAK DAPAT DINILAI", v["reason"], t0, input_flags=v["flags"])

        in_domain, topik, terms = check_political_domain(v["text"])     # pada teks PENUH, seperti saat korpus dibangun
        if not in_domain:
            return self._tolak("di_luar_domain", "DI LUAR CAKUPAN (BUKAN TOPIK POLITIK)",
                               "Teks di luar topik politik yang dipakai melatih sistem.", t0,
                               sub_topik=topik, istilah=terms, input_flags=v["flags"])

        x = praproses(v["text"], self.sambung)
        n_kata_praproses = len(x.split()) if x else 0

        # 1. PENGAMAN TEKS URL/DERAU: Tolak jika teks memendek (< 10 kata) setelah pembersihan URL/karakter
        if not x or n_kata_praproses < 10:
            return self._tolak("ditolak", "TIDAK DAPAT DINILAI",
                               f"Teks kosong atau terlalu sedikit kata setelah pembersihan URL ({n_kata_praproses} kata < 10).",
                               t0, sub_topik=topik, istilah=terms, input_flags=v["flags"])

        # 2. PENGAMAN BATCH & NUMERIK (Tandai status "gagal" untuk anomali mesin AI, bukan penolakan naskah)
        raw_res = self.backend.seed_probs_each([x])
        if raw_res is None or len(raw_res) == 0:
            return self._tolak("gagal", "TIDAK DAPAT DINILAI", "Galat backend: keluaran inferensi kosong.",
                               t0, sub_topik=topik, istilah=terms, input_flags=v["flags"])

        probs = np.asarray(raw_res[0], dtype=float)
        n_seeds = len(getattr(self.backend, "seeds", []))

        # Cek: jumlah seed > 0, dimensi cocok, bebas NaN/Inf (np.isfinite), dan probabilitas wajib [0.0, 1.0]
        if n_seeds == 0 or len(probs) != n_seeds or not np.all(np.isfinite(probs)) or np.any(probs < 0.0) or np.any(probs > 1.0):
            return self._tolak("gagal", "TIDAK DAPAT DINILAI",
                               "Galat komputasi model (probabilitas memuat NaN/Inf, di luar [0,1], atau jumlah seed tidak sesuai).",
                               t0, sub_topik=topik, istilah=terms, input_flags=v["flags"])

        # 3. KEPUTUSAN BINER PER SEED: Murni 0 atau 1 sebelum pembulatan desimal
        seed_decisions = {s: int(probs[j] >= 0.5) for j, s in enumerate(self.backend.seeds)}
        votes = sum(seed_decisions.values())
        status, label = putuskan(votes, n_seeds, self.rule)

        # 4. KONSENSUS ENSEMBLE: Kesepakatan mayoritas seed dengan presisi penuh
        agreement_ratio = max(votes, n_seeds - votes) / n_seeds

        # 5. Diagnostik saja: kegagalan pengukuran tidak mengubah hasil klasifikasi.
        terpotong_kata = _pemotongan_kata(v["text"], self.sambung)
        terpotong_token: Optional[bool] = None

        # Backend aktif menghitung token di bawah lock yang sama dengan inferensi.
        try:
            count_tokens = getattr(self.backend, "count_tokens", None)
            if callable(count_tokens):
                n_tokens = count_tokens(x)
                if (
                    isinstance(n_tokens, (int, np.integer))
                    and not isinstance(n_tokens, (bool, np.bool_))
                    and n_tokens >= 0
                ):
                    terpotong_token = bool(n_tokens > MAX_LEN)
        except Exception:
            terpotong_token = None

        if terpotong_kata is True or terpotong_token is True:
            terpotong: Optional[bool] = True
        elif terpotong_kata is False and terpotong_token is False:
            terpotong = False
        else:
            terpotong = None

        res = {
            "success": True,
            "status": status,
            "label": label,
            "votes_hoax": f"{votes}/{n_seeds}",
            "agreement_ratio": agreement_ratio,
            "decision_rule": self.rule,
            "seed_decisions": seed_decisions,
            "sub_topik": topik,
            "istilah": terms,
            "teks_dinilai": x,
            "terpotong": terpotong,
            "input_flags": v["flags"],
            "disclaimer": DISCLAIMER,
        }
        if explain:
            res["explanation"] = self._lime(x)
        if debug:
            res["debug"] = {
                "prob_hoax_per_seed": {s: round(float(probs[j]), 6) for j, s in enumerate(self.backend.seeds)},
                "mean_prob_hoax": round(float(probs.mean()), 6),
                "pemotongan": {
                    "terpotong_kata": terpotong_kata,
                    "terpotong_token": terpotong_token,
                    "max_words": MAX_WORDS,
                    "max_len_tokens": MAX_LEN
                }
            }
        res["latency_seconds"] = round(time.time() - t0, 3)
        return res

class BackendIndoBERT:
    """Satu model dasar; keadaan terlatih tiap seed ditukar saat inferensi. Gagal keras bila integritas tidak cocok."""

    def __init__(self, seeds: Optional[List[int]] = None):
        # Transformers 5.17 dapat mengonversi .bin di latar walau use_safetensors=False.
        # Matikan konversi opsional, tanpa menonaktifkan unduhan untuk instalasi baru.
        os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")
        import torch
        import torch.nn as nn
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.seeds = list(seeds or SEEDS)
        self.allow_unverified = os.environ.get("VERIDIX_ALLOW_UNVERIFIED") == "1"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._lock = threading.Lock()
        self.audit: Dict[str, Any] = {}

        self._cek_pipeline()
        self.tokenizer = _load_pretrained(AutoTokenizer)
        self.clf = self._bangun(nn, AutoModel).to(self.device).eval()
        self._cek_revisi_model_dasar()
        self.states = {s: self._muat(s) for s in self.seeds}

    # -- integritas -----------------------------------------------------------------
    def _gagal(self, pesan: str):
        if self.allow_unverified:
            print(f"[PERINGATAN] {pesan} (dilewati karena VERIDIX_ALLOW_UNVERIFIED=1)")
        else:
            raise RuntimeError(f"INTEGRITAS GAGAL: {pesan}")

    def _cek_pipeline(self):
        import text_pipeline as tp
        h = sha256_file(ROOT_DIR / "text_pipeline.py")
        self.audit["text_pipeline_sha256"] = h
        if tp.PIPELINE_VERSION != "tp-1.6" or h != EXPECTED_PIPELINE_SHA256:
            self._gagal(f"text_pipeline.py tidak sama dengan berkas beku (versi={tp.PIPELINE_VERSION}, sha={h[:12]}...)")

    def _cek_revisi_model_dasar(self):
        rev = getattr(self.clf.bert.config, "_commit_hash", None)
        self.audit["base_revision"] = rev
        if rev != EXPECTED_BASE_REVISION:
            self._gagal(f"revisi model dasar {rev} != {EXPECTED_BASE_REVISION}")

    @staticmethod
    def _bangun(nn, AutoModel):
        class Clf(nn.Module):                      # identik dengan colab_02_indobert.py
            def __init__(self):
                super().__init__()
                self.bert = _load_pretrained(AutoModel, use_safetensors=False)
                for p in self.bert.embeddings.parameters():
                    p.requires_grad = False
                for i in range(8):
                    for p in self.bert.encoder.layer[i].parameters():
                        p.requires_grad = False
                self.drop = nn.Dropout(0.3)
                self.head = nn.Linear(self.bert.config.hidden_size, 2)

            def forward(self, ids, am):
                return self.head(self.drop(self.bert(input_ids=ids, attention_mask=am).last_hidden_state[:, 0, :]))
        return Clf()

    def _muat(self, seed: int):
        nama = f"ckpt_ce_{seed}.pt"
        path = next((d / nama for d in (ROOT_DIR / "saved_models" / "indobert_ce_final", ROOT_DIR / "saved_models", ROOT_DIR)
                     if (d / nama).exists()), None)
        if path is None:
            raise FileNotFoundError(f"FATAL: {nama} tidak ditemukan. Ketiga seed wajib ada.")
        h = sha256_file(path)
        self.audit[f"sha256_seed_{seed}"] = h
        if h != EXPECTED_SHA256[seed]:
            self._gagal(f"hash {nama} tidak cocok ({h[:12]}... != {EXPECTED_SHA256[seed][:12]}...)")
        sd = self.torch.load(path, map_location="cpu", weights_only=True)
        harapan = {n for n, p in self.clf.named_parameters() if p.requires_grad}
        if set(sd.keys()) != harapan:
            raise ValueError(f"FATAL: kunci {nama} tidak sama dengan parameter yang dilatih "
                             f"(kurang={len(harapan - set(sd))}, lebih={len(set(sd) - harapan)})")
        return sd

    # -- inferensi ------------------------------------------------------------------
    # -- Tambahkan helper method thread-safe ini di dalam BackendIndoBERT --
    def count_tokens(self, text: str) -> Optional[int]:
        """Menghitung jumlah token sub-kata secara thread-safe."""
        try:
            with self._lock:
                return len(self.tokenizer.encode(str(text), add_special_tokens=True, truncation=False))
        except Exception:
            return None

    def seed_probs_each(self, texts: List[str]) -> np.ndarray:
        return self._seed_probs_each(texts)

    def seed_probs_each_untruncated(self, texts: List[str], token_counts: List[int]) -> np.ndarray:
        """Nilai segmen persis seperti dicek, tanpa pemotongan tokenizer."""
        return self._seed_probs_each(texts, expected_tokens=token_counts)

    def _seed_probs_each(
        self, texts: List[str], expected_tokens: Optional[List[int]] = None,
    ) -> np.ndarray:
        torch = self.torch
        texts = [str(t) for t in texts]
        out = np.zeros((len(texts), len(self.seeds)), dtype=np.float64)

        with self._lock:
            enc = self.tokenizer(
                texts, max_length=MAX_LEN, padding="max_length",
                truncation=expected_tokens is None, return_tensors="pt",
            )
            if expected_tokens is not None:
                shape = (len(texts), MAX_LEN)
                if (
                    enc["input_ids"].shape != shape
                    or enc["attention_mask"].shape != shape
                    or enc["attention_mask"].sum(dim=1).tolist() != expected_tokens
                ):
                    raise ValueError("Tokenisasi batch tidak sesuai dengan pemeriksaan segmen.")
            batch_size = DOCUMENT_CPU_BATCH if expected_tokens is not None and str(self.device) == "cpu" else BATCH
            with torch.no_grad():
                for j, s in enumerate(self.seeds):
                    self.clf.load_state_dict(self.states[s], strict=False)
                    for i in range(0, len(texts), batch_size):
                        ids = enc["input_ids"][i:i + batch_size].to(self.device)
                        am = enc["attention_mask"][i:i + batch_size].to(self.device)
                        p = torch.softmax(self.clf(ids, am), dim=1)[:, 1].cpu().numpy()
                        out[i:i + len(p), j] = p
        return out
    
_PRED = None
_PRED_LOCK = threading.Lock()


def get_predictor() -> Penilai:
    global _PRED
    with _PRED_LOCK:
        if _PRED is None:
            _PRED = Penilai(BackendIndoBERT(), decision_rule=DECISION_RULE)
    return _PRED


class _LazyPredictor:
    """Kompatibel dengan pemanggil lama (predictor.predict_and_explain), tetapi model baru dimuat saat pertama dipakai."""

    def predict_and_explain(self, text, explain: bool = True, debug: bool = False):
        return get_predictor().nilai(text, explain=explain, debug=debug)

    def explain(self, text):
        return get_predictor().explain_text(text)


predictor = _LazyPredictor()
