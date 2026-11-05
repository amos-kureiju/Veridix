r"""Uji fungsi gambar -> OCR aktif -> gerbang -> pembersihan -> model (3 seed).

    .\.venv\Scripts\python.exe uji_ujung_ke_ujung.py gambar1.png gambar2.png
    .\.venv\Scripts\python.exe uji_ujung_ke_ujung.py --lime gambar.png
    .\.venv\Scripts\python.exe uji_ujung_ke_ujung.py --output hasil.json gambar.png

Memakai fungsi OCR/pembersihan/model aplikasi, belum seluruh gerbang HTTP,
editor frontend, atau penyimpanan riwayat. Bukan evaluasi akurasi; tidak membaca
lockbox. JSON memuat setiap masukan, termasuk penolakan dan galat. Kode keluar
1 untuk galat berkas/mesin/laporan; penolakan biasa bukan galat eksekusi.
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.ocr_pipeline import (
    KATEGORI_INPUT,
    KATEGORI_KUALITAS,
    KATEGORI_MESIN,
    KATEGORI_OK,
    MIN_KARAKTER,
    proses_gambar,
)

TAHAP_GALAT = {"berkas_tidak_ada", "berkas_galat", "ocr_galat", "model_galat"}
_pred = None


def angka(value, fmt="{:.3f}"):
    """Nilai tidak tersedia/NaN/Inf ditampilkan sebagai tanda '-', bukan nol."""
    return fmt.format(value) if isinstance(value, (int, float)) and math.isfinite(value) else "-"


def model():
    """Muat sekali, hanya sesudah gambar lolos OCR dan batas karakter."""
    global _pred
    if _pred is None:
        from src.ml.inference import get_predictor
        _pred = get_predictor()
    return _pred


def _galat(rec, tahap, exc):
    rec.update(tahap_akhir=tahap, keputusan="GAGAL", galat=f"{type(exc).__name__}: {exc}")
    print("     ", rec["galat"])
    return rec


def process_image(path, *, lime=False, model_provider=None, ocr_fn=None):
    """Satu kasus selalu menjadi satu record; galat tidak menghentikan batch."""
    path_obj = Path(path)
    rec = {"gambar": str(path_obj), "tahap_akhir": None, "keputusan": None}
    print("=" * 80)
    print("Gambar:", path_obj)

    # 1. Validasi keberadaan berkas sebelum memanggil pipeline
    if not path_obj.is_file():
        rec.update(tahap_akhir="berkas_tidak_ada", keputusan="DILEWATI", galat="Berkas tidak ditemukan.")
        print("     ", rec["galat"])
        return rec

    # 2. Jalankan OCR Pipeline (serahkan jalur berkas agar dibaca dengan batas MAX_BYTES + 1)
    t0 = time.perf_counter()
    try:
        raw = (ocr_fn or proses_gambar)(path_obj)
        if not isinstance(raw, dict):
            raise TypeError("Hasil OCR pipeline harus berupa dict.")
    except Exception as exc:
        return _galat(rec, "ocr_galat", exc)
    finally:
        rec["waktu_ocr_dtk"] = round(time.perf_counter() - t0, 3)

    # 3. Simpan seluruh rekaman awal sebelum filter penolakan
    rec["kategori"] = raw.get("kategori")
    rec["kode"] = raw.get("kode")
    rec["alasan"] = raw.get("pesan")
    rec["fitur_ocr"] = raw.get("fitur") if isinstance(raw.get("fitur"), dict) else {}
    rec["teks_ocr_mentah"] = raw.get("teks_mentah", "")
    rec["teks_bersih"] = raw.get("teks_bersih", "")

    features = rec["fitur_ocr"]
    print(
        f"OCR: {rec['waktu_ocr_dtk']:.1f} dtk | kata={features.get('n_kata', '-')} "
        f"| conf rata2={angka(features.get('conf_rata2'))} | kategori={rec['kategori']} ({rec['kode']})"
    )
    if rec["teks_bersih"]:
        print("Teks Bersih:", rec["teks_bersih"][:300])

    # 4. Tangani penolakan pipeline (Model HANYA dipanggil jika KATEGORI_OK)
    if rec["kategori"] == KATEGORI_INPUT:
        rec.update(tahap_akhir="input_ditolak", keputusan="DITOLAK")
        print("KEPUTUSAN:", rec["keputusan"], "->", rec["alasan"])
        return rec

    if rec["kategori"] == KATEGORI_KUALITAS:
        rec.update(tahap_akhir="gerbang_kualitas", keputusan="TIDAK_LAYAK")
        print("KEPUTUSAN:", rec["keputusan"], "->", rec["alasan"])
        return rec

    if rec["kategori"] == KATEGORI_MESIN:
        rec.update(tahap_akhir="ocr_galat", keputusan="GAGAL")
        print("KEPUTUSAN:", rec["keputusan"], "->", rec["alasan"])
        return rec

    if rec["kategori"] != KATEGORI_OK:
        rec.update(tahap_akhir="ocr_galat", keputusan="GAGAL", alasan="Kategori pipeline tidak dikenal.")
        print("KEPUTUSAN:", rec["keputusan"], "->", rec["alasan"])
        return rec

    # 5. Jalankan Evaluator Model (hanya jika kategori OK)
    cleaned = rec["teks_bersih"]
    t_load = time.perf_counter()
    try:
        evaluator = (model_provider or model)()
    except Exception as exc:
        return _galat(rec, "model_galat", exc)
    finally:
        rec["waktu_akses_model_dtk"] = round(time.perf_counter() - t_load, 3)

    t_model = time.perf_counter()
    try:
        result = evaluator.nilai(cleaned, explain=lime, debug=True)
        if not isinstance(result, dict):
            raise TypeError("Hasil model harus berupa dict.")
    except Exception as exc:
        return _galat(rec, "model_galat", exc)
    finally:
        rec["waktu_model_dtk"] = round(time.perf_counter() - t_model, 3)

    rec.update(
        tahap_akhir="model",
        keputusan=result.get("label"),
        status=result.get("status"),
        votes_hoax=result.get("votes_hoax"),
        terpotong=result.get("terpotong"),
    )
    print(
        f"KEPUTUSAN: {rec['status']} | {rec['keputusan']} | suara hoaks={rec['votes_hoax']} "
        f"| inferensi {rec['waktu_model_dtk']:.1f} dtk"
    )

    if not result.get("success"):
        rec["alasan"] = result.get("reason")
        print("     alasan:", rec["alasan"])
    else:
        rec["teks_dinilai"] = result.get("teks_dinilai")
        debug = result.get("debug") or {}
        rec["debug_prob_per_seed"] = (
            debug.get("prob_hoax_per_seed") if isinstance(debug, dict) else None
        )
        print("     teks dinilai:", (rec["teks_dinilai"] or "")[:200])
        if lime:
            rec["explanation"] = result.get("explanation")

    return rec


def write_report(output, report):
    """Tulis atomik agar kegagalan simpan tidak merusak laporan sebelumnya."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as destination:
            json.dump(report, destination, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("images", nargs="+", help="Jalur gambar yang diuji")
    parser.add_argument("--lime", action="store_true", help="Tambahkan penjelasan LIME")
    parser.add_argument("--output", type=Path, help="Jalur JSON; default memakai waktu hingga mikrodetik")
    args = parser.parse_args(argv)
    now = datetime.now(timezone(timedelta(hours=7)))
    output = args.output or Path(f"hasil_ujung_ke_ujung_{now:%Y%m%d_%H%M%S_%f}.json")
    if output.resolve() in {Path(path).resolve() for path in args.images}:
        parser.error("Jalur laporan harus berbeda dari seluruh berkas gambar masukan.")

    results = [process_image(path, lime=args.lime) for path in args.images]
    summary = dict(Counter(row["tahap_akhir"] for row in results))
    n_errors = sum(row["tahap_akhir"] in TAHAP_GALAT for row in results)
    report = {
        "waktu": now.isoformat(timespec="seconds"), "lime": args.lime,
        "mode": "fungsi_ocr_dan_model_tanpa_http_atau_database",
        "min_karakter_ocr": MIN_KARAKTER, "total": len(results),
        "jumlah_galat": n_errors, "ringkasan": summary, "gambar": results,
    }
    print("=" * 80)
    print("Ringkasan tahap akhir:", summary, f"| total gambar: {len(results)} | galat: {n_errors}")
    try:
        write_report(output, report)
    except (OSError, TypeError, ValueError) as exc:
        print(f"Laporan gagal disimpan: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("Tersimpan:", output)
    return 1 if n_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
