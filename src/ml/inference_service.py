"""
inference_service.py — kontrak layanan model (tanpa FastAPI/DB; dapat dipanggil dari route mana pun).

Aturan desain:
  1. Teks dibentuk oleh text_pipeline (modul yang SAMA dengan pembangun dataset). Tidak ada aturan pra-proses tersembunyi.
  2. Tidak ada sanitizer/regex yang dibuat dari kasus uji. Ketahanan harus berasal dari data dan pelatihan.
  3. Probabilitas DIKALIBRASI (temperature scaling di VAL), vonis memakai zona abstain yang ditentukan di VAL
     untuk presisi target — bukan angka 0,5 bawaan dan bukan angka yang dipilih dengan melihat hasil uji.
  4. Setiap hasil membawa versi model, pipeline, suhu, dan zona -> dapat direproduksi dan diaudit.
  5. Hasil mengatakan apa adanya: tingkat kemiripan dengan pola klaim yang pernah dibantah, bukan 'kebenaran'.
"""
import hashlib
import re
from dataclasses import dataclass, asdict, field
from typing import Callable, Dict, Optional, Tuple

import numpy as np
from scipy.optimize import minimize_scalar

import text_pipeline as tp

PIPELINE_VERSION = tp.PIPELINE_VERSION
LABEL_TEXT = {                       # teks tampilan; ubah di sini, bukan di route/frontend
    "mirip_klaim_dibantah": "Mirip pola klaim yang pernah dibantah",
    "tidak_mirip": "Tidak mirip pola klaim yang pernah dibantah",
    "perlu_konfirmasi": "Perlu konfirmasi (model tidak cukup yakin)",
}


class InputError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message); self.code = code


# --------------------------------------------------------------------------------------
# Kalibrasi & zona abstain (dipelajari dari VALIDASI, tidak dari data uji)
# --------------------------------------------------------------------------------------
def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True); e = np.exp(z); return e / e.sum(axis=1, keepdims=True)


def fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    """Temperatur T yang meminimalkan NLL pada data validasi. logits: (n,2), y: (n,)."""
    def nll(T):
        p = _softmax(logits / T)[np.arange(len(y)), y]
        return -np.log(np.clip(p, 1e-12, 1)).mean()
    return float(minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded").x)


def expected_calibration_error(p_hoax: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    conf = np.maximum(p_hoax, 1 - p_hoax); correct = ((p_hoax >= 0.5).astype(int) == y); ece = 0.0
    edges = np.linspace(0.5, 1.0, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any(): ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def fit_band(p_hoax: np.ndarray, y: np.ndarray, target_precision: float = 0.95, min_support: int = 30) -> Tuple[float, float]:
    """
    (t_low, t_high): p >= t_high -> 'mirip' dengan presisi >= target; p <= t_low -> 'tidak mirip' dengan presisi >= target;
    di antaranya -> perlu_konfirmasi. Dipilih pada VAL. Bila target tidak tercapai, zona abstain melebar ke seluruh rentang
    sehingga layanan abstain, bukan berpura-pura yakin.
    """
    t_high, t_low = 1.0, 0.0
    for t in np.unique(np.round(p_hoax, 4))[::-1][::1]:                      # turun dari yang terbesar
        m = p_hoax >= t
        if m.sum() >= min_support and (y[m] == 1).mean() >= target_precision: t_high = float(t)
    for t in np.unique(np.round(p_hoax, 4)):                                  # naik dari yang terkecil
        m = p_hoax <= t
        if m.sum() >= min_support and (y[m] == 0).mean() >= target_precision: t_low = float(t)
    if t_low >= t_high:                                                       # tidak ada zona keyakinan yang konsisten
        return 0.0, 1.0
    return t_low, t_high


# --------------------------------------------------------------------------------------
# Layanan
# --------------------------------------------------------------------------------------
@dataclass
class ServiceConfig:
    model_id: str                      # mis. 'indobert-v2-seed42-<sha8>'
    temperature: float = 1.0
    t_low: float = 0.0
    t_high: float = 1.0
    min_words: int = 10                # = MIN_WORDS saat training (01b); satu sumber kebenaran
    max_words: int = 60                # = MAX_WORDS saat training
    max_chars: int = 6000
    calibration_note: str = "belum dikalibrasi"


@dataclass
class Result:
    verdict: str
    verdict_text: str
    p_hoax_calibrated: float
    p_hoax_raw: float
    n_words_used: int
    truncated: bool
    model_id: str
    pipeline_version: str
    temperature: float
    band: Tuple[float, float]
    input_sha256: str                  # jejak tanpa menyimpan teks (kebijakan penyimpanan diputuskan terpisah)
    notes: list = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


class InferenceService:
    def __init__(self, logits_fn: Callable[[list], np.ndarray], cfg: ServiceConfig):
        """logits_fn(list[str]) -> ndarray (n,2) logit mentah [fakta, hoaks]. Model/tokenizer dibungkus di luar."""
        self.logits_fn, self.cfg = logits_fn, cfg

    def validate(self, text) -> str:
        if not isinstance(text, str) or not text.strip():
            raise InputError("kosong", "Teks kosong.")
        if len(text) > self.cfg.max_chars:
            raise InputError("terlalu_panjang", f"Teks melebihi {self.cfg.max_chars} karakter.")
        n = len(tp.clean(text).split())
        if n < self.cfg.min_words:
            raise InputError("terlalu_pendek", f"Teks minimal {self.cfg.min_words} kata (ditemukan {n}).")
        return text

    def prepare(self, text: str) -> Tuple[str, bool]:
        """Pembentukan teks = fungsi yang sama dengan pembangun dataset. Tanpa 'sanitizer' khusus."""
        cleaned = tp.ensure_end(tp.clean(text))
        capped = tp.cap_sentences(cleaned, self.cfg.max_words)
        return capped, len(capped.split()) < len(cleaned.split())

    def predict(self, text: str) -> Result:
        self.validate(text)
        prepared, truncated = self.prepare(text)
        logit = np.asarray(self.logits_fn([prepared]), dtype=float).reshape(1, 2)
        p_raw = float(_softmax(logit)[0, 1]); p_cal = float(_softmax(logit / self.cfg.temperature)[0, 1])
        c = self.cfg
        verdict = "mirip_klaim_dibantah" if p_cal >= c.t_high else ("tidak_mirip" if p_cal <= c.t_low else "perlu_konfirmasi")
        notes = []
        if truncated: notes.append(f"Teks dipotong ke ±{c.max_words} kata, sama seperti saat pelatihan.")
        if (c.t_low, c.t_high) == (0.0, 1.0): notes.append("Zona keyakinan belum dikalibrasi/tidak tercapai: layanan abstain.")
        return Result(verdict, LABEL_TEXT[verdict], p_cal, p_raw, len(prepared.split()), truncated, c.model_id, PIPELINE_VERSION,
                      c.temperature, (c.t_low, c.t_high), hashlib.sha256(text.encode("utf-8")).hexdigest(), notes)


def calibrate_from_validation(logits_val: np.ndarray, y_val: np.ndarray, target_precision: float = 0.95) -> Dict:
    """Satu fungsi yang menghasilkan semua parameter kalibrasi dari VAL + laporannya (ECE sebelum/sesudah)."""
    T = fit_temperature(logits_val, y_val)
    p_before, p_after = _softmax(logits_val)[:, 1], _softmax(logits_val / T)[:, 1]
    t_low, t_high = fit_band(p_after, y_val, target_precision)
    covered = ((p_after >= t_high) | (p_after <= t_low)).mean()
    return {"temperature": T, "t_low": t_low, "t_high": t_high,
            "ece_before": expected_calibration_error(p_before, y_val), "ece_after": expected_calibration_error(p_after, y_val),
            "coverage_val": float(covered), "target_precision": target_precision}