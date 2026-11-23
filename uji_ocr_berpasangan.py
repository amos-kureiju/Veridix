"""uji_ocr_berpasangan.py — Evaluasi Berpasangan Akurasi Transkripsi (CER/WER)

dan Konsistensi Klasifikasi Model (Teks Asli vs Teks OCR).
"""
import argparse
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.inference import SEEDS, get_predictor, validate_claim_result
from src.utils.ocr_pipeline import (
    KATEGORI_INPUT,
    KATEGORI_KUALITAS,
    KATEGORI_MESIN,
    KATEGORI_OK,
    VERSI_PIPELINE,
    hash_kebijakan,
    kebijakan,
    proses_gambar,
)
from uji_ujung_ke_ujung import write_report

STATUS_DINILAI = ("dinilai", "ambigu")
KATEGORI_TERUKUR = (KATEGORI_OK, KATEGORI_KUALITAS)

# METRIK TRANSKRIPSI: JARAK LEVENSHTEIN, CER, DAN WER

def jarak_levenshtein(seq1: List[Any], seq2: List[Any]) -> int:
    """Menghitung jarak Levenshtein antara dua urutan (karakter atau kata)."""
    n, m = len(seq1), len(seq2)
    if n == 0:
        return m
    if m == 0:
        return n

    prev = list(range(m + 1))
    curr = [0] * (m + 1)

    for i in range(1, n + 1):
        curr[0] = i
        for j in range(1, m + 1):
            biaya = 0 if seq1[i - 1] == seq2[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # Penghapusan
                curr[j - 1] + 1,   # Penyisipan
                prev[j - 1] + biaya  # Pergantian
            )
        prev, curr = curr, prev

    return prev[m]


def hitung_cer_wer(ref: str, hyp: str) -> Tuple[Optional[float], Optional[float], int, int]:
    """Menghitung CER dan WER secara eksak (mempertahankan spasi, kapitalisasi, dan tanda baca).

    Mengembalikan: (cer_persen, wer_persen, char_errors, word_errors)
    """
    if not ref or not ref.strip():
        return (None, None, len(hyp), len(hyp.split()))

    # 1. CER (Level Karakter)
    char_ref = list(ref)
    char_hyp = list(hyp)
    jarak_char = jarak_levenshtein(char_ref, char_hyp)
    cer = (jarak_char / len(char_ref)) * 100.0

    # 2. WER (Level Kata/Token)
    kata_ref = ref.split()
    kata_hyp = hyp.split()
    jarak_kata = jarak_levenshtein(kata_ref, kata_hyp)
    wer = (jarak_kata / len(kata_ref)) * 100.0

    return round(cer, 4), round(wer, 4), jarak_char, jarak_kata


# KASUS BASELINE DEFAULT

DATASET_PASANGAN_DEFAULT = [
    {
        "id": "U01",
        "kategori": "teks_pendek",
        "gambar": "data/sample_probe.png",
        "deskripsi": "Klaim sangat pendek (49 karakter), menguji gerbang penolakan mutu",
        "transkripsi_manual": "KEMENTERIAN KEUANGAN MEMASTIKAN BANSOS TAHUN 2026",
    },
    {
        "id": "U02",
        "kategori": "teks_panjang_jelas",
        "gambar": "data/sample_panjang.png",
        "deskripsi": "Teks resmi kebijakan pemerintah, cukup panjang dan tajam",
        "transkripsi_manual": (
            "[KUTIPAN RESMI PRESIDEN RI] Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial "
            "tahun anggaran baru harus tepat sasaran."
        ),
    },
]


def validasi_manifest(dataset):
    if not isinstance(dataset, list) or not dataset:
        raise ValueError("Manifest harus berupa daftar kasus yang tidak kosong.")
    ids = set()
    for nomor, kasus in enumerate(dataset, 1):
        if not isinstance(kasus, dict):
            raise ValueError(f"Kasus ke-{nomor} harus berupa objek.")
        for field in ("id", "gambar", "transkripsi_manual"):
            nilai = kasus.get(field)
            if not isinstance(nilai, str) or (field != "transkripsi_manual" and not nilai.strip()):
                raise ValueError(f"Kasus ke-{nomor} memiliki field {field} tidak sah.")
        for field in ("kategori", "deskripsi"):
            if field in kasus and not isinstance(kasus[field], str):
                raise ValueError(f"Kasus ke-{nomor} memiliki field {field} tidak sah.")
        identitas = kasus["id"].strip()
        if identitas in ids:
            raise ValueError(f"ID kasus ke-{nomor} sudah dipakai.")
        ids.add(identitas)


