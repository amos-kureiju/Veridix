"""buat_sampel_uji.py — Generator citra sintetis terisolasi dalam folder 'data/sintetis/'."""

import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DATA_DIR = Path("data/sintetis")


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


def buat_semua_sampel():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    font_utama = dapatkan_font(26)

    print("=" * 75)
    print(f"MEMBUAT CITRA UJI SINTETIS DI FOLDER '{DATA_DIR}'")
    print("=" * 75)

    # 1. Sampel Teks Panjang (104 karakter persis sesuai acuan, TANPA banner judul)
    p1 = DATA_DIR / "sample_panjang_sintetis.png"
    img1 = Image.new("RGB", (900, 240), color=(255, 255, 255))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle([(15, 15), (885, 225)], outline=(210, 215, 220), width=2)

    teks_panjang = (
        "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial "
        "tahun anggaran baru harus tepat sasaran."
    )
    baris1 = textwrap.wrap(teks_panjang, width=52)
    y_offset = 55
    for b in baris1:
        draw1.text((35, y_offset), b, fill=(20, 20, 20), font=font_utama)
        y_offset += 45
    img1.save(p1, format="PNG")
    print(f"[OK] 1. Teks Panjang Sintetis : {p1} (104 karakter, identik acuan)")

    # 2. Sampel Teks Pendek (49 karakter, menguji penolakan mutu)
    p2 = DATA_DIR / "sample_probe_sintetis.png"
    img2 = Image.new("RGB", (850, 180), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([(15, 15), (835, 165)], outline=(210, 215, 220), width=2)
    draw2.text((35, 70), "KEMENTERIAN KEUANGAN MEMASTIKAN BANSOS TAHUN 2026", fill=(30, 30, 30), font=font_utama)
    img2.save(p2, format="PNG")
    print(f"[OK] 2. Teks Pendek Sintetis  : {p2} (49 karakter)")

    # 3. Sampel Teks Buram (Blur 3.8px)
    p3 = DATA_DIR / "sample_buram_sintetis.png"
    img3 = Image.new("RGB", (850, 240), color=(248, 248, 248))
    draw3 = ImageDraw.Draw(img3)
    draw3.rectangle([(15, 15), (835, 225)], outline=(220, 220, 220), width=2)
    teks_buram = (
        "Rapat pleno rekapitulasi penghitungan suara pemilu "
        "berlangsung secara tertutup di gedung bawaslu daerah."
    )
    y_offset = 55
    for b in textwrap.wrap(teks_buram, width=48):
        draw3.text((35, y_offset), b, fill=(80, 80, 80), font=font_utama)
        y_offset += 45
    img3_buram = img3.filter(ImageFilter.GaussianBlur(radius=3.8))
    img3_buram.save(p3, format="PNG")
    print(f"[OK] 3. Teks Buram Sintetis   : {p3} (menguji MUTU_CONF/BARIS_RENDAH)")

    # 4. Sampel Tanpa Teks (Bentuk Geometris Murni)
    p4 = DATA_DIR / "sample_tanpa_teks_sintetis.png"
    img4 = Image.new("RGB", (600, 300), color=(235, 240, 245))
    draw4 = ImageDraw.Draw(img4)
    draw4.ellipse([(50, 50), (220, 220)], fill=(70, 130, 180), outline=(50, 100, 150), width=3)
    draw4.rectangle([(280, 70), (520, 230)], fill=(200, 140, 80), outline=(170, 110, 60), width=3)
    img4.save(p4, format="PNG")
    print(f"[OK] 4. Tanpa Teks Sintetis   : {p4} (menguji MUTU_TIDAK_ADA_TEKS)")

    # 5. Sampel Format BMP Tidak Didukung
    p5 = DATA_DIR / "sample_tidak_didukung.bmp"
    img5 = Image.new("RGB", (500, 180), color=(255, 255, 255))
    draw5 = ImageDraw.Draw(img5)
    draw5.text((30, 70), "Berkas Gambar Format BMP", fill=(0, 0, 0), font=font_utama)
    img5.save(p5, format="BMP")
    print(f"[OK] 5. Format BMP Tidak Sah  : {p5} (menguji INPUT_FORMAT_TIDAK_DIDUKUNG)")

    print("=" * 75)
    import json
    manifest_data = [
        {
            "id": "S01",
            "kategori": "teks_panjang_jelas",
            "gambar": "data/sintetis/sample_panjang_sintetis.png",
            "deskripsi": "Teks panjang 104 karakter persis acuan, menguji baseline OCR diterima",
            "transkripsi_manual": "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial tahun anggaran baru harus tepat sasaran."
        },
        {
            "id": "S02",
            "kategori": "teks_pendek",
            "gambar": "data/sintetis/sample_probe_sintetis.png",
            "deskripsi": "Teks pendek 49 karakter, menguji penolakan mutu MUTU_TEKS_PENDEK",
            "transkripsi_manual": "KEMENTERIAN KEUANGAN MEMASTIKAN BANSOS TAHUN 2026"
        },
        {
            "id": "S03",
            "kategori": "buram",
            "gambar": "data/sintetis/sample_buram_sintetis.png",
            "deskripsi": "Teks kabur Gaussian blur 3.8px, menguji MUTU_CONF_RENDAH / MUTU_BARIS_RENDAH",
            "transkripsi_manual": "Rapat pleno rekapitulasi penghitungan suara pemilu berlangsung secara tertutup di gedung bawaslu daerah."
        },
        {
            "id": "S04",
            "kategori": "tanpa_teks",
            "gambar": "data/sintetis/sample_tanpa_teks_sintetis.png",
            "deskripsi": "Grafis geometris abstrak tanpa teks, menguji MUTU_TIDAK_ADA_TEKS",
            "transkripsi_manual": ""
        },
        {
            "id": "S05",
            "kategori": "format_tidak_didukung",
            "gambar": "data/sintetis/sample_tidak_didukung.bmp",
            "deskripsi": "Berkas Windows BMP, menguji penolakan masukan INPUT_FORMAT_TIDAK_DIDUKUNG",
            "transkripsi_manual": "Berkas Gambar Format BMP"
        }
    ]

    manifest_path = DATA_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    print(f"[OK] 6. Manifest Pasangan     : {manifest_path} (5 kondisi uji lengkap)")
    print("SELESAI: Berkas sintetis tersimpan tanpa menimpa baseline 'data/'")


def main():
    buat_semua_sampel()


if __name__ == "__main__":
    main()