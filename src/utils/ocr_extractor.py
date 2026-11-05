"""
ocr_paddle3.py — Pembungkus resmi PaddleOCR 3.7.0 (Pengganti modul lama 2.x).
Fitur Unggulan:
  1. Proteksi DLL PyTorch & oneDNN CPU (Bebas shm.dll & PIR bug).
  2. Canvas Padding (15px): Mencegah huruf tepi terpotong seperti kasus 'residen'.
  3. Max Width Resize (1400px): Menjaga efisiensi latensi CPU pada gambar raksasa.
  4. Gerbang Kualitas Input: Menolak teks < 10 kata atau confidence < 0.60.
"""
import os
import io
import re
import math
import tempfile
import logging
import threading

logger = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024        # 10 MB
MAX_PIXELS = 40_000_000             # pembatas bom dekompresi

_OCR_LOCK = threading.RLock()      # reentrant: ocr_lines() -> get_ocr() memakai kunci yang sama

os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
try:
    import torch  # noqa: F401  (muat DLL PyTorch lebih dulu di Windows)
except Exception:
    pass

import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = MAX_PIXELS  # setelah impor PIL (hanya peringatan; batas tegas di _cek_piksel)

OCR_KWARGS = dict(lang="id")
_OCR = None


class GambarDitolak(ValueError):
    """Gambar ditolak sebelum pemrosesan berat (ukuran berkas / jumlah piksel)."""


class GalatKeluaranOCR(Exception):
    """Keluaran OCR tidak konsisten. Teks mentah dipertahankan untuk pemeriksaan."""
    def __init__(self, pesan, teks_mentah=None):
        super().__init__(pesan)
        self.teks_mentah = list(teks_mentah or [])


def _cek_piksel(size, tahap):
    w, h = size
    if w * h > MAX_PIXELS:
        raise GambarDitolak(f"Jumlah piksel {tahap} ({w}x{h}) melebihi batas {MAX_PIXELS}.")


def _daftar(x):
    """Aman untuk list maupun ndarray (hindari `x or []` yang rancu pada array)."""
    return [] if x is None else list(x)


def get_ocr():
    global _OCR
    with _OCR_LOCK:
        if _OCR is None:
            from paddleocr import PaddleOCR
            _OCR = PaddleOCR(**OCR_KWARGS)
        return _OCR


def reset_ocr():
    global _OCR
    with _OCR_LOCK:
        _OCR = None


def _to_path(src, max_width=1400, padding_border=15):
    """Standarkan masukan ke PNG sementara. Mengembalikan (path, True)."""
    dibuka = None  # gambar yang dibuka fungsi ini; wajib ditutup
    try:
        if isinstance(src, (str, os.PathLike)):
            if os.path.getsize(str(src)) > MAX_BYTES:
                raise GambarDitolak("Ukuran berkas gambar melebihi batas.")
            img = dibuka = Image.open(str(src))
        elif isinstance(src, (bytes, bytearray)):
            if len(src) > MAX_BYTES:
                raise GambarDitolak("Ukuran gambar melebihi batas.")
            img = dibuka = Image.open(io.BytesIO(bytes(src)))
        elif isinstance(src, Image.Image):
            img = src
        elif isinstance(src, np.ndarray):
            img = Image.fromarray(src)
        else:
            raise TypeError(f"Jenis masukan tidak didukung: {type(src)}")

        _cek_piksel(img.size, "masukan")   # sebelum dekode/konversi (ukuran dibaca dari header)

        # Orientasi EXIF (foto ponsel)
        img = ImageOps.exif_transpose(img)

        # Transparansi: tempelkan di atas latar putih, bukan hitam
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            latar = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            img = Image.alpha_composite(latar, rgba).convert("RGB")
        else:
            img = img.convert("RGB")

        w, h = img.size
        if w > max_width:
            skala = max_width / float(w)
            img = img.resize((max_width, max(1, int(round(h * skala)))), Image.Resampling.LANCZOS)

        # Padding menambah piksel (gambar tinggi-sempit bisa membesar drastis): cek SEBELUM expand
        _cek_piksel((img.size[0] + 2 * padding_border, img.size[1] + 2 * padding_border), "akhir")
        if padding_border > 0:
            img = ImageOps.expand(img, border=padding_border, fill="white")

        fd, p = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            img.save(p, format="PNG")
        except Exception:
            if os.path.exists(p):
                os.remove(p)
            raise
        return p, True
    finally:
        if dibuka is not None:
            dibuka.close()


