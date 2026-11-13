"""
src/ml/inference.py — jalur inferensi aplikasi (versi final yang dapat diuji).

Struktur:
  Penilai            : orkestrasi murni Python (validasi -> domain -> praproses -> suara per seed -> keputusan -> LIME).
                       Tidak butuh torch, jadi dapat diuji dengan backend tiruan.
  BackendIndoBERT    : satu model dasar + tiga keadaan terlatih (layer 8-11, pooler, kepala) yang ditukar per seed.
                       Memuat hanya SATU salinan model dasar (memuat tiga sekaligus pernah menyebabkan 'bad allocation'). """
import hashlib
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
from src.utils.praproses import praproses, MAX_WORDS  # noqa: E402

MODEL_NAME = "indobenchmark/indobert-base-p1"
SEEDS = [42, 123, 999]
MAX_LEN, BATCH = 128, 32

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

    def _lime(self, text: str) -> Dict[str, Any]:
        out = {"explanation_available": False, "tokens": [], "catatan": LIME_CATATAN,
               "num_samples": LIME_NUM_SAMPLES}
        try:
            if self._explainer is None:
                from lime.lime_text import LimeTextExplainer
                self._explainer = LimeTextExplainer(class_names=["TIDAK_HOAKS", "HOAKS"], split_expression=r"\W+",
                                                    random_state=42)
            n_uniq = len(set(text.lower().split()))
            exp = self._explainer.explain_instance(text, self._mean_probs, labels=(1,), num_features=max(1, min(8, n_uniq)),
                                                   num_samples=LIME_NUM_SAMPLES)
            out["tokens"] = [{"word": str(w), "weight": round(float(s), 4),
                              "influence": "KE_HOAKS" if s > 0 else "KE_TIDAK_HOAKS"} for w, s in exp.as_list(label=1)]
            out["diagnostik"] = self._diagnostik_lime(exp)
            out["explanation_available"] = True
        except Exception as e:  # penjelasan gagal tidak boleh menggagalkan vonis
            out["error"] = f"{type(e).__name__}: {e}"
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
        """Teks hasil praproses yang persis dinilai model; None bila tidak layak."""
        v = validate_input_text(text)
        if not v["ok"]:
            return None
        x = praproses(v["text"], self.sambung)
        return x if x and len(x.split()) >= 10 else None

    def explain_text(self, text: Any) -> Dict[str, Any]:
        x = self.siapkan_teks(text)
        if x is None:
            return {"explanation_available": False, "tokens": [], "catatan": LIME_CATATAN,
                    "num_samples": LIME_NUM_SAMPLES,
                    "error": "Teks tidak layak untuk dijelaskan."}
        return self._lime(x)

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

        # 5. DETEKSI PEMOTONGAN TEKS (Thread-Safe via Lock Bersama)
        terpotong_kata = len(v["text"].split()) > MAX_WORDS
        terpotong_token: Optional[bool] = None

        # PERBAIKAN: Selalu gunakan helper count_tokens() yang terlindungi lock
        if hasattr(self.backend, "count_tokens") and x:
            n_tokens = self.backend.count_tokens(x)
            if n_tokens is not None:
                terpotong_token = n_tokens > MAX_LEN
            else:
                # Ketersediaan tidak diketahui (tidak ditelan menjadi False)
                terpotong_token = None
        else:
            terpotong_token = None

        terpotong = bool(terpotong_kata or (terpotong_token is True))

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
            "terpotong": terpotong,  # <-- Kini mencakup kata (> 60) dan sub-token (> 128)
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
    def seed_probs_each(self, texts: List[str]) -> np.ndarray:
        torch = self.torch
        texts = [str(t) for t in texts]
        enc = self.tokenizer(texts, max_length=MAX_LEN, padding="max_length", truncation=True, return_tensors="pt")
        out = np.zeros((len(texts), len(self.seeds)), dtype=np.float64)
        with self._lock, torch.no_grad():
            for j, s in enumerate(self.seeds):
                self.clf.load_state_dict(self.states[s], strict=False)   # menimpa SEMUA kunci terlatih
                for i in range(0, len(texts), BATCH):
                    ids = enc["input_ids"][i:i + BATCH].to(self.device)
                    am = enc["attention_mask"][i:i + BATCH].to(self.device)
                    p = torch.softmax(self.clf(ids, am), dim=1)[:, 1].cpu().numpy()
                    out[i:i + len(p), j] = p
        return out

    # -- Tambahkan helper method thread-safe ini di dalam BackendIndoBERT --
    def count_tokens(self, text: str) -> Optional[int]:
        """Menghitung jumlah token sub-kata secara thread-safe."""
        try:
            with self._lock:
                return len(self.tokenizer.encode(str(text), add_special_tokens=True, truncation=False))
        except Exception:
            return None

    def seed_probs_each(self, texts: List[str]) -> np.ndarray:
        torch = self.torch
        texts = [str(t) for t in texts]
        out = np.zeros((len(texts), len(self.seeds)), dtype=np.float64)

        with self._lock:
            # Tokenisasi wajib di dalam lock agar tidak ada kebocoran batas token
            enc = self.tokenizer(texts, max_length=MAX_LEN, padding="max_length", truncation=True, return_tensors="pt")
            with torch.no_grad():
                for j, s in enumerate(self.seeds):
                    self.clf.load_state_dict(self.states[s], strict=False)
                    for i in range(0, len(texts), BATCH):
                        ids = enc["input_ids"][i:i + BATCH].to(self.device)
                        am = enc["attention_mask"][i:i + BATCH].to(self.device)
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
