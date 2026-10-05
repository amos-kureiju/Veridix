"""
text_pipeline.py
Satu-satunya tempat aturan pembentukan teks. Dipakai OLEH:
  - notebook pembangun dataset (01b_rebuild_dataset.ipynb)
  - backend inferensi / PaddleOCR (import yang sama) -> mencegah training-serving skew.
Aturan berlaku IDENTIK untuk kelas fakta dan hoaks.
"""
import html
import re
from typing import Optional

# ---- pembersihan tag & artefak ---------------------------------------------
TAG = re.compile(
    r"[\[\(\{]\s*(SALAH|HOAKS|HOAX|DISINFORMASI|MANIPULASI|MISLEADING|FITNAH|KLARIFIKASI|BENAR|FALSE|BANTUAN|UPDATE)\s*[\]\)\}]\s*:?",
    re.I,
)

# Penanda bagian "bantahan" milik situs pemeriksa fakta
DEBUNK_CUT = re.compile(
    r"\b(PENJELASAN\s*:|FAKTANYA\s*:|FAKTA SEBENARNYA|HASIL CEK FAKTA|HASIL PERIKSA FAKTA|"
    r"BERDASARKAN PENELUSURAN|SETELAH DITELUSURI|HASIL VERIFIKASI|KESIMPULAN\s*:)\b.*",
    re.I | re.S,
)

# Pembersih Dateline/Byline Media Portal Berita (Fakta)
MEDIA_BYLINE = re.compile(
    r"^\s*(?:[A-Z\s]+,\s*)?(?:CNN\s+Indonesia|TEMPO\.CO|KOMPAS\.com|Liputan6\.com|Detikcom|ANTARA|Merdeka\.com)"
    r"(?:\s*,\s*[A-Za-z\s]+)?\s*[-–—]+\s*",
    re.I
)
GENERIC_CITY_BYLINE = re.compile(r"^\s*[A-Z\s]{3,15}\s*[-–—]\s*")

FOOTNOTE = re.compile(r"\bsumber\s*:.*$", re.I | re.S)
URL = re.compile(r"https?://\S+|www\.\S+")
HTML_TAG = re.compile(r"<[^>]+>")


def norm_ws(t: str) -> str:
    return re.sub(r"\s+", " ", str(t)).strip()


def strip_byline(t: str) -> str:
    """Menghapus awalan media (cth: 'JAKARTA, CNN Indonesia --') agar tidak jadi shortcut."""
    t = MEDIA_BYLINE.sub("", t).strip()
    t = GENERIC_CITY_BYLINE.sub("", t).strip()
    return t


def clean(t) -> str:
    """Pembersihan minimal yang sama untuk semua kelas. Tidak membuang tanda baca esensial."""
    if t is None:
        return ""
    t = html.unescape(str(t))
    if t.strip().lower() in ("nan", "none"):
        return ""
    t = URL.sub(" ", t)
    t = HTML_TAG.sub(" ", t)
    t = TAG.sub(" ", t)
    t = DEBUNK_CUT.sub("", t)
    t = FOOTNOTE.sub("", t)
    t = strip_byline(t)
    return norm_ws(t)


# ---- pembentukan teks & deduplikasi judul -----------------------------------
def _alnum(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def _drop_alnum_prefix(s: str, n: int) -> str:
    seen = 0
    for i, ch in enumerate(s):
        if ch.isalnum():
            seen += 1
            if seen == n:
                return s[i + 1:]
    return ""


def strip_leading_title(title: str, body: str, max_repeat: int = 3) -> str:
    """
    Buang pengulangan judul di awal body.
    Tahan terhadap byline media, elipsis (...), tanda petik, dan beda tanda baca.
    """
    body = strip_byline(body)
    t = _alnum(title)
    if not t or len(t) < 10:
        return body

    for _ in range(max_repeat):
        b_alnum = _alnum(body)
        # 1. Exact alnum match
        if b_alnum.startswith(t):
            body = _drop_alnum_prefix(body, len(t)).lstrip(" .:-–—,")
            body = strip_byline(body)
        # 2. Toleransi elipsis / awalan (potongan 35 karakter alnum pertama)
        elif len(t) >= 35 and b_alnum.startswith(t[:35]):
            prefix_len = min(len(t), len(b_alnum))
            body = _drop_alnum_prefix(body, prefix_len).lstrip(" .:-–—,")
            body = strip_byline(body)
        else:
            break
    return body


def ensure_end(text: str) -> str:
    text = text.rstrip(" ,;:-–—")
    return text if text.endswith((".", "!", "?")) else text + "."


def build_text(title, body) -> str:
    """Judul tepat SATU kali, lalu isi. Berlaku identik untuk fakta maupun hoaks."""
    title = clean(title)
    body = clean(body)
    body = strip_leading_title(title, body)
    title = title.rstrip(" .:-–—")
    out = f"{title}. {body}" if (title and body) else (title or body)
    return ensure_end(norm_ws(out)) if out else ""


def cap_sentences(text: str, max_words: int) -> str:
    """Batas panjang yang SAMA untuk semua kelas; potong di batas kalimat bila memungkinkan."""
    w = text.split()
    if len(w) <= max_words:
        return text
    cut = " ".join(w[:max_words])
    p = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return cut[: p + 1] if p >= 0.5 * len(cut) else ensure_end(cut)


# ---- detektor judul ganda robust (untuk audit) ------------------------------
def dup_title(t: str, min_overlap: float = 0.70) -> bool:
    """
    Deteksi judul ganda robust (dipakai untuk audit & validasi C-criteria).
    Menggunakan token overlap set agar tahan elipsis (...) dan variasi minor.
    """
    t = str(t).strip()
    parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
    if len(parts) < 2:
        return False
    
    first_tokens = set(re.findall(r"\b\w{3,}\b", parts[0].lower()))
    if len(first_tokens) < 4:
        return False
        
    rest_head = " ".join(parts[1].split()[:len(parts[0].split()) + 6])
    rest_tokens = set(re.findall(r"\b\w{3,}\b", rest_head.lower()))
    
    overlap = len(first_tokens & rest_tokens) / max(len(first_tokens), 1)
    return overlap >= min_overlap


# ---- antarmuka khusus paddleocr & api inferensi -----------------------------
def prepare_ocr_or_raw_text(text: str, max_words: int = 60) -> str:
    """
    Pipeline satu pintu saat menerima teks utuh (misal luaran PaddleOCR atau input web).
    Otomatis mendeteksi jika kalimat pertama berulang di kalimat kedua.
    """
    t = clean(text)
    parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
    if len(parts) == 2:
        # Jika teks membawa judul ganda di dalam dirinya sendiri
        t = build_text(title=parts[0], body=parts[1])
    return cap_sentences(t, max_words=max_words)