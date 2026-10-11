"""
text_pipeline.py — Versi tp-1.5
Perubahan dari tp-1.4:
  1. clean(): baris baru dipertahankan sampai akhir (norm_ws hanya di akhir).
  2. MAFINFO_META / STANDALONE_DIVIDER presisi (narasi hoaks tidak terpotong).
  3. NARASI_LABEL wajib berpenanda ':' / '-' ("Klaim Presiden ..." tidak dirusak).
  4. UNBRACKETED_TAG ("HASUT: ...", "KLARIFIKASI: ..."), DATELINE ("TEMPO.CO, Jakarta -"),
     BOILER ("ADVERTISEMENT", label "Lihat Juga :") dibuang untuk SEMUA kelas.
  5. strip_leading_title(): cari judul di dekat awal isi (bukan hanya prefiks persis).
  6. C1 dipisah: dup_title_strict (artefak pipeline, harafiah) vs dup_title_para (parafrasa judul-lead).
"""

import html
import re

PIPELINE_VERSION = "tp-1.6"

# ── 1. REGEX ────────────────────────────────────────────────────────────────

# Blok metadata Mafindo: === KATEGORI: KONTEN YANG MENYESATKAN ===
MAFINFO_META = re.compile(
    r"={3,}\s*(?:KATEGORI|KONTEN|STATUS|LABEL)\b[^=]{0,120}={3,}\s*",
    re.IGNORECASE,
)

# Sisa deretan === di mana pun posisinya
STANDALONE_DIVIDER = re.compile(r"={3,}")

# Bagian penjelasan pemeriksa fakta di akhir teks
DEBUNK_CUT = re.compile(
    r"\n?\s*(?:namun\s+|tetapi\s+)?(PENJELASAN(?:\s*(?:&|dan|/)\s*FAKTA|\s+LENGKAP)?|FAKTANYA|HASIL PERIKSA FAKTA|KLARIFIKASI|"
    r"HOAKS ATAU FAKTA\?|KESIMPULAN|ANALISIS)\s*:.*",
    re.IGNORECASE | re.S,
)

# Stempel debunker di awal teks
DEBUNKER_HEADER = re.compile(
    r"^\s*hasil\s+(?:periksa|cek)\s+fakta\s+[^\.\n]+(?:\([^\)]+\))?[\.\:\,\-]?\s*"
    r"(?:(?:informasi|konten|klaim|kabar|video|narasi)\s+tersebut\s+"
    r"(?:hoaks|hoax|palsu|tidak\s+benar|keliru|disinformasi)[\.\:\,\-]?)?\s*",
    re.I,
)

# Label wajib berpenanda ":" / "-" agar "Klaim Presiden ..." tidak dirusak
NARASI_LABEL = re.compile(
    r"^\s*(?:narasi(?:\s+(?:pada\s+)?(?:postingan|unggahan|di\s+(?:facebook|whatsapp)))?"
    r"|klaim|informasi\s+yang\s+beredar)\b\s*[:\-–—]\s*",
    re.I | re.M,
)

# Awalan framing judul (dipakai hanya untuk PERBANDINGAN judul vs isi, tidak mengubah judul)
FRAMING_PREFIX = re.compile(
    r"^\s*(?:(?:berita|artikel)\s+\S+(?:\s+\S+){0,2}?\s+tentang|breaking\s+news|video|foto|gambar|"
    r"tangkapan\s+layar|pesan\s+berantai|berita|artikel|informasi|gawat)\b\s*!*\s*"
    r"[:\-–—\"'\u201c\u201d]?\s*",
    re.I,
)

# Tag tanpa kurung: "HASUT: ...", "KLARIFIKASI: ..."
UNBRACKETED_TAG = re.compile(
    r"^\s*(?:HASUT|DISINFORMASI|MISINFORMASI|HOAKS|HOAX|SALAH|FALSE|KLARIFIKASI)\s*:\s*",
    re.I,
)

# Tanda tangan sumber di awal isi (jalan pintas sumber = label)
DATELINE = re.compile(
    r"^\s*(?:[A-Za-z .]{2,30},\s*)?(?i:TEMPO\.CO|CNN\s+Indonesia|KOMPAS\.com)"
    r"(?:\s*,\s*[A-Za-z .]{2,30})?\s*(?:--|[-–—])\s*"
)

