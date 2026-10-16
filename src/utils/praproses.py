"""
src/utils/praproses.py — SATU-SATUNYA jalur praproses inferensi (aplikasi, uji derau, uji OCR, evaluasi lockbox).

Jalur ini SAMA dengan yang dipakai pada semua uji yang sudah dijalankan:
    tp.clean  ->  tp.ensure_end  ->  tp.cap_sentences(60)
Dua langkah tambahan dari rancangan sebelumnya SENGAJA tidak aktif:
  * penyambungan tanda hubung akhir baris (belum divalidasi pada OCR nyata; aktifkan hanya bila terbukti
    membantu pada set KALIBRASI),
  * tp.norm_title pada seluruh teks (dirancang untuk JUDUL; tidak pernah diuji pada teks utuh).
Menyimpang dari jalur yang diuji berarti sistem yang dijalankan bukan sistem yang dievaluasi.
"""
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import text_pipeline as tp  # noqa: E402  (modul beku tp-1.6)

MAX_WORDS = 60


def sambung_tanda_hubung(text: str) -> str:
    """'me- netapkan' -> 'menetapkan'. Hanya bila huruf sebelum '-' dan huruf kecil sesudahnya; tidak menyentuh
    'Prabowo- Gibran', 'TNI- Polri', atau rentang angka '2019- 2024'."""
    return re.sub(r"(?<=[A-Za-z])-\s+(?=[a-z])", "", text)


def praproses(text: str, sambung: bool = False) -> str:
    t = tp.clean(str(text))
    if sambung:
        t = sambung_tanda_hubung(t)
    if not t:
        return ""
    return tp.cap_sentences(tp.ensure_end(t), MAX_WORDS)