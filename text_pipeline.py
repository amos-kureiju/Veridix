"""
text_pipeline.py — Versi tp-1.5 (Protokol Reviewer Resmi)
Pembaruan:
  - T1: PIPELINE_VERSION = "tp-1.5"
  - T2: DATELINE stripper (membuang TEMPO.CO, CNN Indonesia agar tidak jadi shortcut)
  - T2: UNBRACKETED_TAG stripper (membuang HASUT:, KLARIFIKASI:)
  - T2: BOILER stripper (membuang ADVERTISEMENT, baca juga:)
  - T3: Pembersihan clean() bertahap tanpa merusak baris baru (\n)
  - T4: strip_leading_title() dengan pencarian jendela geser (pos = b.find)
  - T5: Pemisahan dup_title_strict (duplikasi harafiah) dan dup_title_para (parafrasa)
"""

import html
import re

PIPELINE_VERSION = "tp-1.5"

# ── 1. REGEX PRESISI PROTOKOL REVIEWER ──────────────────────────────────────

# Label wajib berpenanda ":" / "-" agar "Klaim Presiden ..." tidak dirusak
NARASI_LABEL = re.compile(
    r"^\s*(?:narasi(?:\s+(?:pada\s+)?(?:postingan|unggahan|di\s+(?:facebook|whatsapp)))?"
    r"|klaim|informasi\s+yang\s+beredar)\b\s*[:\-–—]\s*",
    re.IGNORECASE | re.MULTILINE
)

FRAMING_PREFIX = re.compile(
    r"^\s*(?:(?:berita|artikel)\s+\S+(?:\s+\S+){0,2}?\s+tentang|breaking\s+news|video|foto|gambar|"
    r"tangkapan\s+layar|pesan\s+berantai|berita|artikel|informasi|gawat)\b\s*!*\s*[:\-–—\"'\u201c\u201d]?\s*",
    re.IGNORECASE
)

# Tag tanpa kurung: "HASUT: ...", "KLARIFIKASI: ..."
UNBRACKETED_TAG = re.compile(
    r"^\s*(?:HASUT|DISINFORMASI|MISINFORMASI|HOAKS|HOAX|SALAH|FALSE|KLARIFIKASI)\s*:\s*",
    re.IGNORECASE
)

# Tanda tangan sumber di awal isi (jalan pintas sumber = label yang wajib dibuang)
DATELINE = re.compile(
    r"^\s*(?:[A-Za-z .]{2,30},\s*)?(?i:TEMPO\.CO|CNN\s+Indonesia|KOMPAS\.com)"
    r"(?:\s*,\s*[A-Za-z .]{2,30})?\s*(?:--|[-–—])\s*"
)

BOILER = re.compile(
    r"\b(?:ADVERTISEMENT|SCROLL TO CONTINUE WITH CONTENT)\b|\b(?:lihat|baca)\s+juga\s*:",
    re.IGNORECASE
)

# Hapus blok metadata Mafindo (=== KATEGORI ... ===)
MAFINFO_META = re.compile(
    r"={3,}\s*(?:KATEGORI|KONTEN|STATUS|LABEL)\b[^=]{0,120}={3,}\s*",
    re.IGNORECASE
)

STANDALONE_DIVIDER = re.compile(r"={3,}")

DEBUNK_CUT = re.compile(
    r"\n?\s*(?:namun\s+|tetapi\s+)?(PENJELASAN|FAKTANYA|HASIL PERIKSA FAKTA|KLARIFIKASI|"
    r"HOAKS ATAU FAKTA\?|KESIMPULAN|ANALISIS)\s*:.*",
    re.IGNORECASE | re.S
)

DEBUNKER_HEADER = re.compile(
    r"^\s*hasil\s+(?:periksa|cek)\s+fakta\s+[^\.\n]+(?:\([^\)]+\))?[\.\:\,\-]?\s*"
    r"(?:(?:informasi|konten|klaim|kabar|video|narasi)\s+tersebut\s+(?:hoaks|hoax|palsu|tidak\s+benar|keliru|disinformasi)[\.\:\,\-]?)?\s*",
    re.I
)

