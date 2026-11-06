"""uji_ocr_berpasangan.py — Evaluasi Berpasangan Akurasi Transkripsi (CER/WER)

dan Konsistensi Klasifikasi Model (Teks Asli vs Teks OCR).
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.inference import get_predictor
from src.utils.ocr_pipeline import VERSI_PIPELINE, hash_kebijakan, proses_gambar

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


def hitung_cer_wer(ref: str, hyp: str) -> Tuple[float, float, int, int]:
    """Menghitung CER dan WER secara eksak (mempertahankan spasi, kapitalisasi, dan tanda baca).

    Mengembalikan: (cer_persen, wer_persen, char_errors, word_errors)
    """
    if not ref:
        return (0.0 if not hyp else 100.0, 0.0 if not hyp else 100.0, len(hyp), len(hyp.split()))

    # 1. CER (Level Karakter)
    char_ref = list(ref)
    char_hyp = list(hyp)
    jarak_char = jarak_levenshtein(char_ref, char_hyp)
    cer = (jarak_char / len(char_ref)) * 100.0

    # 2. WER (Level Kata/Token)
    kata_ref = ref.split()
    kata_hyp = hyp.split()
    if not kata_ref:
        wer = 0.0 if not kata_hyp else 100.0
        jarak_kata = len(kata_hyp)
    else:
        jarak_kata = jarak_levenshtein(kata_ref, kata_hyp)
        wer = (jarak_kata / len(kata_ref)) * 100.0

    return round(cer, 4), round(wer, 4), jarak_char, jarak_kata


# KORPUS UJI PASANGAN DEFAULT (5 KATEGORI KASUS LENGKAP)

DATASET_PASANGAN_DEFAULT = [
    {
        "id": "U01",
        "kategori": "teks_pendek",
        "gambar": "data/sample_probe.png",
        "deskripsi": "Klaim sangat pendek (< 50 karakter), menguji gerbang penolakan mutu",
        "transkripsi_manual": "Beredar kabar hoaks pemilu curang di Jakarta.",
    },
    {
        "id": "U02",
        "kategori": "teks_panjang_jelas",
        "gambar": "data/sample_panjang.png",
        "deskripsi": "Teks resmi kebijakan pemerintah, cukup panjang dan tajam",
        "transkripsi_manual": (
            "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial pangan beras "
            "tahun 2026 disalurkan tepat sasaran kepada masyarakat penerima manfaat secara transparan."
        ),
    },
]


# PROSEDUR EVALUASI BERPASANGAN

def evaluasi_satu_kasus(
    kasus: Dict[str, Any],
    evaluator: Any,
    catat_latensi_pemanasan: bool = False
) -> Dict[str, Any]:
    jalur_gambar = Path(kasus["gambar"])
    rec = {
        "id": kasus["id"],
        "kategori_kasus": kasus["kategori"],
        "deskripsi": kasus.get("deskripsi", ""),
        "jalur_gambar": str(jalur_gambar),
        "transkripsi_manual": kasus.get("transkripsi_manual", ""),
        "status_berkas": "ada" if jalur_gambar.is_file() else "tidak_ditemukan",
    }

    if not jalur_gambar.is_file():
        rec["keputusan_akhir"] = "DILEWATI_BERKAS_TIDAK_ADA"
        return rec

    # 1. Jalankan Pipeline OCR
    t0_ocr = time.perf_counter()
    raw_ocr = proses_gambar(jalur_gambar)
    durasi_ocr = round(time.perf_counter() - t0_ocr, 4)

    rec["ocr"] = {
        "kategori": raw_ocr.get("kategori"),
        "kode": raw_ocr.get("kode"),
        "pesan": raw_ocr.get("pesan"),
        "daftar_alasan": raw_ocr.get("alasan", []),
        "teks_mentah": raw_ocr.get("teks_mentah", ""),
        "teks_bersih": raw_ocr.get("teks_bersih", ""),
        "durasi_detik": durasi_ocr,
        "identitas_berkas": raw_ocr.get("berkas"),
        "fitur": raw_ocr.get("fitur"),
    }

    # 2. Hitung Metrik Akurasi Transkripsi (CER/WER)
    ref = rec["transkripsi_manual"]
    hyp = raw_ocr.get("teks_bersih", "")
    cer, wer, char_err, word_err = hitung_cer_wer(ref, hyp)
    rec["metrik_transkripsi"] = {
        "cer_persen": cer,
        "wer_persen": wer,
        "char_errors": char_err,
        "word_errors": word_err,
        "karakter_ref": len(ref),
        "kata_ref": len(ref.split()),
        "karakter_hyp": len(hyp),
        "kata_hyp": len(hyp.split()),
    }

    # 3. Prediksi Teks Asli (Ground Truth) melalui Model
    t0_model_gt = time.perf_counter()
    res_gt = evaluator.nilai(ref, explain=False, debug=True) if len(ref.strip()) >= 30 else None
    durasi_model_gt = round(time.perf_counter() - t0_model_gt, 4) if res_gt else 0.0

    rec["evaluasi_teks_asli"] = {
        "status": res_gt.get("status") if res_gt else "tidak_dievaluasi_terlalu_pendek",
        "label": res_gt.get("label") if res_gt else None,
        "votes_hoax": res_gt.get("votes_hoax") if res_gt else None,
        "seed_decisions": res_gt.get("seed_decisions") if res_gt else None,
        "agreement_ratio": res_gt.get("agreement_ratio") if res_gt else None,
        "durasi_detik": durasi_model_gt,
    }

    # 4. Prediksi Teks Hasil OCR (Hanya jika lolos gerbang mutu KATEGORI_OK)
    if raw_ocr.get("kategori") == "OK" and raw_ocr.get("dapat_dinilai") is True:
        t0_model_ocr = time.perf_counter()
        res_ocr = evaluator.nilai(hyp, explain=False, debug=True)
        durasi_model_ocr = round(time.perf_counter() - t0_model_ocr, 4)

        rec["evaluasi_teks_ocr"] = {
            "status": res_ocr.get("status"),
            "label": res_ocr.get("label"),
            "votes_hoax": res_ocr.get("votes_hoax"),
            "seed_decisions": res_ocr.get("seed_decisions"),
            "agreement_ratio": res_ocr.get("agreement_ratio"),
            "durasi_detik": durasi_model_ocr,
        }

        # 5. Uji Konsistensi Keputusan Model
        label_gt = res_gt.get("label") if res_gt else None
        label_ocr = res_ocr.get("label")
        rec["konsistensi"] = {
            "label_sama": (label_gt == label_ocr) if label_gt else None,
            "status_sama": (res_gt.get("status") == res_ocr.get("status")) if res_gt else None,
            "selisih_votes": None,
        }
        rec["keputusan_akhir"] = "SELESAI_DIEVALUASI"
    else:
        rec["evaluasi_teks_ocr"] = None
        rec["konsistensi"] = {
            "label_sama": None,
            "status_sama": None,
            "alasan": f"Teks OCR ditolak gerbang mutu ({raw_ocr.get('kode')})"
        }
        rec["keputusan_akhir"] = f"DITOLAK_{raw_ocr.get('kategori')}"

    return rec


# MAIN RUNNER DENGAN PENGUKURAN COLD VS WARM START

def main():
    parser = argparse.ArgumentParser(description="Evaluasi berpasangan OCR CER/WER dan konsistensi klasifikasi.")
    parser.add_argument("--dataset", type=Path, help="Jalur berkas JSON dataset pasangan (opsional)")
    parser.add_argument("--output", type=Path, default=Path("reports/ocr/evaluasi_berpasangan.json"), help="Jalur simpan JSON")
    args = parser.parse_args()

    print("=" * 105)
    print("BENCHMARK EVALUASI BERPASANGAN: TRANSKRIPSI (CER/WER) & KONSISTENSI VONIS INDOBERT")
    print("=" * 105)

    # Muat dataset
    if args.dataset and args.dataset.is_file():
        with open(args.dataset, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    else:
        dataset = DATASET_PASANGAN_DEFAULT

    # Inisialisasi model
    evaluator = get_predictor()

    # 1. Pengukuran Cold Start vs Warm Start pada sampel pertama yang valid
    sampel_latensi = next((k for k in dataset if Path(k["gambar"]).is_file()), None)
    latensi_benchmark = {}
    if sampel_latensi:
        p = Path(sampel_latensi["gambar"])
        print(f"\n[Pengukuran Latensi] Menguji Cold Start vs Warm Start pada '{p.name}'...")
        # Iterasi 1 (Cold / Initial)
        t_c = time.perf_counter()
        _ = proses_gambar(p)
        durasi_cold = round(time.perf_counter() - t_c, 3)

        # Iterasi 2 (Warm / Ready)
        t_w = time.perf_counter()
        _ = proses_gambar(p)
        durasi_warm = round(time.perf_counter() - t_w, 3)

        latensi_benchmark = {
            "berkas_uji": str(p),
            "cold_start_dtk": durasi_cold,
            "warm_start_dtk": durasi_warm,
            "efisiensi_akselerasi": f"{round(durasi_cold / max(durasi_warm, 0.001), 1)}x lebih cepat pada warm state"
        }
        print(f"  • Cold Start : {durasi_cold} dtk (termasuk inisialisasi mesin)")
        print(f"  • Warm Start : {durasi_warm} dtk (mesin telah siap di memori)")

    # 2. Jalankan Evaluasi Kasus per Kasus
    hasil_kasus = []
    print("\n" + "-" * 105)
    print(f"{'ID':<5} | {'Kategori Kasus':<20} | {'Status OCR':<12} | {'CER':<8} | {'WER':<8} | {'Vonis Asli':<16} | {'Vonis OCR':<16} | {'Konsisten'}")
    print("-" * 105)

    for kasus in dataset:
        res = evaluasi_satu_kasus(kasus, evaluator)
        hasil_kasus.append(res)

        st_ocr = res.get("ocr", {}).get("kategori", "-")
        cer_str = f"{res.get('metrik_transkripsi', {}).get('cer_persen', 0.0):.1f}%"
        wer_str = f"{res.get('metrik_transkripsi', {}).get('wer_persen', 0.0):.1f}%"
        lbl_gt = str(res.get("evaluasi_teks_asli", {}).get("label") or "-")
        lbl_ocr = str(res.get("evaluasi_teks_ocr", {}).get("label") if res.get("evaluasi_teks_ocr") else "DITOLAK")
        kons = str(res.get("konsistensi", {}).get("label_sama") if res.get("evaluasi_teks_ocr") else "-")

        print(f"{kasus['id']:<5} | {kasus['kategori']:<20} | {st_ocr:<12} | {cer_str:<8} | {wer_str:<8} | {lbl_gt:<16} | {lbl_ocr:<16} | {kons}")

    # 3. Rekam Laporan Komprehensif Bab 4
    now = datetime.now(timezone(timedelta(hours=7)))
    laporan_final = {
        "metadata": {
            "waktu_eksekusi": now.isoformat(timespec="seconds"),
            "versi_pipeline": VERSI_PIPELINE,
            "hash_kebijakan": hash_kebijakan(),
            "aturan_konsensus": getattr(getattr(evaluator, "backend", None), "voting_rule", "unanimous_consensus"),
            "latensi_benchmark": latensi_benchmark,
        },
        "ringkasan": {
            "total_kasus": len(hasil_kasus),
            "diterima_ocr": sum(1 for r in hasil_kasus if r.get("ocr", {}).get("kategori") == "OK"),
            "ditolak_ocr": sum(1 for r in hasil_kasus if r.get("ocr", {}).get("kategori") != "OK"),
            "rata2_cer_diterima": round(
                float(sum(r["metrik_transkripsi"]["cer_persen"] for r in hasil_kasus if r.get("ocr", {}).get("kategori") == "OK") /
                max(sum(1 for r in hasil_kasus if r.get("ocr", {}).get("kategori") == "OK"), 1)), 2
            ),
            "rata2_wer_diterima": round(
                float(sum(r["metrik_transkripsi"]["wer_persen"] for r in hasil_kasus if r.get("ocr", {}).get("kategori") == "OK") /
                max(sum(1 for r in hasil_kasus if r.get("ocr", {}).get("kategori") == "OK"), 1)), 2
            ),
        },
        "hasil_evaluasi": hasil_kasus,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(laporan_final, f, indent=2, ensure_ascii=False)

    print("-" * 105)
    print(f"\n[OK] Evaluasi berpasangan selesai. Laporan tersimpan di: {args.output}")


if __name__ == "__main__":
    main()