def ocr_lines(src):
    """Daftar teks per baris dan skor kepercayaan. Panjang keduanya selalu sama."""
    path, tmp = _to_path(src)
    texts, scores = [], []
    try:
        with _OCR_LOCK:
            hasil = list(get_ocr().predict(path))
        for r in hasil:
            t = [str(x) for x in _daftar(r.get("rec_texts"))]
            s = [float(x) for x in _daftar(r.get("rec_scores"))]
            if len(t) != len(s):   # jangan buang teks diam-diam; nyatakan sebagai galat keluaran
                raise GalatKeluaranOCR(
                    f"jumlah teks ({len(t)}) tidak sama dengan jumlah skor ({len(s)})", texts + t)
            texts += t
            scores += s
    finally:
        if tmp and os.path.exists(path):
            os.remove(path)
    if not all(math.isfinite(x) and 0.0 <= x <= 1.0 for x in scores):
        raise GalatKeluaranOCR("skor OCR tidak valid (NaN/Inf atau di luar rentang 0-1)", texts)
    return texts, scores


def join_lines(lines, sambung_tanda_hubung=False):
    """Gabungkan baris dengan spasi."""
    text = " ".join(l.strip() for l in lines if l and l.strip())
    if sambung_tanda_hubung:
        text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    return text


def fitur_kualitas(text, scores, ambang_baris_rendah=0.60):
    toks = text.split()
    campur = [t for t in toks if re.search(r"[A-Za-z]", t) and re.search(r"\d", t)]
    return dict(
        n_kata=len(toks),
        n_baris=len(scores),
        conf_rata2=float(np.mean(scores)) if scores else None,
        conf_min=float(np.min(scores)) if scores else None,
        share_baris_conf_rendah=float(np.mean([s < ambang_baris_rendah for s in scores])) if scores else 1.0,
        share_token_huruf_angka=(len(campur) / len(toks)) if toks else 0.0,
        n_pemenggalan_hubung=len(re.findall(r"\w- \w", text)),
    )


# Ambang awal selaras dengan batas data latih (min_kata=10)
ATURAN_AWAL = dict(min_kata=10, min_conf_rata2=0.60, maks_share_baris_rendah=None, maks_share_token_huruf_angka=None)


def putuskan(f, aturan=None):
    """Gerbang kualitas input: tolak jika teks tidak memenuhi syarat kelayakan."""
    a = dict(ATURAN_AWAL, **(aturan or {}))
    alasan = []
    if f["n_kata"] == 0:
        alasan.append("tidak ada teks terbaca")
    elif f["n_kata"] < a["min_kata"]:
        alasan.append(f"teks terlalu pendek ({f['n_kata']} kata < {a['min_kata']})")
    if f["n_kata"] > 0 and a["min_conf_rata2"] is not None:
        if f["conf_rata2"] is None:
            alasan.append("kepercayaan OCR tidak tersedia")
        elif not (f["conf_rata2"] >= a["min_conf_rata2"]):   # NaN juga ditolak
            alasan.append(f"kepercayaan OCR rendah ({f['conf_rata2']:.2f} < {a['min_conf_rata2']})")
    if a["maks_share_baris_rendah"] is not None and f["share_baris_conf_rendah"] > a["maks_share_baris_rendah"]:
        alasan.append("terlalu banyak baris berkepercayaan rendah")
    if a["maks_share_token_huruf_angka"] is not None and f["share_token_huruf_angka"] > a["maks_share_token_huruf_angka"]:
        alasan.append("terlalu banyak token campuran huruf-angka")
    return (len(alasan) == 0), alasan


def extract_text_from_image(src, sambung_tanda_hubung=False, aturan=None):
    """Antarmuka resmi aplikasi: dict(success, message, text, ...)."""
    try:
        lines, scores = ocr_lines(src)
        text = join_lines(lines, sambung_tanda_hubung)
        f = fitur_kualitas(text, scores)
        ok, alasan = putuskan(f, aturan)
        return dict(
            success=True,
            message="OK" if ok else "; ".join(alasan),
            text=text,
            lines=lines,
            scores=scores,
            fitur=f,
            dapat_dinilai=ok,
            alasan=alasan,
            teks_mentah=text
        )
    except GambarDitolak as e:
        return dict(success=False, message=str(e), text="", lines=[], scores=[], fitur=None,
                    dapat_dinilai=False, alasan=["gambar ditolak"], teks_mentah="")
    except GalatKeluaranOCR as e:
        return dict(success=False, message=f"Keluaran OCR tidak konsisten: {e}", text="", lines=[],
                    scores=[], fitur=None, dapat_dinilai=False,
                    alasan=["keluaran OCR tidak konsisten"], teks_mentah=join_lines(e.teks_mentah))
    except Exception as e:
        return dict(
            success=False,
            message=f"Terjadi kesalahan saat mengekstrak gambar: {e}",
            text="",
            lines=[],
            scores=[],
            fitur=None,
            dapat_dinilai=False,
            alasan=["OCR gagal"],
            teks_mentah=""
        )