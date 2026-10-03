import re

# REGEX CERDAS PENANGKAL POSITIONAL BIAS INDOBERT
# Menjamin pembersihan tuntas dari kata pembuka hingga 'bahwa' atau ':'
_SOCIAL_PREFIX_PATTERN = re.compile(
    r'^\s*('
    # 1. Menangkap: "Beredar [apapun hingga 80 karakter] bahwa/terkait/menyebut:"
    r'beredar\b.*?\b(bahwa|terkait|menyebutkan|menyebut|tentang)\s*:?\s*|'
    # 2. Menangkap: "Beredar [video/kabar/narasi di grup WA/medsos]:"
    r'beredar\b[^\n\.\:\?]{0,70}?[:\-–—]\s*|'
    # 3. Menangkap: "Viral [apapun hingga 80 karakter] bahwa/terkait:"
    r'viral\b.*?\b(bahwa|terkait|menyebutkan|menyebut|tentang)\s*:?\s*|'
    # 4. Menangkap: "Viral di TikTok/Twitter/Medsos:"
    r'viral\b[^\n\.\:\?]{0,50}?[:\-–—]\s*|'
    # 5. Menangkap: "Berikut teksnya/narasinya/faktanya:"
    r'berikut\s+(teksnya|narasinya|isi\s+pesannya|informasinya|klarifikasinya|faktanya)\s*:?\s*|'
    # 6. Menangkap: "Dapat dari grup WA / WhatsApp / Telegram:"
    r'dapat\s+(dari\s+)?(grup\s+)?(wa|whatsapp|telegram|sebelah|teman)\s*:?\s*|'
    # 7. Sapaan khas medsos & ajakan share
    r'guys[\s,!]+|'
    r'info\s+(penting|viral|terbaru|hoax)?\s*:?\s*|'
    r'(tolong\s+)?di\s*share\s*(ya|dong)?\s*[,!]?\s*'
    r')',
    re.IGNORECASE
)

def sanitize_social_prefix(text: str) -> str:
    """
    Membersihkan total seluruh pengantar media sosial hingga ke pokok berita asli
    agar tidak memicu positional attention collapse pada IndoBERT.
    """
    cleaned = _SOCIAL_PREFIX_PATTERN.sub('', str(text)).strip()
    
    # Pengaman kedua: Bersihkan sisa kata hubung menggantung di awal (jika ada)
    cleaned = re.sub(r'^(bahwa|terkait|tentang|di\s+media\s+sosial|di\s+medsos)\s*:?\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^[:\s,\-–—]+', '', cleaned).strip()
    
    # Jika hasil pembersihan minimal 3 kata, gunakan hasil bersih. Jika tidak, kembalikan asli.
    return cleaned if len(cleaned.split()) >= 3 else str(text).strip()


def clean_standard_text(text: str, do_lower: bool = False) -> str:
    """
    Pembersihan standar untuk semua teks.
    """
    # 1. Hapus URL
    text = re.sub(r'https?://\S+|www\.\S+', '', str(text))
    # 2. Hapus Tag HTML
    text = re.sub(r'<.*?>', '', text)
    # 3. Normalisasi spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()
    # 4. Casing
    return text.lower() if do_lower else text


def clean_ocr_artifacts(text: str) -> str:
    """
    Pembersihan ekstra KHUSUS untuk teks hasil OCR gambar.
    """
    text = re.sub(r'[\|\\_~^©®™«»]', ' ', str(text))
    text = text.encode('ascii', 'ignore').decode('utf-8')
    return clean_standard_text(text)