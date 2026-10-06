"""
text_pipeline.py
Satu-satunya tempat aturan pembentukan teks (Single Source of Truth).
Dipakai oleh notebook dataset (01b), training (03), dan backend inferensi.
"""
import html
import re

PIPELINE_VERSION = "tp-1.2"   # Naik ke 1.2: pembersih pembatas garis === dan metadata KATEGORI

# ---- pembersihan -----------------------------------------------------------
TAG = re.compile(
    r"[\[\(\{]\s*(SALAH|HOAKS|HOAX|DISINFORMASI|MANIPULASI|MISLEADING|FITNAH|KLARIFIKASI|BENAR|FALSE)\s*[\]\)\}]\s*:?",
    re.I,
)

# Pemotong pembatas garis Mafindo/TurnBackHoax (misal: ==========================KATEGORI: ...)
DIVIDER_CUT = re.compile(r"\s*={3,}.*", re.S)

# Penanda potongan bagian akhir bantahan/vonis jurnalis
DEBUNK_CUT = re.compile(
    r"\b(?:namun\s+|tetapi\s+)?(PENJELASAN|FAKTANYA|FAKTA SEBENARNYA|HASIL CEK FAKTA|"
    r"BERDASARKAN PENELUSURAN|SETELAH DITELUSURI|HASIL VERIFIKASI|KESIMPULAN|"
    r"KATEGORI\s*:|INFORMASI MENYESATKAN|KONTEN SUDAH DIMANIPULASI|MENYESATKAN\.\s*FAKTA)\b.*",
    re.I | re.S,
)

# Pembersih kalimat pengantar debunker di awal teks
DEBUNKER_HEADER = re.compile(
    r"^\s*hasil\s+(?:periksa|cek)\s+fakta\s+[^\.\n]+(?:\([^\)]+\))?[\.\:\,\-]?\s*"
    r"(?:(?:informasi|konten|klaim|kabar|video|narasi)\s+tersebut\s+(?:hoaks|hoax|palsu|tidak\s+benar|keliru|disinformasi)[\.\:\,\-]?)?\s*",
    re.I
)

FOOTNOTE = re.compile(r"\bsumber\s*:.*$", re.I | re.S)
LEADING_TAG = re.compile(r"^\s*(?:[\[\(\{][^\]\)\}]{1,25}[\]\)\}]\s*:?\s*)+")
URL = re.compile(r"https?://\S+|www\.\S+")
HTML_TAG = re.compile(r"<[^>]+>")


def norm_ws(t: str) -> str:
    return re.sub(r"\s+", " ", str(t)).strip()


def clean(t) -> str:
    """Pembersihan minimal yang sama untuk semua kelas. Tidak membuang tanda baca esensial."""
    if t is None:
        return ""
    t = html.unescape(str(t))
    if t.strip().lower() in ("nan", "none"):
        return ""
    t = URL.sub(" ", t)
    t = HTML_TAG.sub(" ", t)
    t = LEADING_TAG.sub("", norm_ws(t))
    t = DEBUNKER_HEADER.sub("", t)
    t = DIVIDER_CUT.sub("", t)       # Memotong garis pembatas === Mafindo
    t = TAG.sub(" ", t)
    t = DEBUNK_CUT.sub("", t)
    t = FOOTNOTE.sub("", t)
    return norm_ws(t)


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
    """Buang pengulangan judul di awal body."""
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
    """Batas panjang yang sama untuk semua kelas; potong di batas kalimat bila ada."""
    w = text.split()
    if len(w) <= max_words:
        return text
    cut = " ".join(w[:max_words])
    p = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return cut[: p + 1] if p >= 0.5 * len(cut) else ensure_end(cut)


def has_leading_tag(t) -> bool:
    return bool(LEADING_TAG.match(html.unescape(str(t))))


def dup_title(t: str) -> bool:
    """Deteksi judul ganda robust berbasis token overlap."""
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
    return overlap >= 0.70