import easyocr
import io
from PIL import Image
import numpy as np

# Pola Singleton: Model hanya dimuat 1 kali ke RAM
_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        print("--> [OCR Engine] Memuat model EasyOCR (Bahasa Indonesia & Inggris)...")
        # gpu=False untuk CPU laptop lokal
        _ocr_reader = easyocr.Reader(['id', 'en'], gpu=False)
    return _ocr_reader

def extract_text_from_image(image_bytes: bytes) -> dict:
    """
    Mengekstrak teks dari gambar screenshot berita/WA.
    Mengembalikan dictionary: status, teks hasil ekstraksi, dan pesan.
    """
    try:
        # 1. Buka file gambar dari memory
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)

        # 2. Ekstraksi teks menggunakan EasyOCR
        reader = get_ocr_reader()
        results = reader.readtext(image_np, detail=0)
        extracted_text = " ".join(results).strip()

        # 3. Filter pengaman: teks minimal 30 karakter (membuang gambar logo/foto kosong)
        if len(extracted_text) < 30:
            return {
                "success": False,
                "text": extracted_text,
                "message": "Teks pada gambar terlalu pendek (minimal 30 karakter berita). Pastikan gambar memuat teks berita yang jelas."
            }

        return {
            "success": True,
            "text": extracted_text,
            "message": "Teks berhasil diekstrak."
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "message": f"Gagal mengekstrak gambar: {str(e)}"
        }