FOOTNOTE = re.compile(r"\(sumber:.*?\)|\[.*?\]|https?://\S+", re.IGNORECASE)
LEADING_TAG = re.compile(r"^\s*(?:[\[\(\{][^\]\)\}]{1,25}[\]\)\}]\s*:?\s*)+")
HTML_TAG = re.compile(r"<[^>]+>")


def norm_ws(t: str) -> str:
    return re.sub(r"\s+", " ", str(t)).strip()


def clean(text: str) -> str:
    """Urutan clean() sesuai T3 protokol reviewer."""
    if text is None:
        return ""
    t = html.unescape(str(text))
    if t.strip().lower() in ("nan", "none"):
        return ""

    t = HTML_TAG.sub(" ", t)
    t = LEADING_TAG.sub("", t)
    t = UNBRACKETED_TAG.sub("", t)      # T3 baru
    t = DATELINE.sub("", t)             # T3 baru (hapus TEMPO.CO, dsb.)
    t = DEBUNKER_HEADER.sub("", t)
    t = DEBUNK_CUT.sub("", t)
    t = MAFINFO_META.sub(" ", t)
    t = STANDALONE_DIVIDER.sub(" ", t)
    t = NARASI_LABEL.sub("", t)
    t = BOILER.sub(" ", t)              # T3 baru
    t = FOOTNOTE.sub("", t)
    return norm_ws(t)


clean_pipeline = clean


# ── 2. PEMBENTUKAN TEKS & SLIDING TITLE STRIPPER ─────────────────────────────
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


def strip_leading_title(title: str, body: str, max_repeat: int = 3, max_prefix: int = 30) -> str:
    """T4: Cari judul di dekat awal isi menggunakan jendela geser."""
    body = NARASI_LABEL.sub("", body.strip())
    t = _alnum(FRAMING_PREFIX.sub("", title.strip()))
    if len(t) < 8:
        t = _alnum(title)
    if not t:
        return body

    for _ in range(max_repeat):
        b = _alnum(body)
        if not b or b == t:
            return ""
        pos = b.find(t, 0, max_prefix + len(t))
        if pos < 0:
            break
        body = _drop_alnum_prefix(body, pos + len(t)).lstrip(" .:-–—,\"'“”‘’")
        body = NARASI_LABEL.sub("", body.strip())
    return body


def ensure_end(text: str) -> str:
    text = text.rstrip(" ,;:-–—")
    return text if text.endswith((".", "!", "?")) else text + "."


def build_text(title: str, body: str) -> str:
    title = clean(str(title)).strip()
    body = clean(str(body)).strip()

    if _alnum(title) and _alnum(body) and _alnum(title) == _alnum(body):
        return ensure_end(title)

    body = strip_leading_title(title, body)
    title = title.rstrip(" .:-–—")
    out = f"{title}. {body}" if (title and body) else (title or body)
    return ensure_end(norm_ws(out)) if out else ""


def cap_sentences(text: str, max_words: int) -> str:
    w = text.split()
    if len(w) <= max_words:
        return text
    cut = " ".join(w[:max_words])
    p = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return cut[: p + 1] if p >= 0.5 * len(cut) else ensure_end(cut)


def has_leading_tag(t) -> bool:
    return bool(LEADING_TAG.match(html.unescape(str(t)))) or bool(UNBRACKETED_TAG.match(html.unescape(str(t))))


# ── 3. T5: PEMISAHAN C1 HARAFIAT VS PARAFRASA ────────────────────────────────
def dup_title_strict(t: str) -> bool:
    """Artefak pipeline: kalimat pertama diulang harafiah di awal sisa teks."""
    parts = re.split(r"(?<=[.!?])\s+", str(t).strip(), maxsplit=1)
    if len(parts) < 2:
        return False
    a, b = _alnum(parts[0]), _alnum(parts[1])
    return len(a) >= 8 and b.find(a, 0, len(a) + 30) >= 0


def dup_title_para(t: str) -> bool:
    """Overlap token >= 0.70 (menangkap parafrasa wajar jurnalisme)."""
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


dup_title = dup_title_para