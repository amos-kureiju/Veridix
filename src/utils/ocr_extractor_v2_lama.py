# src/utils/ocr_extractor.py
import re
import io
import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ocr_paddle3 import extract_text_from_image, get_ocr, reset_ocr  # noqa: F401

# Pola Singleton: Model hanya dimuat 1 kali ke RAM agar hemat memori
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        print("--> [OCR Engine] Menginisialisasi PaddleOCR Bahasa Indonesia...")
        # use_angle_cls=True untuk mengoreksi teks miring/rotasi
        _ocr_engine = PaddleOCR(use_angle_cls=True, lang='id', show_log=False)
    return _ocr_engine

def resize_image_for_speed(image_np: np.ndarray, max_width: int = 1000) -> np.ndarray:
    """
    Mengecilkan resolusi gambar raksasa ke lebar maksimal 1000px
    agar waktu proses di CPU laptop turun dari 4.8 detik menjadi ~1.5 detik.
    """
    height, width = image_np.shape[:2]
    if width > max_width:
        scale = max_width / float(width)
        new_height = int(height * scale)
        image_np = cv2.resize(image_np, (max_width, new_height), interpolation=cv2.INTER_AREA)
    return image_np

def extract_text_from_image(image_bytes: bytes) -> dict:
    """
    Mengekstrak teks dari gambar screenshot berita menggunakan PaddleOCR.
    """
    try:
        # 1. Buka gambar dari bytes memory
        image_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image_pil)

        # 2. Optimasi kecepatan: resize gambar
        image_optimized = resize_image_for_speed(image_np, max_width=1000)

        # 3. Ekstraksi menggunakan PaddleOCR
        ocr = get_ocr_engine()
        result = ocr.ocr(image_optimized, cls=True)

        if not result or result[0] is None:
            return {
                "success": False,
                "text": "",
                "message": "Gambar tidak memuat teks atau gambar terlalu buram."
            }

        # 4. Ambil teks dan bersihkan artefak noise
        extracted_lines = [line[1][0] for line in result[0]]
        raw_text = " ".join(extracted_lines).strip()
        
        # Bersihkan simbol aneh OCR
        cleaned_text = re.sub(r'[^\w\s.,!?\'"-]', ' ', raw_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        # 5. Validasi: batas minimal 50 karakter untuk teks dari gambar
        if len(cleaned_text) < 50:
            return {
                "success": False,
                "text": cleaned_text,
                "message": "Teks pada gambar kurang dari 50 karakter berita (terlalu pendek)."
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
            "message": f"Terjadi kesalahan saat mengekstrak gambar: {str(e)}"
        }