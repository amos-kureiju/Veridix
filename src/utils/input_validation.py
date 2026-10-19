"""
src/utils/input_validation.py — sanitasi dan validasi masukan teks SEBELUM masuk model.
Prinsip: menolak dengan alasan yang jelas, bukan memaksakan vonis.

Ambang bertanda SEMENTARA (MIN_STOPWORD_RATIO) wajib dikalibrasi dengan kalibrasi_gerbang_domain.py
pada data latih/val (bukan lockbox), lalu dicatat di protokol.
"""
import re
import unicodedata
from typing import Any, Dict

MIN_WORDS = 10                  # sama dengan CFG["MIN_WORDS"] saat korpus dibangun
MAX_CHARS = 20000               # batas pengaman; teks panjang tidak ditolak, hanya 60 kata pertama yang dinilai
MIN_LETTER_RATIO = 0.40
MIN_STOPWORD_RATIO = 0.02       # dikalibrasi dari kalibrasi_gerbang_domain.py pada data beku (ringkasan: menolak ~0,6% fakta dan ~2,8% hoaks;
                                # teks Inggris tetap ditolak karena rasionya 0,00). Verifikasi ulang dengan keluaran mentah dan catat di protokol.

ID_STOPWORDS = {
    "yang", "di", "dan", "dari", "ini", "untuk", "pada", "adalah", "ke", "itu", "dengan", "dalam", "bisa", "akan",
    "juga", "ada", "mereka", "sudah", "oleh", "saat", "bahwa", "tidak", "tersebut", "kita", "para", "karena",
    "bagi", "sampai",
}

# Huruf Sirilik/Yunani yang mirip huruf Latin (ditulis sebagai kode titik agar aman dari masalah penyandian berkas).
_HOMOGLYPHS = {
    0x0430: "a", 0x0435: "e", 0x043E: "o", 0x0440: "p", 0x0441: "c", 0x0443: "y", 0x0445: "x", 0x0456: "i",
    0x0410: "A", 0x0412: "B", 0x0415: "E", 0x041A: "K", 0x041C: "M", 0x041D: "H", 0x041E: "O", 0x0420: "P",
    0x0421: "C", 0x0422: "T", 0x0425: "X", 0x0406: "I",
    0x03BF: "o", 0x0391: "A", 0x0392: "B", 0x0395: "E", 0x039A: "K", 0x039C: "M", 0x039D: "N", 0x039F: "O",
    0x03A1: "P", 0x03A4: "T", 0x03A7: "X", 0x0399: "I", 0x03A5: "Y",
}
_KEEP_WS = ("\n", "\t", "\r")


def sanitize_characters(text: str):
    """NFKC, buang karakter format/kontrol tak terlihat (zero-width, bidi), normalkan homoglif ke Latin."""
    s = unicodedata.normalize("NFKC", str(text))
    flags = {"had_invisible": False, "had_homoglyph": False}
    kept = []
    for ch in s:
        if unicodedata.category(ch) in ("Cf", "Cc") and ch not in _KEEP_WS:
            flags["had_invisible"] = True
            continue
        kept.append(ch)
    s2 = "".join(kept)
    s3 = s2.translate(_HOMOGLYPHS)
    flags["had_homoglyph"] = s3 != s2
    return s3.strip(), flags


def stopword_ratio(text: str) -> float:
    words = re.findall(r"[a-z]+", text.lower())
    return (sum(w in ID_STOPWORDS for w in words) / len(words)) if words else 0.0


def validate_input_text(text: Any) -> Dict[str, Any]:
    """Kembalikan dict: ok, text (tersanitasi), reason, flags, n_words, stopword_ratio."""
    out = {"ok": False, "text": "", "reason": "", "flags": {}, "n_words": 0, "stopword_ratio": None}
    if text is None or not str(text).strip():
        out["reason"] = "Teks kosong."
        return out

    s, flags = sanitize_characters(text)
    out.update(text=s, flags=flags)
    if not s:
        out["reason"] = "Teks kosong setelah pembersihan karakter tak terlihat."
        return out
    if len(s) > MAX_CHARS:
        out["reason"] = f"Teks melebihi batas pengaman ({len(s)} > {MAX_CHARS} karakter)."
        return out

    letters = re.findall(r"[A-Za-z]", s)
    if not letters:
        out["reason"] = "Teks tidak memuat huruf."
        return out
    ratio = len(letters) / max(len(re.sub(r"\s", "", s)), 1)
    if ratio < MIN_LETTER_RATIO:
        out["reason"] = f"Teks didominasi angka atau simbol (rasio huruf {ratio:.2f} < {MIN_LETTER_RATIO})."
        return out

    n = len(s.split())
    out["n_words"] = n
    if n < MIN_WORDS:
        out["reason"] = f"Teks terlalu pendek ({n} kata < {MIN_WORDS})."
        return out

    sr = stopword_ratio(s)
    out["stopword_ratio"] = round(sr, 4)
    if sr < MIN_STOPWORD_RATIO:
        out["reason"] = f"Teks tampak bukan bahasa Indonesia (rasio kata fungsi {sr:.2f} < {MIN_STOPWORD_RATIO})."
        return out

    out["ok"] = True
    return out