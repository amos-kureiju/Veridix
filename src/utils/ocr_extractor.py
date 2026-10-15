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
import tempfile

os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
try:
    import torch  # noqa: F401  (muat DLL PyTorch lebih dulu di Windows)
except Exception:
    pass

import numpy as np
from PIL import Image, ImageOps

OCR_KWARGS = dict(lang="id")
_OCR = None


def get_ocr():
    global _OCR
    if _OCR is None:
        from paddleocr import PaddleOCR
        _OCR = PaddleOCR(**OCR_KWARGS)
    return _OCR


def reset_ocr():
    global _OCR
    _OCR = None


def _to_path(src, max_width=1400, padding_border=15):
    """
    Menstandarkan input ke berkas PNG sementara dengan:
      - Padding putih di sekeliling tepi (mencegah huruf pertama/terakhir terpotong).
      - Pengecilan proporsional jika lebar > max_width (efisiensi latensi CPU).
    """
    if isinstance(src, (str, os.PathLike)):
        img = Image.open(str(src))
    elif isinstance(src, (bytes, bytearray)):
        img = Image.open(io.BytesIO(bytes(src)))
    elif isinstance(src, Image.Image):
        img = src
    elif isinstance(src, np.ndarray):
        img = Image.fromarray(src)
    else:
        raise TypeError(f"Jenis masukan tidak didukung: {type(src)}")

    img = img.convert("RGB")

    # 1. Pengecilan resolusi proporsional jika terlalu besar
    w, h = img.size
    if w > max_width:
        scale = max_width / float(w)
        new_h = int(h * scale)
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    # 2. Tambahkan bantalan margin 15px agar teks mepet tepi tidak terpenggal OCR
    if padding_border > 0:
        img = ImageOps.expand(img, border=padding_border, fill="white")

    fd, p = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img.save(p, format="PNG")
    return p, True


def ocr_lines(src):
    """Daftar teks per baris dan skor kepercayaannya dari PaddleOCR 3.7.0."""
    path, tmp = _to_path(src)
    try:
        res = get_ocr().predict(path)
    finally:
        if tmp and os.path.exists(path):
            os.remove(path)

    texts, scores = [], []
    for r in res:
        texts += [str(t) for t in r.get("rec_texts", [])]
        scores += [float(s) for s in r.get("rec_scores", [])]
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
        conf_rata2=float(np.mean(scores)) if scores else 0.0,
        conf_min=float(np.min(scores)) if scores else 0.0,
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
    if f["n_kata"] > 0 and a["min_conf_rata2"] is not None and f["conf_rata2"] < a["min_conf_rata2"]:
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
            alasan=alasan
        )
    except Exception as e:
        return dict(
            success=False,
            message=f"Terjadi kesalahan saat mengekstrak gambar: {e}",
            text="",
            lines=[],
            scores=[],
            fitur=None,
            dapat_dinilai=False,
            alasan=["OCR gagal"]
        )