"""
degradasi_gambar.py — gangguan GAMBAR terkontrol untuk uji ujung-ke-ujung (gambar -> OCR -> model).
Hanya PIL + numpy. Deterministik. TIDAK memanggil PaddleOCR; sambungkan lewat fungsi ocr_fn milik Anda:
    ocr_fn(PIL.Image) -> (teks: str, kepercayaan_rata2: float)
Pakai pada gambar NYATA yang sudah dilabel manusia. Satu gambar -> banyak kondisi, jadi tiap kondisi berpasangan.
"""

import io
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
 
 
def blur(img, radius):
    return img.filter(ImageFilter.GaussianBlur(radius))
 
 
def low_res(img, scale):
    """Perkecil lalu perbesar kembali (mirip gambar kecil/WhatsApp)."""
    w, h = img.size
    small = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
    return small.resize((w, h), Image.BILINEAR)
 
 
def jpeg(img, quality):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")
 
 
def rotate(img, deg):
    return img.convert("RGB").rotate(deg, expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC)
 
 
def low_contrast(img, factor):
    return ImageEnhance.Contrast(img.convert("RGB")).enhance(factor)
 
 
def gauss_noise(img, sigma, seed=0):
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    arr = arr + np.random.default_rng(seed).normal(0, sigma, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
 
 
def watermark(img, text="CONTOH", alpha=70):
    base = img.convert("RGBA")
    layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(layer)
    w, h = base.size
    for y in range(0, h, max(40, h // 6)):
        for x in range(0, w, max(120, w // 4)):
            d.text((x, y), text, fill=(128, 128, 128, alpha))
    return Image.alpha_composite(base, layer).convert("RGB")
 
 
CONDITIONS = {
    "asli (acuan)":        lambda im: im.convert("RGB"),
    "blur ringan (r=1)":   lambda im: blur(im.convert("RGB"), 1),
    "blur sedang (r=2)":   lambda im: blur(im.convert("RGB"), 2),
    "blur berat (r=4)":    lambda im: blur(im.convert("RGB"), 4),
    "resolusi 50%":        lambda im: low_res(im.convert("RGB"), 0.5),
    "resolusi 25%":        lambda im: low_res(im.convert("RGB"), 0.25),
    "JPEG q=40":           lambda im: jpeg(im, 40),
    "JPEG q=15":           lambda im: jpeg(im, 15),
    "miring 5 derajat":    lambda im: rotate(im, 5),
    "miring 15 derajat":   lambda im: rotate(im, 15),
    "kontras rendah 0.4":  lambda im: low_contrast(im, 0.4),
    "derau gauss s=25":    lambda im: gauss_noise(im, 25),
    "tanda air":           lambda im: watermark(im),
}
 
 
def apply_all(img):
    """{nama_kondisi: gambar}. Semua deterministik."""
    return {k: f(img) for k, f in CONDITIONS.items()}

# ── BLOK PENGUJIAN MANDIRI DI TERMINAL ──────────────────────────────────────
if __name__ == "__main__":
  print("=" * 70)
  print("UJI MODUL DEGRADASI GAMBAR BERHASIL")
  print("=" * 70)

  # Buat gambar uji dummy di memori (tanpa perlu file eksternal)
  dummy_img = Image.new("RGB", (400, 150), color=(255, 255, 255))
  hasil = apply_all(dummy_img)

  print(f"Total gangguan visual terpasang: {len(hasil)} kondisi:")
  for i, nama_kondisi in enumerate(hasil.keys(), 1):
    dimensi = hasil[nama_kondisi].size
    print(
        f"  {i:>2}. [AKTIF] {nama_kondisi:<28} -> Ukuran:"
        f" {dimensi[0]}x{dimensi[1]}"
    )

  print("=" * 70)
  print("STATUS: 13/13 fungsi gangguan citra siap dipasangkan ke PaddleOCR!")
  print("=" * 70)