##ocr_pipeline.py — Jalur tunggal gambar -> teks siap verifikasi.

import hashlib
import io
import json
import logging
import os
import re
import time
import warnings
import inspect

import numpy as np
from PIL import Image, UnidentifiedImageError
 
try:
    from . import ocr_extractor as ex
except ImportError:  # dijalankan sebagai skrip/uji mandiri
    import ocr_extractor as ex
 
logger = logging.getLogger(__name__)
 
VERSI_PIPELINE = "1.0"
FORMAT_DIIZINKAN = ("PNG", "JPEG", "MPO", "WEBP", "BMP")   # MPO = varian JPEG dari sebagian kamera ponsel
 
KATEGORI_OK = "OK"
KATEGORI_INPUT = "TOLAK_INPUT"
KATEGORI_KUALITAS = "TOLAK_KUALITAS"
KATEGORI_MESIN = "GALAT_MESIN"
SEMUA_KATEGORI = (KATEGORI_OK, KATEGORI_INPUT, KATEGORI_KUALITAS, KATEGORI_MESIN)
 
_PEMISAH = re.compile(r"[\u2028\u2029\u000b\u000c\u0085]")          # jadi spasi, bukan dihapus
_KONTROL = re.compile(r"[\u0000-\u0008\u000e-\u001f\u007f\u200b-\u200f\ufeff]")
 
 
# ----------------------------------------------------------------------------------
# Kebijakan & pesan
# ----------------------------------------------------------------------------------
def pesan_pengguna(kode):
    """Pesan ramah pengguna per kode (tanpa detail internal)."""
    mb = ex.MAX_BYTES // (1024 * 1024)
    juta = ex.MAX_PIXELS / 1_000_000
    return {
        "OK": "Teks berhasil dibaca dan memenuhi syarat untuk diverifikasi.",
        "INPUT_TIPE_TIDAK_DIDUKUNG": "Jenis masukan tidak didukung. Unggah berkas gambar.",
        "INPUT_KOSONG": "Berkas kosong.",
        "INPUT_UKURAN_BERKAS": f"Ukuran berkas melebihi {mb} MB. Kompres atau perkecil gambar.",
        "INPUT_FORMAT_TIDAK_DIDUKUNG": "Format gambar tidak didukung. Gunakan PNG, JPEG, WebP, atau BMP.",
        "INPUT_PIKSEL_BERLEBIH": f"Resolusi gambar terlalu besar (maksimal {juta:g} juta piksel). Perkecil resolusinya.",
        "INPUT_TIDAK_TERBACA": "Berkas bukan gambar yang dapat dibaca, atau rusak.",
        "INPUT_DITOLAK": "Gambar ditolak karena tidak memenuhi syarat masukan.",
        "MUTU_TIDAK_ADA_TEKS": "Tidak ada teks yang terbaca pada gambar.",
        "MUTU_TEKS_PENDEK": "Teks yang terbaca terlalu pendek untuk diverifikasi.",
        "MUTU_CONF_RENDAH": "Kualitas pembacaan teks rendah. Gunakan gambar yang lebih jelas.",
        "MUTU_CONF_TIDAK_TERSEDIA": "Tingkat kepercayaan pembacaan teks tidak tersedia, sehingga tidak dapat dinilai.",
        "MUTU_BARIS_RENDAH": "Terlalu banyak baris teks yang sulit dibaca.",
        "MUTU_TOKEN_CAMPURAN": "Terlalu banyak token campuran huruf dan angka; kemungkinan salah baca.",
        "MESIN_KELUARAN_TIDAK_VALID": "Keluaran mesin OCR tidak konsisten sehingga tidak dinilai. Periksa teks mentah atau coba lagi.",
        "MESIN_GAGAL": "Mesin OCR mengalami kegagalan. Coba lagi nanti.",
    }.get(kode, "Gambar tidak dapat diproses.")
 
 
def kebijakan(aturan=None, sambung_tanda_hubung=False):
    p = inspect.signature(ex._to_path).parameters
    return {
        "max_bytes": ex.MAX_BYTES,
        "max_pixels": ex.MAX_PIXELS,
        "format_diizinkan": list(FORMAT_DIIZINKAN),
        "max_width_resize": p["max_width"].default,
        "padding_px": p["padding_border"].default,
        "aturan_gerbang": dict(ex.ATURAN_AWAL, **(aturan or {})),
        "sambung_tanda_hubung": bool(sambung_tanda_hubung),
        "versi_pipeline": VERSI_PIPELINE,
    }


