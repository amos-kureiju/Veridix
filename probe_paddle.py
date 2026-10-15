# ── ATURAN WINDOWS: import torch WAJIB di baris paling awal! ─────────────────
import os
import sys

# Matikan PIR & oneDNN via environment variable sebelum Paddle aktif
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_onednn"] = "0"

import torch  # PyTorch DLL dimuat duluan agar shm.dll tidak konflik
import numpy as np
from PIL import Image, ImageDraw

import paddle
paddle.set_device("cpu")

from paddleocr import PaddleOCR

path_gambar = "data/sample_probe.png"
if not os.path.exists(path_gambar):
    os.makedirs("data", exist_ok=True)
    im = Image.new("RGB", (700, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)
    draw.text((40, 80), "KEMENTERIAN KEUANGAN MEMASTIKAN BANSOS 2026", fill=(0, 0, 0))
    im.save(path_gambar)

img = np.array(Image.open(path_gambar).convert("RGB"))

print("=" * 70)
print("PROBE PADDLEOCR 3.X (URUTAN DLL AMAN & PIR DISABLED)")
print("=" * 70)
print(f"PyTorch: {torch.__version__} | Device: {paddle.get_device()}")

# Inisialisasi engine tanpa parameter usang
ocr = PaddleOCR(lang="id")

# Uji 1: Metode predict() bawaan seri 3.x
print("\n--- Uji 1: ocr.predict(input=img) ---")
try:
    res_pred = ocr.predict(img)
    print("Uji 1 SUKSES!")
    print("Tipe output:", type(res_pred))
    if isinstance(res_pred, list) and len(res_pred) > 0:
        r = res_pred[0]
        if hasattr(r, "keys"):
            print("Keys:", list(r.keys()))
            for k in ("rec_text", "rec_texts", "rec_scores"):
                if k in r:
                    print(f"  {k}:", r[k])
except Exception as e:
    print("Uji 1 GAGAL:", e)

# Uji 2: Metode predict() dengan input jalur berkas
print("\n--- Uji 2: ocr.predict(input=path_gambar) ---")
try:
    res_file = ocr.predict(path_gambar)
    print("Uji 2 SUKSES!")
    if isinstance(res_file, list) and len(res_file) > 0:
        r = res_file[0]
        if hasattr(r, "keys"):
            for k in ("rec_text", "rec_texts", "rec_scores"):
                if k in r:
                    print(f"  {k}:", r[k])
except Exception as e:
    print("Uji 2 GAGAL:", e)

print("=" * 70)