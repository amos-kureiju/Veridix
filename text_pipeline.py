"""
text_pipeline.py
Satu-satunya tempat aturan pembentukan teks. Dipakai OLEH:
  - notebook pembangun dataset (01b_rebuild_dataset.ipynb)
  - backend inferensi (import yang sama) -> mencegah training-serving skew.
Aturan berlaku IDENTIK untuk kelas fakta dan hoaks.
"""
import html
import re

PIPELINE_VERSION = "tp-1.1"   # naik dari 1.0: tag pembuka generik dibuang untuk SEMUA kelas

# ---- pembersihan -----------------------------------------------------------
TAG = re.compile(
    r"[\[\(\{]\s*(SALAH|HOAKS|HOAX|DISINFORMASI|MANIPULASI|MISLEADING|FITNAH|KLARIFIKASI|BENAR|FALSE)\s*[\]\)\}]\s*:?",
    re.I,
)
# 1. Penanda potongan bagian akhir (hanya memotong jika ada penanda tegas bantahan)
DEBUNK_CUT = re.compile(
    r"\b(PENJELASAN\s*[:,-]|FAKTANYA\s*[:,-]|FAKTA SEBENARNYA\s*[:,-]|HASIL CEK FAKTA\s*[:,-]|"
    r"BERDASARKAN PENELUSURAN\s*[:,-]|SETELAH DITELUSURI\s*[:,-]|HASIL VERIFIKASI\s*[:,-])\b.*",
    re.I | re.S,
)

# 2. Pembersih kalimat pengantar debunker di AWAL teks (hanya membuang 1 kalimat stempel debunker)
DEBUNKER_HEADER = re.compile(
    r"^\s*hasil\s+(?:periksa|cek)\s+fakta\s+[^\.\n]+(?:\([^\)]+\))?[\.\:\,\-]?\s*"
    r"(?:(?:informasi|konten|klaim|kabar|video|narasi)\s+tersebut\s+(?:hoaks|hoax|palsu|tidak\s+benar|keliru|disinformasi)[\.\:\,\-]?)?\s*",
    re.I
)
FOOTNOTE = re.compile(r"\bsumber\s*:.*$", re.I | re.S)
# tag kategori di awal teks, mis. "[BERITA]", "(HASUT)", "[PENIPUAN]": generik, bukan daftar yang disusun dari contoh uji
LEADING_TAG = re.compile(r"^\s*(?:[\[\(\{][^\]\)\}]{1,25}[\]\)\}]\s*:?\s*)+")
URL = re.compile(r"https?://\S+|www\.\S+")
HTML_TAG = re.compile(r"<[^>]+>")


def norm_ws(t: str) -> str:
    return re.sub(r"\s+", " ", str(t)).strip()


def clean(t) -> str:
    """Pembersihan minimal yang sama untuk semua kelas. Tidak membuang tanda baca."""
    t = html.unescape(str(t))
    if t.strip().lower() in ("nan", "none"):
        return ""
    t = URL.sub(" ", t)
    t = HTML_TAG.sub(" ", t)
    t = LEADING_TAG.sub("", norm_ws(t))
    t = DEBUNKER_HEADER.sub("", t)
    t = TAG.sub(" ", t)
    t = DEBUNK_CUT.sub("", t)
    t = DEBUNK_CUT.sub("", t)
    t = FOOTNOTE.sub("", t)
    return norm_ws(t)


# ---- pembentukan teks -------------------------------------------------------
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
    """Buang pengulangan judul di awal body (tahan terhadap beda tanda baca/kapital)."""
    t = _alnum(title)
    if not t:
        return body
    for _ in range(max_repeat):
        if _alnum(body).startswith(t):
            body = _drop_alnum_prefix(body, len(t)).lstrip(" .:-–—,")
        else:
            break
    return body


def ensure_end(text: str) -> str:
    text = text.rstrip(" ,;:-–—")
    return text if text.endswith((".", "!", "?")) else text + "."


def build_text(title, body) -> str:
    """Judul tepat SATU kali, lalu isi. Sama untuk fakta maupun hoaks."""
    title, body = clean(title), clean(body)
    body = strip_leading_title(title, body)
    title = title.rstrip(" .:-–—")
    out = f"{title}. {body}" if (title and body) else (title or body)
    return ensure_end(norm_ws(out)) if out else ""


def cap_sentences(text: str, max_words: int) -> str:
    """Batas panjang yang SAMA untuk semua kelas; potong di batas kalimat bila ada."""
    w = text.split()
    if len(w) <= max_words:
        return text
    cut = " ".join(w[:max_words])
    p = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return cut[: p + 1] if p >= 0.5 * len(cut) else ensure_end(cut)


def has_leading_tag(t) -> bool:
    return bool(LEADING_TAG.match(html.unescape(str(t))))


def dup_title(t: str) -> bool:
    """Deteksi judul ganda (dipakai untuk audit)."""
    t = str(t).strip()
    first = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower().strip(" .")
    return len(first) >= 15 and t.lower().count(first) >= 2