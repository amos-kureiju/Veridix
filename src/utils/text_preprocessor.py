import re

def clean_standard_text(text) -> str:
    """
    Pembersihan standar untuk semua teks (Teks langsung maupun OCR).
    Stopwords dan imbuhan TIDAK dihapus.
    """

    # 1. Hapus URL
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # 2. Hapus Tag HTML
    text = re.sub(r'<.*?>', '', text)
    # 3. Normalisasi spasi berlebih dan ganti baris baru jadi spasi
    text = re.sub(r'\s+', ' ', text).strip()
    # 4. Lowercase
    return text.lower()

def clean_ocr_artifacts(text: str) -> str:
    """
    Pembersihan ekstra KHUSUS untuk teks hasil OCR gambar.
    Membuang noise simbol pipa, karakter non-ASCII, dan glitch pembacaan scanner.
    """
    # 1. Hapus karakter visual noise khas OCR (pipa, tilde, garis bawah berlebih)
    text = re.sub(r'[\|\\_~^©®™«»]', ' ', text)
    # 2. Hapus karakter non-ASCII yang aneh
    text = text.encode('ascii', 'ignore').decode('utf-8')
    # 3. Lanjutkan ke pembersihan standar
    return clean_standard_text(text)