def evaluasi_teks(teks: str, evaluator: Any) -> Dict[str, Any]:
    if len(teks.strip()) < 30:
        return dict(status="tidak_dievaluasi_terlalu_pendek", label=None, votes_hoax=None, durasi_detik=None)
    if evaluator is None:
        return dict(status="gagal", label=None, votes_hoax=None, durasi_detik=None, alasan="Model tidak tersedia.")

    mulai = time.perf_counter()
    try:
        hasil = evaluator.nilai(teks, explain=False, debug=True)
        validate_claim_result(hasil)
    except Exception as exc:
        return dict(
            status="gagal", label=None, votes_hoax=None,
            durasi_detik=round(time.perf_counter() - mulai, 4),
            alasan=f"Inferensi gagal atau keluarannya tidak sah ({type(exc).__name__}).",
        )

    durasi = round(time.perf_counter() - mulai, 4)
    if hasil["status"] not in STATUS_DINILAI:
        return dict(status=hasil["status"], label=None, votes_hoax=None, durasi_detik=durasi, alasan=hasil["reason"])

    debug = hasil.get("debug")
    skor = debug.get("prob_hoax_per_seed") if isinstance(debug, dict) else None
    skor_valid = (
        isinstance(skor, dict) and skor.keys() == set(SEEDS)
        and all(type(v) in (float, int) and 0 <= v <= 1 and math.isfinite(v) for v in skor.values())
    )
    return dict(
        status=hasil["status"],
        label=hasil["label"],
        votes_hoax=hasil["votes_hoax"],
        seed_decisions=hasil["seed_decisions"],
        agreement_ratio=hasil["agreement_ratio"],
        decision_rule=hasil["decision_rule"],
        teks_dinilai=hasil.get("teks_dinilai"),
        terpotong=hasil.get("terpotong"),
        debug_prob_per_seed=skor if skor_valid else None,
        durasi_detik=durasi,
    )


