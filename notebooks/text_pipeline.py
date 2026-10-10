"""
text_pipeline.py — Versi tp-1.4 (Final, Steril, & Rapi)
Perbaikan:
  1. Baris baru (\n) dipertahankan saat clean(), norm_ws() dipanggil di akhir.
  2. MAFINFO_META dan STANDALONE_DIVIDER presisi (narasi hoaks tidak terpotong).
  3. NARASI_LABEL dikunci di awal baris (tidak memotong kata 'klaim' di tengah kalimat).
  4. strip_leading_title() menangani awalan framing (Video/Foto/Tangkapan Layar).
  5. build_text() kebal terhadap duplikasi judul identik.
"""

import html
import re

PIPELINE_VERSION = "tp-1.4"

# ── 1. REGEX PRESISI ────────────────────────────────────────────────────────

# Hapus blok metadata Mafindo (contoh: === KATEGORI: KONTEN YANG MENYESATKAN ===)
MAFINFO_META = re.compile(
    r"={3,}\s*(?:KATEGORI|KONTEN|STATUS|LABEL)\b[^=]{0,120}={3,}\s*",
    re.IGNORECASE
)

# Hapus sisa deretan === mandiri di mana pun posisinya
STANDALONE_DIVIDER = re.compile(r"={3,}")

# Potong bagian penjelasan jurnalis di akhir teks
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

# Kunci NARASI_LABEL hanya di awal baris (tidak memotong kata 'klaim' di tengah kalimat)
NARASI_LABEL = re.compile(
    r"^\s*(?:narasi\s+(?:postingan|pada\s+postingan|unggahan|di\s+facebook|di\s+whatsapp)|"
    r"narasi|klaim|informasi\s+yang\s+beredar)\s*[:\-–—]?\s*",
    re.IGNORECASE | re.MULTILINE
)

# Penanda awalan framing judul hoaks (Video, Foto, Gambar, Tangkapan Layar, Gawat)
FRAMING_PREFIX = re.compile(
    r"^\s*(?:video|foto|gambar|tangkapan\s+layar|pesan\s+berantai|berita|artikel|informasi|gawat\s*!*)\s*[:\-–—\"\'\u201c\u201d]?\s*",
    re.IGNORECASE
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
    Pipeline pembersihan bedah presisi:
    Baris baru (\n) DIPERTAHANKAN selama regex bekerja, baru dipadatkan di akhir.
    """
    if text is None:
        return ""
    t = html.unescape(str(text))
    if t.strip().lower() in ("nan", "none"):
        return ""

    t = HTML_TAG.sub(" ", t)
    t = LEADING_TAG.sub("", t)          # Jangan norm_ws di sini agar \n tidak hilang!
    t = DEBUNKER_HEADER.sub("", t)

    # 1. Potong bagian penjelasan jurnalis di akhir
    t = DEBUNK_CUT.sub("", t)

    # 2. Hapus blok metadata Mafindo (=== KATEGORI ... ===)
    t = MAFINFO_META.sub(" ", t)

    # 3. Hapus garis pembatas ===
    t = STANDALONE_DIVIDER.sub(" ", t)

    # 4. Hapus label NARASI / Narasi postingan:
    t = NARASI_LABEL.sub("", t)

    # 5. Hapus footnote, URL, dan tag status
    t = FOOTNOTE.sub("", t)
    t = TAG.sub("", t)

    # 6. Normalisasi akhir
    return norm_ws(t)


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
    """
    Buang pengulangan judul di awal body.
    Tahan terhadap awalan framing (Video/Foto/Tangkapan Layar) dan label narasi.
    """
    body = NARASI_LABEL.sub("", body.strip())
    
    # Bersihkan awalan Video/Foto/Gambar dari judul sebelum dibandingkan
    t_clean = FRAMING_PREFIX.sub("", title.strip())
    t = _alnum(t_clean)
    if not t or len(t) < 8:
        t = _alnum(title)
        if not t:
            return body

    for _ in range(max_repeat):
        b_alnum = _alnum(body)
        b_clean_alnum = _alnum(FRAMING_PREFIX.sub("", body.strip()))
        
        # Jika body sama persis dengan judul (kasus fallback), kosongkan body
        if b_alnum == t or b_clean_alnum == t:
            return ""
        if b_alnum.startswith(t):
            body = _drop_alnum_prefix(body, len(t)).lstrip(" .:-–—,")
            body = NARASI_LABEL.sub("", body.strip())
        elif b_clean_alnum.startswith(t):
            body = FRAMING_PREFIX.sub("", body.strip())
            body = _drop_alnum_prefix(body, len(t)).lstrip(" .:-–—,")
            body = NARASI_LABEL.sub("", body.strip())
        else:
            break
    return body


def ensure_end(text: str) -> str:
    text = text.rstrip(" ,;:-–—")
    return text if text.endswith((".", "!", "?")) else text + "."


def build_text(title: str, body: str) -> str:
    """
    Bangun teks final dari judul dan isi.
    Mencegah jalan pintas judul ganda pada portal berita & fallback hoaks.
    """
    title = clean(str(title)).strip()
    body = clean(str(body)).strip()

    # Jika body identik dengan title (kasus fallback), jangan digandakan!
    if _alnum(title) and _alnum(body) and _alnum(title) == _alnum(body):
        return ensure_end(title)

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