"""audit_latensi_dan_ablasi.py — Menjawab 2 evaluasi pembimbing:

  1. Pengukuran latensi berulang setelah warm-up (5 run).
  2. Uji ablasi derau terisolasi ('residen' vs 'te pat') pada 3 seed.
"""

import os
import sys
import time
import numpy as np

sys.path.insert(0, os.getcwd())
import inferensi_lokal as il
from src.utils import ocr_extractor as op
import text_pipeline as tp

SEEDS = [42, 123, 999]
models = {s: il.load_ckpt(f"ckpt_ce_{s}.pt") for s in SEEDS}

print("=" * 80)
print("1. PENGUKURAN LATENSI OCR BERULANG (WARM-UP 5 KALI)")
print("=" * 80)
gambar_uji = "data/sample_panjang.png"

# Panggilan 1 (Cold-Start)
t0 = time.time()
r0 = op.extract_text_from_image(gambar_uji)
durasi_cold = time.time() - t0
print(f"Panggilan 1 (Cold-Start) : {durasi_cold:.2f} detik")

# Panggilan 2-5 (Warmed-Up)
durasi_warm = []
for i in range(2, 6):
  t_start = time.time()
  _ = op.extract_text_from_image(gambar_uji)
  d = time.time() - t_start
  durasi_warm.append(d)
  print(f"Panggilan {i} (Warm)       : {d:.2f} detik")

print(f"--> Median Latensi Warm-Up : {np.median(durasi_warm):.2f} detik")


print("\n" + "=" * 80)
print("2. UJI ABLASI DERAU TERISOLASI PADA 3 SEED")
print("=" * 80)

kalimat_dasar = (
    "menegaskan bahwa penyaluran bantuan sosial tahun anggaran baru harus"
    " sasaran."
)

variasi_uji = [
    {
        "kondisi": "A. Kedua Derau Ada (Hasil OCR)",
        "teks": (
            "residen Joko Widodo menegaskan bahwa penyaluran bantuan sosial"
            " tahun anggaran baru harus te pat sasaran."
        ),
    },
    {
        "kondisi": "B. Hanya 'residen' (Spasi 'tepat' diperbaiki)",
        "teks": (
            "residen Joko Widodo menegaskan bahwa penyaluran bantuan sosial"
            " tahun anggaran baru harus tepat sasaran."
        ),
    },
    {
        "kondisi": "C. Hanya 'te pat' (Huruf 'Presiden' diperbaiki)",
        "teks": (
            "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial"
            " tahun anggaran baru harus te pat sasaran."
        ),
    },
    {
        "kondisi": "D. Bersih Sempurna (Acuan Asli)",
        "teks": (
            "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial"
            " tahun anggaran baru harus tepat sasaran."
        ),
    },
]

for var in variasi_uji:
  teks_input = tp.cap_sentences(tp.ensure_end(tp.clean(var["teks"])), 60)
  print(f"\n[{var['kondisi']}]")
  print(f"Teks: {teks_input[:70]}...")

  p_seeds = []
  for s in SEEDS:
    _, pr = il.predict_texts(models[s], [teks_input])
    p_seeds.append(float(pr[0]))

  rerata_p = float(np.mean(p_seeds))
  vonis_rerata = "HOAKS" if rerata_p >= 0.5 else "FAKTA"
  sepakat = len(set([1 if p >= 0.5 else 0 for p in p_seeds])) == 1

  print(
      f"  P(hoaks) per Seed (42, 123, 999) : {[round(p, 3) for p in p_seeds]}"
  )
  print(
      f"  Rerata Probabilitas              : {rerata_p:.3f} -> Vonis:"
      f" {vonis_rerata}"
  )
  print(
      f"  Status Konsensus                 :"
      f" {'SEPAKAT' if sepakat else 'TIDAK SEPAKAT (PERLU VERIFIKASI)'}"
  )

print("=" * 80)