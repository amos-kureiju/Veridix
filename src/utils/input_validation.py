"""input_validation.py - validasi & normalisasi masukan, TANPA ketergantungan torch.

Semua ambang di sini adalah NILAI AWAL SEMENTARA. Tetapkan/ubah hanya berdasarkan
set kalibrasi atau val (bukan set uji/lockbox), lalu catat di protokol.
"""
import re
import unicodedata
from typing import Dict, Tuple

# ── Satu-satunya sumber konstanta (pakai juga di ekstraktor & skrip evaluasi) ──
MAX_CHARS = 5000            # batas atas masukan (cegah beban CPU/regex)
MIN_WORDS = 5               # TETAPKAN dari panjang minimum data latih, lalu kunci
MIN_ALPHA_RATIO = 0.5       # huruf / karakter non-spasi
INDO_STOPWORD_MIN_RATIO = 0.05  # heuristik bahasa; kalibrasi false-reject di val

# Homoglif Sirilik/Yunani yang umum meniru huruf Latin
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "і": "i", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "ο": "o",
})
_NON_LATIN_LETTER = re.compile(r"[\u0370-\u03FF\u0400-\u04FF]")
_TOKEN = re.compile(r"\w+", re.UNICODE)

_INDO_STOPWORDS = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "ini", "itu", "pada",
    "adalah", "akan", "tidak", "dalam", "oleh", "bahwa", "atau", "sudah", "telah",
    "juga", "karena", "ada", "bisa", "saya", "kami", "mereka", "dia", "sebagai",
    "para", "tersebut", "secara", "lebih", "saat", "jika", "agar", "namun",
    "serta", "hingga", "yaitu", "kepada", "bagi", "sebuah", "setelah",
}


def normalize_input(text: str) -> Tuple[str, Dict[str, int]]:
    """NFKC, buang karakter tak terlihat (zero-width/bidi/kontrol), perbaiki homoglif.

    Mengembalikan (teks, info). info dipakai untuk log/peringatan, bukan vonis.
    """
    info = {"invisible_removed": 0, "homoglyph_fixed": 0}
    s = unicodedata.normalize("NFKC", text)

    kept = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat == "Cf" or (cat == "Cc" and ch not in "\n\r\t"):
            info["invisible_removed"] += 1
            continue
        kept.append(ch)
    s = "".join(kept)

    def _fix(m):
        tok = m.group(0)
        if _NON_LATIN_LETTER.search(tok) and re.search(r"[A-Za-z]", tok):
            fixed = tok.translate(_HOMOGLYPHS)
            if fixed != tok:
                info["homoglyph_fixed"] += 1
            return fixed
        return tok

    s = _TOKEN.sub(_fix, s)
    return s, info


def check_basic(text: str) -> Tuple[bool, str]:
    """Tolak teks kosong / tanpa huruf / hampir seluruhnya simbol atau angka."""
    stripped = re.sub(r"\s+", "", text or "")
    if not stripped:
        return False, "Masukan kosong."
    letters = sum(ch.isalpha() for ch in stripped)
    if letters == 0:
        return False, "Masukan tidak memuat huruf."
    if letters / len(stripped) < MIN_ALPHA_RATIO:
        return False, "Masukan didominasi angka atau simbol, bukan teks."
    return True, ""


def looks_indonesian(text: str) -> Tuple[bool, float]:
    """Heuristik kasar berbasis kata fungsi bahasa Indonesia (BUKAN deteksi bahasa penuh)."""
    toks = [t.lower() for t in re.findall(r"[A-Za-z]+", text)]
    if not toks:
        return False, 0.0
    hits = sum(t in _INDO_STOPWORDS for t in toks)
    ratio = hits / len(toks)
    return (hits >= 1 and ratio >= INDO_STOPWORD_MIN_RATIO), ratio