def hash_kebijakan(aturan=None, sambung_tanda_hubung=False):
    isi = json.dumps(kebijakan(aturan, sambung_tanda_hubung), sort_keys=True,
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(isi).hexdigest()
 
 
# ----------------------------------------------------------------------------------
# Validasi unggahan
# ----------------------------------------------------------------------------------
def inspeksi_unggahan(src):
    """Validasi masukan sebelum OCR. Mengembalikan (info_berkas, sumber_untuk_ocr).
    Melempar ex.GambarDitolak (dengan `kode` INPUT_*) bila ditolak."""
    info = {"format": None, "lebar": None, "tinggi": None, "ukuran_byte": None, "sha256": None}
    data = None
 
    if isinstance(src, (str, os.PathLike)):
        p = os.fspath(src)
        try:
            if not os.path.isfile(p):
                raise ex.GambarDitolak("Berkas tidak ditemukan.", "INPUT_TIDAK_TERBACA")
            with open(p, "rb") as fh:
                data = fh.read(ex.MAX_BYTES + 1)      # jangan baca lebih dari batas
        except ex.GambarDitolak:
            raise
        except OSError as e:
            raise ex.GambarDitolak("Berkas tidak dapat dibaca.", "INPUT_TIDAK_TERBACA") from e
        if len(data) == 0:
            raise ex.GambarDitolak("Berkas kosong.", "INPUT_KOSONG")
        if len(data) > ex.MAX_BYTES:
            raise ex.GambarDitolak("Ukuran berkas gambar melebihi batas.", "INPUT_UKURAN_BERKAS")
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError as e:
            raise ex.GambarDitolak("Berkas tidak dapat dibaca.", "INPUT_TIDAK_TERBACA") from e
    elif isinstance(src, (bytes, bytearray)):
        data = bytes(src)
        if not data:
            raise ex.GambarDitolak("Berkas kosong.", "INPUT_KOSONG")
        if len(data) > ex.MAX_BYTES:
            raise ex.GambarDitolak("Ukuran gambar melebihi batas.", "INPUT_UKURAN_BERKAS")
    elif isinstance(src, Image.Image):
        size = src.size
    elif isinstance(src, np.ndarray):
        if src.ndim not in (2, 3) or src.size == 0:
            raise ex.GambarDitolak("Array gambar tidak valid.", "INPUT_TIPE_TIDAK_DIDUKUNG")
        size = (src.shape[1], src.shape[0])
    else:
        raise ex.GambarDitolak(f"Jenis masukan tidak didukung: {type(src).__name__}",
                               "INPUT_TIPE_TIDAK_DIDUKUNG")
 
    if data is not None:
        info["ukuran_byte"] = len(data)
        info["sha256"] = hashlib.sha256(data).hexdigest()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", Image.DecompressionBombWarning)  # ditolak tegas di bawah
                with Image.open(io.BytesIO(data)) as im:
                    info["format"], size = im.format, im.size
        except Image.DecompressionBombError as e:
            raise ex.GambarDitolak("Jumlah piksel gambar melebihi batas.", "INPUT_PIKSEL_BERLEBIH") from e
        except (UnidentifiedImageError, OSError, ValueError) as e:
            raise ex.GambarDitolak("Berkas bukan gambar yang dapat dibaca.", "INPUT_TIDAK_TERBACA") from e
        if info["format"] not in FORMAT_DIIZINKAN:
            raise ex.GambarDitolak(f"Format {info['format']} tidak didukung.", "INPUT_FORMAT_TIDAK_DIDUKUNG")
 
    info["lebar"], info["tinggi"] = int(size[0]), int(size[1])
    ex._cek_piksel(size, "masukan")
    return info, (data if data is not None else src)
 
 
# ----------------------------------------------------------------------------------
# Pembersihan teks OCR (tidak menggantikan praproses klasifikasi di aplikasi)
# ----------------------------------------------------------------------------------
def bersihkan_teks_ocr(teks, sambung_tanda_hubung=False):
    """Buang karakter kontrol/zero-width, rapikan spasi. Teks mentah tetap disimpan terpisah."""
    t = _PEMISAH.sub(" ", teks)
    t = _KONTROL.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    if sambung_tanda_hubung:
        t = re.sub(r"(\w)-\s+(\w)", r"\1\2", t)
    return t
 
 
# ----------------------------------------------------------------------------------
# Pipeline utama
# ----------------------------------------------------------------------------------
def _kerangka(aturan, sambung_tanda_hubung=False):
    return {
        "versi_pipeline": VERSI_PIPELINE, "kategori": None, "kode": None, "dapat_dinilai": False,
        "pesan": "", "detail_teknis": None, "alasan": [],
        "teks_mentah": "", "teks_bersih": "", "lines": [], "scores": [], "fitur": None,
        "aturan": dict(ex.ATURAN_AWAL, **(aturan or {})), "berkas": None,
        "durasi_detik": {}, "hash_kebijakan": hash_kebijakan(aturan, sambung_tanda_hubung),
        "sambung_tanda_hubung": bool(sambung_tanda_hubung),
    }
 
 
def _tutup(h, t0, kategori, kode, pesan=None, detail=None):
    h.update(kategori=kategori, kode=kode, pesan=pesan or pesan_pengguna(kode), detail_teknis=detail,
             dapat_dinilai=(kategori == KATEGORI_OK))
    h["durasi_detik"]["total"] = round(time.perf_counter() - t0, 4)
    return h
 
 
def proses_gambar(src, *, sambung_tanda_hubung=False, aturan=None, ocr_fn=None):
    """Proses satu gambar. Selalu mengembalikan dict laporan (tidak melempar untuk galat yang
    dapat diantisipasi). `ocr_fn(src) -> (lines, scores)` dapat disuntikkan untuk pengujian."""
    t0 = time.perf_counter()
    h = _kerangka(aturan)
 
    # 1. validasi unggahan
    t = time.perf_counter()
    try:
        info, src_ocr = inspeksi_unggahan(src)
    except ex.GambarDitolak as e:
        h["durasi_detik"]["validasi"] = round(time.perf_counter() - t, 4)
        return _tutup(h, t0, KATEGORI_INPUT, e.kode, detail=str(e))
    h["berkas"] = info
    h["durasi_detik"]["validasi"] = round(time.perf_counter() - t, 4)
 
    # 2. ekstraksi OCR
    t = time.perf_counter()
    try:
        lines, scores = (ocr_fn or ex.ocr_lines)(src_ocr)
        ex.validasi_keluaran(lines, scores)
    except ex.GambarDitolak as e:        # pemeriksaan lapis kedua di extractor (mis. piksel setelah padding)
        h["durasi_detik"]["ocr"] = round(time.perf_counter() - t, 4)
        return _tutup(h, t0, KATEGORI_INPUT, e.kode, detail=str(e))
    except ex.GalatKeluaranOCR as e:
        h["durasi_detik"]["ocr"] = round(time.perf_counter() - t, 4)
        h["teks_mentah"] = ex.join_lines(e.teks_mentah)
        h["teks_bersih"] = bersihkan_teks_ocr(h["teks_mentah"], sambung_tanda_hubung)
        logger.warning("Keluaran OCR tidak valid: %s", e)
        return _tutup(h, t0, KATEGORI_MESIN, "MESIN_KELUARAN_TIDAK_VALID", detail=str(e))
    except Exception as e:
        h["durasi_detik"]["ocr"] = round(time.perf_counter() - t, 4)
        logger.exception("OCR gagal")
        return _tutup(h, t0, KATEGORI_MESIN, "MESIN_GAGAL", detail=f"{type(e).__name__}: {e}")
    h["durasi_detik"]["ocr"] = round(time.perf_counter() - t, 4)
    h["lines"], h["scores"] = list(lines), [float(x) for x in scores]
 
    # 3. pembersihan + gerbang kualitas
    t = time.perf_counter()
    h["teks_mentah"] = ex.join_lines(h["lines"])
    h["teks_bersih"] = bersihkan_teks_ocr(h["teks_mentah"], sambung_tanda_hubung)
    h["fitur"] = ex.fitur_kualitas(h["teks_bersih"], h["scores"])
    alasan = ex.putuskan_berkode(h["fitur"], aturan)
    h["durasi_detik"]["gerbang"] = round(time.perf_counter() - t, 4)
    if alasan:
        h["alasan"] = [{"kode": k, "pesan": p} for k, p in alasan]
        pesan = "; ".join(dict.fromkeys(pesan_pengguna(k) for k, _ in alasan))
        return _tutup(h, t0, KATEGORI_KUALITAS, alasan[0][0], pesan=pesan,
                      detail="; ".join(p for _, p in alasan))
    return _tutup(h, t0, KATEGORI_OK, "OK")
 
 
def ekstrak_untuk_aplikasi(src, sambung_tanda_hubung=False, aturan=None, ocr_fn=None):
    """Pengganti langsung ocr_extractor.extract_text_from_image: bentuk lama + kolom baru.
    success=True berarti OCR selesai (hasil bisa layak atau ditolak mutu); False untuk
    penolakan masukan atau galat mesin."""
    h = proses_gambar(src, sambung_tanda_hubung=sambung_tanda_hubung, aturan=aturan, ocr_fn=ocr_fn)
    selesai = h["kategori"] in (KATEGORI_OK, KATEGORI_KUALITAS)
    return dict(
        success=selesai, message=h["pesan"], text=h["teks_bersih"] if selesai else "",
        lines=h["lines"], scores=h["scores"], fitur=h["fitur"], dapat_dinilai=h["dapat_dinilai"],
        alasan=[a["pesan"] for a in h["alasan"]] or ([] if h["dapat_dinilai"] else [h["pesan"]]),
        teks_mentah=h["teks_mentah"], kategori=h["kategori"], kode=h["kode"], laporan=h,
    )