def evaluasi_satu_kasus(kasus: Dict[str, Any], evaluator: Any) -> Dict[str, Any]:
    jalur_gambar = Path(kasus["gambar"])
    rec = {
        "id": kasus.get("id", "UNKNOWN"),
        "kategori_kasus": kasus.get("kategori", "tidak_ditentukan"),
        "deskripsi": kasus.get("deskripsi", ""),
        "jalur_gambar": str(jalur_gambar),
        "transkripsi_manual": kasus["transkripsi_manual"],
        "status_berkas": "ada" if jalur_gambar.is_file() else "tidak_ditemukan",
    }

    if not jalur_gambar.is_file():
        rec["keputusan_akhir"] = "DILEWATI_BERKAS_TIDAK_ADA"
        return rec

    try:
        # 1. Jalankan Pipeline OCR
        t0_ocr = time.perf_counter()
        raw_ocr = proses_gambar(jalur_gambar)
        durasi_ocr = round(time.perf_counter() - t0_ocr, 4)

        kategori_ocr = raw_ocr["kategori"]
        if kategori_ocr not in (*KATEGORI_TERUKUR, KATEGORI_INPUT, KATEGORI_MESIN):
            raise ValueError("Kategori OCR tidak sah.")
        hyp = raw_ocr.get("teks_bersih")
        if kategori_ocr in KATEGORI_TERUKUR and not isinstance(hyp, str):
            raise ValueError("Teks keluaran OCR tidak sah.")
        if kategori_ocr == KATEGORI_OK and (raw_ocr.get("dapat_dinilai") is not True or not hyp.strip()):
            raise ValueError("Keluaran OCR kategori OK tidak konsisten.")

        rec["ocr"] = {
            "kategori": kategori_ocr,
            "kode": raw_ocr.get("kode"),
            "pesan": raw_ocr.get("pesan"),
            "daftar_alasan": raw_ocr.get("alasan", []),
            "teks_mentah": raw_ocr.get("teks_mentah", ""),
            "teks_bersih": raw_ocr.get("teks_bersih", ""),
            "dapat_dinilai": raw_ocr.get("dapat_dinilai"),
            "durasi_detik": durasi_ocr,
            "identitas_berkas": raw_ocr.get("berkas"),
            "fitur": raw_ocr.get("fitur"),
        }

        ref = rec["transkripsi_manual"]
        if kategori_ocr in KATEGORI_TERUKUR:
            cer, wer, char_err, word_err = hitung_cer_wer(ref, hyp)
            rec["metrik_transkripsi"] = {
                "tersedia": cer is not None,
                "cer_persen": cer,
                "wer_persen": wer,
                "char_errors": char_err,
                "word_errors": word_err,
                "ref_chars": len(ref) if ref.strip() else 0,
                "ref_words": len(ref.split()),
            }
        else:
            rec["metrik_transkripsi"] = {
                "tersedia": False,
                "cer_persen": None,
                "wer_persen": None,
                "alasan": f"Tidak ada transkripsi OCR yang sah ({kategori_ocr}).",
            }

        res_asli = evaluasi_teks(ref, evaluator)
        res_ocr = evaluasi_teks(hyp, evaluator) if kategori_ocr == KATEGORI_OK else None
        rec["evaluasi_teks_asli"] = res_asli
        rec["evaluasi_teks_ocr"] = res_ocr
        rec["konsistensi"] = dict(label_sama=None, votes_sama=None, seed_sama=None)
        if "gagal" in (res_asli["status"], (res_ocr or {}).get("status")):
            rec["keputusan_akhir"] = "GALAT_MODEL"
        elif kategori_ocr == KATEGORI_MESIN:
            rec["keputusan_akhir"] = "GALAT_MESIN_OCR"
        elif res_ocr is None:
            rec["keputusan_akhir"] = f"DITOLAK_{kategori_ocr}"
            rec["konsistensi"]["alasan"] = f"Teks ditolak ({raw_ocr.get('kode')})"
        elif res_asli["status"] not in STATUS_DINILAI or res_ocr["status"] not in STATUS_DINILAI:
            rec["keputusan_akhir"] = "TIDAK_DAPAT_DIBANDINGKAN"
        elif res_asli["decision_rule"] != res_ocr["decision_rule"]:
            rec["keputusan_akhir"] = "GALAT_MODEL"
            rec["konsistensi"]["alasan"] = "Aturan voting pasangan berbeda."
        else:
            rec["konsistensi"].update(
                label_sama=res_asli["label"] == res_ocr["label"],
                votes_sama=res_asli["votes_hoax"] == res_ocr["votes_hoax"],
                seed_sama=res_asli["seed_decisions"] == res_ocr["seed_decisions"],
            )
            rec["keputusan_akhir"] = "SELESAI_DIEVALUASI"

    except Exception as exc:
        rec["keputusan_akhir"] = "GALAT_EKSEKUSI"
        rec["galat"] = type(exc).__name__

    return rec


def ringkas_hasil(hasil_kasus):
    def kategori(row):
        return row.get("ocr", {}).get("kategori")

    def hitung_keputusan(keputusan):
        return sum(row["keputusan_akhir"] == keputusan for row in hasil_kasus)

    ringkasan = {
        "total_kasus": len(hasil_kasus),
        "diterima_ocr": sum(kategori(row) == KATEGORI_OK for row in hasil_kasus),
        "ditolak_kualitas": sum(kategori(row) == KATEGORI_KUALITAS for row in hasil_kasus),
        "ditolak_input": sum(kategori(row) == KATEGORI_INPUT for row in hasil_kasus),
        "galat_mesin": sum(kategori(row) == KATEGORI_MESIN for row in hasil_kasus),
        "berkas_tidak_ada": hitung_keputusan("DILEWATI_BERKAS_TIDAK_ADA"),
        "galat_model": hitung_keputusan("GALAT_MODEL"),
        "galat_eksekusi": hitung_keputusan("GALAT_EKSEKUSI"),
        "pasangan_dibandingkan": hitung_keputusan("SELESAI_DIEVALUASI"),
        "pasangan_label_berubah": sum(
            row.get("konsistensi", {}).get("label_sama") is False for row in hasil_kasus
        ),
        "pasangan_suara_berubah": sum(
            row.get("konsistensi", {}).get("votes_sama") is False for row in hasil_kasus
        ),
    }
    for metrik in ("cer", "wer"):
        hasil = [(kategori(row), row.get("metrik_transkripsi", {}).get(f"{metrik}_persen")) for row in hasil_kasus]
        semua = [nilai for _, nilai in hasil if nilai is not None]
        diterima = [nilai for status, nilai in hasil if status == KATEGORI_OK and nilai is not None]
        ringkasan[f"{metrik}_terukur"] = len(semua)
        ringkasan[f"{metrik}_terukur_diterima"] = len(diterima)
        ringkasan[f"rata2_{metrik}_semua_terukur"] = round(sum(semua) / len(semua), 4) if semua else None
        ringkasan[f"rata2_{metrik}_diterima"] = round(sum(diterima) / len(diterima), 4) if diterima else None
    return ringkasan


