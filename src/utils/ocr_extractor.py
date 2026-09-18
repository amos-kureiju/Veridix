import re
import io
import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR

# 1. Inisialisasi Singleton: Hanya dimuat 1 kali ke RAM
print("--> [OCR Engine] Memuat PaddleOCR Bahasa Indonesia...")
ocr_engine = PaddleOCR(use_angle_cls=True, lang='id', show_log=False)

def resize_image_for_speed(image_np: np.ndarray, max_width: int = 1000) -> np.ndarray:
    """
    Mengecilkan resolusi gambar raksasa ke lebar 1000px
    agar waktu proses di CPU turun dari 4.8 detik menjadi ~1.5 detik.
    """
    height, width = image_np.shape[:2]
    if width > max_width:
        scale = max_width / float(width)
        new_height = int(height * scale)
        image_np = cv2.resize(image_np, (max_width, new_height), interpolation=cv2.INTER_AREA)
    return image_np

def extract_text_from_image(image_bytes: bytes) -> dict:
    """
    Ekstraksi teks screenshot menggunakan PaddleOCR dengan optimasi kecepatan.
    """
    try:
        # Buka gambar dan ubah ke numpy array
        image_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image_pil)

        # Optimasi kecepatan: resize gambar
        image_optimized = resize_image_for_speed(image_np, max_width=1000)

        # Ekstraksi menggunakan PaddleOCR
        result = ocr_engine.ocr(image_optimized, cls=True)

        if not result or result[0] is None:
            return {
                "success": False,
                "text": "",
                "message": "Gambar tidak memuat teks atau gambar terlalu buram."
            }

        # Ambil teks hasil ekstraksi
        extracted_lines = [line[1][0] for line in result[0]]
        raw_text = " ".join(extracted_lines).strip()

        # Pembersihan artefak noise OCR
        cleaned_text = re.sub(r'[^\w\s.,!?\'"-]', ' ', raw_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        # Validasi batas minimal 50 karakter (khusus OCR)
        if len(cleaned_text) < 50:
            return {
                "success": False,
                "text": cleaned_text,
                "message": "Teks pada gambar kurang dari 50 karakter berita."
            }

        return {
            "success": True,
            "text": cleaned_text,
            "message": "Teks berhasil diekstrak dengan akurasi tinggi oleh PaddleOCR."
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "message": f"Gagal mengekstrak teks dari gambar: {str(e)}"
        }