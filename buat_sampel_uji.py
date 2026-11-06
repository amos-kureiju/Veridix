# Menghasilkan 5 variasi gambar uji OCR

from pathlib import Path
import textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Muat font Windows Arial yang tajam (dengan fallback aman)
def dapatkan_font(ukuran=26):
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for fp in font_paths:
        if Path(fp).is_file():
            try:
                return ImageFont.truetype(fp, ukuran)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=ukuran)
    except Exception:
        return ImageFont.load_default()

font_utama = dapatkan_font(26)
font_judul = dapatkan_font(30)

print("=" * 75)
print("MEMBUAT 5 SAMPEL GAMBAR UJI DI FOLDER 'data/'")
print("=" * 75)

# ---------------------------------------------------------------------
# 1. SAMPEL TEKS PANJANG & JELAS (data/sample_panjang.png)
# ---------------------------------------------------------------------
p1 = DATA_DIR / "sample_panjang.png"
img1 = Image.new("RGB", (900, 320), color=(255, 255, 255))
draw1 = ImageDraw.Draw(img1)

# Frame gaya tangkapan layar berita medsos
draw1.rectangle([(20, 20), (880, 300)], outline=(220, 226, 230), width=2)
draw1.rectangle([(30, 30), (870, 75)], fill=(240, 244, 248))
draw1.text((45, 40), "[KUTIPAN RESMI PRESIDEN RI]", fill=(15, 30, 50), font=font_judul)

teks_panjang = (
    "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial "
    "tahun anggaran baru harus tepat sasaran."
)
baris1 = textwrap.wrap(teks_panjang, width=50)
y_offset = 105
for b in baris1:
    draw1.text((45, y_offset), b, fill=(20, 20, 20), font=font_utama)
    y_offset += 40

img1.save(p1, format="PNG")
print(f"[OK] 1. Teks Panjang Jelas   : {p1} (104 karakter)")

# ---------------------------------------------------------------------
# 2. SAMPEL TEKS PENDEK (data/sample_probe.png)
# ---------------------------------------------------------------------
p2 = DATA_DIR / "sample_probe.png"
img2 = Image.new("RGB", (850, 180), color=(255, 255, 255))
draw2 = ImageDraw.Draw(img2)
draw2.rectangle([(15, 15), (835, 165)], outline=(210, 215, 220), width=2)

teks_pendek = "KEMENTERIAN KEUANGAN MEMASTIKAN BANSOS TAHUN 2026"
draw2.text((35, 70), teks_pendek, fill=(30, 30, 30), font=font_utama)

img2.save(p2, format="PNG")
print(f"[OK] 2. Teks Pendek (<50 ch) : {p2} (49 karakter, menguji penolakan mutu)")

# ---------------------------------------------------------------------
# 3. SAMPEL BURAM / MUTU RENDAH (data/sample_buram.png)
# ---------------------------------------------------------------------
p3 = DATA_DIR / "sample_buram.png"
img3 = Image.new("RGB", (800, 260), color=(248, 248, 248))
draw3 = ImageDraw.Draw(img3)

teks_buram = (
    "Rapat pleno rekapitulasi penghitungan suara pemilu "
    "berlangsung secara tertutup di gedung bawaslu daerah."
)
baris3 = textwrap.wrap(teks_buram, width=45)
y_offset = 50
for b in baris3:
    draw3.text((40, y_offset), b, fill=(90, 90, 90), font=font_utama)
    y_offset += 40

# Terapkan efek Gaussian Blur agresif agar teks kabur/sulit dibaca
img3_buram = img3.filter(ImageFilter.GaussianBlur(radius=3.8))
img3_buram.save(p3, format="PNG")
print(f"[OK] 3. Teks Buram           : {p3} (menguji MUTU_CONF_RENDAH / MUTU_BARIS_RENDAH)")

# ---------------------------------------------------------------------
# 4. SAMPEL TANPA TEKS / GRAFIS KOSONG (data/sample_tanpa_teks.png)
# ---------------------------------------------------------------------
p4 = DATA_DIR / "sample_tanpa_teks.png"
img4 = Image.new("RGB", (600, 300), color=(235, 240, 245))
draw4 = ImageDraw.Draw(img4)

# Buat bentuk geometris abstrak tanpa satu pun huruf atau angka
draw4.ellipse([(50, 50), (220, 220)], fill=(70, 130, 180), outline=(50, 100, 150), width=3)
draw4.rectangle([(280, 70), (520, 230)], fill=(200, 140, 80), outline=(170, 110, 60), width=3)
draw4.polygon([(300, 260), (450, 40), (580, 260)], fill=(120, 180, 120))

img4.save(p4, format="PNG")
print(f"[OK] 4. Tanpa Teks           : {p4} (menguji penolakan MUTU_TIDAK_ADA_TEKS)")

# ---------------------------------------------------------------------
# 5. SAMPEL FORMAT TIDAK DIDUKUNG / BMP (data/sample_tidak_didukung.bmp)
# ---------------------------------------------------------------------
p5 = DATA_DIR / "sample_tidak_didukung.bmp"
img5 = Image.new("RGB", (500, 200), color=(255, 255, 255))
draw5 = ImageDraw.Draw(img5)
draw5.text((30, 80), "Berkas Gambar Format BMP", fill=(0, 0, 0), font=font_utama)

# Simpan dalam format Windows Bitmap (.bmp)
img5.save(p5, format="BMP")
print(f"[OK] 5. Format BMP Tidak Sah : {p5} (menguji penolakan INPUT_FORMAT_TIDAK_DIDUKUNG)")

print("=" * 75)
print("SELURUH BERKAS BERHASIL DIBUAT DAN SIAP DIUJI DI WEB!")