# Sisa antarmuka portal. ADVERTISEMENT peka huruf besar agar kata biasa tidak ikut terhapus.
BOILER = re.compile(
    r"\b(?:ADVERTISEMENT|SCROLL TO CONTINUE WITH CONTENT)\b|(?i:\b(?:lihat|baca)\s+juga\s*:)"
)

# Footnote, kurung siku, dan URL
FOOTNOTE = re.compile(r"\(sumber:.*?\)|\[.*?\]|https?://\S+", re.IGNORECASE)

LEADING_TAG = re.compile(r"^\s*(?:[\[\(\{][^\]\)\}]{1,25}[\]\)\}]\s*:?\s*)+")
HTML_TAG = re.compile(r"<[^>]+>")

# ── 4. NORMALISASI JUDUL (tp-1.6): deskriptor editorial pemeriksa fakta + tanda kutip pembungkus ──
DESC = re.compile(
    r'^\W*(?:(?:video|foto|gambar|screenshot|tangkapan\s+layar|tangkap\s+layar|sampul|pesan\s+berantai'
    r'|artikel(?:\s+(?!berjudul)\S+){0,3}?\s+berjudul|berita(?:\s+\S+){0,2}?\s+tentang)\b'
    r'|artikel(?:\s+\S+){0,3}?\s+(?=[\u201c"]))\W*', re.I)


def norm_title(t: str, unwrap: bool = True) -> str:
    c = clean(t)
    s = c
    for _ in range(4):
        n = DESC.sub("", s, count=1).strip()
        if not n or n == s:
            break
        s = n
    if unwrap and not re.search(r'[\u201c\u201d"]', s.strip('\u201c\u201d" ')):
        s = s.strip('\u201c\u201d" .')
    return s or c


def norm_ws(t: str) -> str:
    return re.sub(r"\s+", " ", str(t)).strip()


def clean(text: str) -> str:
    """Pembersihan. Baris baru dipertahankan selama regex bekerja, dipadatkan di akhir."""
    if text is None:
        return ""
    t = html.unescape(str(text))
    if t.strip().lower() in ("nan", "none"):
        return ""

    t = HTML_TAG.sub(" ", t)
    t = LEADING_TAG.sub("", t)
    t = UNBRACKETED_TAG.sub("", t)
    t = DATELINE.sub("", t)
    t = DEBUNKER_HEADER.sub("", t)
    t = DEBUNK_CUT.sub("", t)
    t = MAFINFO_META.sub(" ", t)
    t = STANDALONE_DIVIDER.sub(" ", t)
    t = NARASI_LABEL.sub("", t)
    t = BOILER.sub(" ", t)
    t = FOOTNOTE.sub("", t)
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


def strip_leading_title(title: str, body: str, max_repeat: int = 3, max_prefix: int = 30) -> str:
    """Buang pengulangan HARAFIAH judul di dekat awal isi (toleran awalan <= max_prefix karakter alnum)."""
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
    """Teks final dari judul dan isi, tanpa judul ganda harafiah."""
    title = clean(str(title)).strip()
    body = clean(str(body)).strip()

    if _alnum(title) and _alnum(body) and _alnum(title) == _alnum(body):
        return ensure_end(title)

    body = strip_leading_title(title, body)
    title = title.rstrip(" .:-–—")
    out = f"{title}. {body}" if (title and body) else (title or body)
    return ensure_end(norm_ws(out)) if out else ""


def cap_sentences(text: str, max_words: int) -> str:
    """Batas panjang; potong di batas kalimat."""
    w = text.split()
    if len(w) <= max_words:
        return text
    cut = " ".join(w[:max_words])
    p = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return cut[: p + 1] if p >= 0.5 * len(cut) else ensure_end(cut)


def has_leading_tag(t) -> bool:
    return bool(LEADING_TAG.match(html.unescape(str(t))))


# ── 3. DETEKTOR AUDIT (C1) ──────────────────────────────────────────────────
def dup_title_strict(t: str) -> bool:
    """Artefak pipeline: kalimat pertama diulang HARAFIAH di awal sisa teks."""
    parts = re.split(r"(?<=[.!?])\s+", str(t).strip(), maxsplit=1)
    if len(parts) < 2:
        return False
    a, b = _alnum(parts[0]), _alnum(parts[1])
    return len(a) >= 8 and b.find(a, 0, len(a) + 30) >= 0


def dup_title_para(t: str) -> bool:
    """Kemiripan token kalimat pertama vs awal sisa teks >= 0,70 (bisa parafrasa jurnalistik wajar)."""
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


dup_title = dup_title_para      # alias agar kode lama tetap jalan