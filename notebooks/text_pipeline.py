"""
text_pipeline.py — Versi tp-1.3 (Bedah Presisi & Integrasi Menyeluruh)
Mengintegrasikan perbaikan presisi:
  - BUANG   : blok metadata === KATEGORI ... ===
  - BUANG   : teks bantahan jurnalis setelah PENJELASAN:/FAKTANYA:
  - SIMPAN  : teks narasi/klaim hoaks di antaranya
  - LENGKAP : memuat clean(), cap_sentences(), dup_title(), build_text()
"""

import html
import re

PIPELINE_VERSION = "tp-1.3"

# ── 1. REGEX BEDAH PRESISI (LOGIKA REVIEWER) ────────────────────────────────

# Hapus baris pembatas yang seluruhnya berisi tanda ===
STANDALONE_DIVIDER = re.compile(r"^={3,}\s*$", re.MULTILINE)

# Hapus blok metadata Mafindo (contoh: === KATEGORI: KONTEN YANG MENYESATKAN ===)
MAFINFO_META = re.compile(
    r"={3,}\s*(KATEGORI|KONTEN|STATUS|LABEL)[^\n]*={0,}\n?",
    re.IGNORECASE
)

# Potong bagian penjelasan jurnalis (hanya teks setelah kata ini yang dibuang)
DEBUNK_CUT = re.compile(
    r"\n?\s*(?:namun\s+|tetapi\s+)?(PENJELASAN|FAKTANYA|HASIL PERIKSA FAKTA|KLARIFIKASI|"
    r"HOAKS ATAU FAKTA\?|KESIMPULAN|ANALISIS)\s*:.*",
    re.IGNORECASE | re.S
)

# Pembersih stempel debunker di awal kalimat
DEBUNKER_HEADER = re.compile(
    r"^\s*hasil\s+(?:periksa|cek)\s+fakta\s+[^\.\n]+(?:\([^\)]+\))?[\.\:\,\-]?\s*"
    r"(?:(?:informasi|konten|klaim|kabar|video|narasi)\s+tersebut\s+(?:hoaks|hoax|palsu|tidak\s+benar|keliru|disinformasi)[\.\:\,\-]?)?\s*",
    re.I
)

# Hapus label awalan NARASI: (konten klaimnya tetap disimpan)
NARASI_LABEL = re.compile(
    r"^(NARASI|KLAIM|INFORMASI YANG BEREDAR)\s*:?\s*",
    re.IGNORECASE | re.MULTILINE
)

# Hapus footnote dan URL
FOOTNOTE = re.compile(r"\(sumber:.*?\)|\[.*?\]|https?://\S+", re.IGNORECASE)

# Tag status awal
TAG = re.compile(
    r"\[(HOAKS|SALAH|DISINFORMASI|MANIPULASI|FALSE|BENAR|EDUKASI|HASUT)\]",
    re.IGNORECASE
)

LEADING_TAG = re.compile(r"^\s*(?:[\[\(\{][^\]\)\}]{1,25}[\]\)\}]\s*:?\s*)+")
HTML_TAG = re.compile(r"<[^>]+>")


def norm_ws(t: str) -> str:
    return re.sub(r"\s+", " ", str(t)).strip()


def clean(text: str) -> str:
    """
    Pipeline pembersihan bedah presisi. Satu fungsi untuk semua kelas.
    """
    if text is None:
        return ""
    t = html.unescape(str(text))
    if t.strip().lower() in ("nan", "none"):
        return ""

    t = HTML_TAG.sub(" ", t)
    t = LEADING_TAG.sub("", norm_ws(t))
    t = DEBUNKER_HEADER.sub("", t)

    # 1. Potong bagian penjelasan jurnalis di akhir
    t = DEBUNK_CUT.sub("", t)

    # 2. Hapus blok metadata Mafindo (KATEGORI: ...)
    t = MAFINFO_META.sub(" ", t)

    # 3. Hapus garis pembatas ===
    t = STANDALONE_DIVIDER.sub(" ", t)

    # 4. Hapus label NARASI:
    t = NARASI_LABEL.sub("", t)

    # 5. Hapus footnote, URL, dan tag status
    t = FOOTNOTE.sub("", t)
    t = TAG.sub("", t)

    return norm_ws(t)


# Alias untuk kompatibilitas jika dipanggil clean_pipeline
clean_pipeline = clean


# ── 2. PEMBENTUKAN TEKS & PENCEGAH JUDUL GANDA ──────────────────────────────
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


def build_text(title: str, body: str) -> str:
    """
    Bangun teks final dari judul dan isi.
    Mencegah jalan pintas judul ganda pada portal berita.
    """
    title = clean(str(title)).strip()
    body = clean(str(body)).strip()

    body = strip_leading_title(title, body)
    title = title.rstrip(" .:-–—")
    out = f"{title}. {body}" if (title and body) else (title or body)
    return ensure_end(norm_ws(out)) if out else ""


def cap_sentences(text: str, max_words: int) -> str:
    """Batas panjang yang sama untuk semua kelas; potong di batas kalimat."""
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