def ukur_latensi(dataset):
    sumber = next((Path(row["gambar"]) for row in dataset if Path(row["gambar"]).is_file()), None)
    if sumber is None:
        return None

    ukuran = {"berkas_uji": str(sumber)}
    for tahap in ("cold", "warm"):
        mulai = time.perf_counter()
        try:
            hasil = proses_gambar(sumber)
            kategori = hasil["kategori"]
        except Exception as exc:
            ukuran["galat"] = type(exc).__name__
            return ukuran
        ukuran[f"{tahap}_kategori"] = kategori
        ukuran[f"{tahap}_start_dtk"] = round(time.perf_counter() - mulai, 3) if kategori in KATEGORI_TERUKUR else None
    return ukuran


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluasi berpasangan OCR CER/WER dan konsistensi klasifikasi.")
    parser.add_argument("--dataset", type=Path, help="Jalur manifest JSON pasangan, opsional")
    parser.add_argument("--output", type=Path, help="Jalur JSON baru. Default memakai waktu eksekusi.")
    args = parser.parse_args(argv)
    now = datetime.now(timezone(timedelta(hours=7)))
    output = args.output or Path(f"reports/ocr/evaluasi_berpasangan_{now:%Y%m%d_%H%M%S_%f}.json")

    try:
        if args.dataset is not None:
            manifest_bytes = args.dataset.read_bytes()
            dataset = json.loads(manifest_bytes)
        else:
            dataset = DATASET_PASANGAN_DEFAULT
            manifest_bytes = json.dumps(dataset, sort_keys=True, ensure_ascii=False).encode("utf-8")
        validasi_manifest(dataset)
    except FileNotFoundError:
        parser.error(f"Berkas manifest/dataset tidak ditemukan: {args.dataset}")
    except (OSError, ValueError) as exc:
        parser.error(f"Manifest tidak sah: {exc}")

    if os.path.lexists(output):
        parser.error(f"Jalur laporan sudah ada: {output}. Gunakan jalur baru.")
    if output.resolve() in {Path(row["gambar"]).resolve() for row in dataset}:
        parser.error("Jalur laporan harus berbeda dari semua gambar masukan.")

    galat_pemuatan = None
    try:
        evaluator = get_predictor()
    except Exception as exc:
        evaluator = None
        galat_pemuatan = type(exc).__name__

    latensi = ukur_latensi(dataset)
    hasil_kasus = [evaluasi_satu_kasus(row, evaluator) for row in dataset]
    for row in hasil_kasus:
        metrik = row.get("metrik_transkripsi", {})
        print(f"{row['id']} | {row['keputusan_akhir']} | CER {metrik.get('cer_persen')} | WER {metrik.get('wer_persen')}")

    aturan = getattr(evaluator, "rule", None)
    audit = getattr(getattr(evaluator, "backend", None), "audit", None)
    ringkasan = ringkas_hasil(hasil_kasus)
    laporan = {
        "metadata": {
            "waktu_eksekusi": now.isoformat(timespec="seconds"),
            "manifest": str(args.dataset) if args.dataset is not None else "bawaan",
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "versi_pipeline": VERSI_PIPELINE,
            "hash_kebijakan": hash_kebijakan(),
            "kebijakan_ocr": kebijakan(),
            "aturan_konsensus": aturan if isinstance(aturan, str) else None,
            "audit_model": audit if isinstance(audit, dict) else None,
            "galat_pemuatan_model": galat_pemuatan,
            "latensi_benchmark": latensi,
        },
        "ringkasan": ringkasan,
        "hasil_evaluasi": hasil_kasus,
    }

    try:
        write_report(output, laporan, overwrite=False)
    except (OSError, TypeError, ValueError) as exc:
        print(f"Laporan gagal disimpan ({type(exc).__name__}): {output}", file=sys.stderr)
        return 1
    galat = ("galat_mesin", "galat_model", "galat_eksekusi", "berkas_tidak_ada")
    ada_galat = galat_pemuatan or (latensi or {}).get("galat") or any(ringkasan[key] for key in galat)
    print(f"Laporan {'dengan kegagalan ' if ada_galat else ''}tersimpan di {output}")
    return 1 if ada_galat else 0


if __name__ == "__main__":
    raise SystemExit(main())
