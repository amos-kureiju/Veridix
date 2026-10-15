"""evaluasi_aturan_keputusan.py — Mengukur trade-off cakupan vs akurasi antara 3

aturan keputusan pada n=472 (val + dev_test) menggunakan berkas resmi
prediksi_val_dev.csv.
"""

import numpy as np
import pandas as pd

df = pd.read_csv("prediksi_val_dev.csv")
y_true = df["label"].to_numpy()

# Ambil probabilitas dan prediksi kelas dari konfigurasi terpilih (CE)
p42 = df["prob_ce_42"].to_numpy()
p123 = df["prob_ce_123"].to_numpy()
p999 = df["prob_ce_999"].to_numpy()

v42 = df["pred_ce_42"].to_numpy()
v123 = df["pred_ce_123"].to_numpy()
v999 = df["pred_ce_999"].to_numpy()

n_total = len(y_true)

# 1. Aturan Rerata Probabilitas
p_mean = (p42 + p123 + p999) / 3.0
pred_mean = (p_mean >= 0.5).astype(int)
acc_mean = (pred_mean == y_true).mean() * 100

# 2. Aturan Mayoritas (Majority Vote: >= 2 seed sepakat)
votes_sum = v42 + v123 + v999
pred_majority = (votes_sum >= 2).astype(int)
acc_majority = (pred_majority == y_true).mean() * 100

# 3. Aturan Suara Bulat (Unanimous Vote: 3 sepakat; selain itu Abstain/Ambigu)
is_unanimous = (votes_sum == 3) | (votes_sum == 0)
pred_unanimous = np.where(votes_sum == 3, 1, np.where(votes_sum == 0, 0, -1))

n_decided = int(is_unanimous.sum())
n_abstain = n_total - n_decided
coverage_pct = (n_decided / n_total) * 100

# Akurasi hanya pada sampel yang diputuskan
acc_on_decided = (
    ((pred_unanimous[is_unanimous] == y_true[is_unanimous]).mean() * 100)
    if n_decided > 0
    else 0.0
)

# Kesalahan yang terjadi secara bulat (Unanimous Errors: 3 seed kompak salah)
unanimous_errors = int(
    (is_unanimous & (pred_unanimous != y_true) & (pred_unanimous != -1)).sum()
)

print("=" * 80)
print(f"ANALISIS ATURAN KEPUTUSAN KONSENSUS (n={n_total} sampel val + dev_test)")
print("=" * 80)
print(f"{'Aturan Keputusan':<28} {'Cakupan (%)':<15} {'Akurasi Terputus (%)':<24} {'Salah Kompak (Unanimous Error)':<25}")
print("-" * 80)
print(f"{'1. Rerata Probabilitas':<28} {'100.0%':<15} {f'{acc_mean:.2f}%':<24} {'-':<25}")
print(f"{'2. Suara Mayoritas (2/3)':<28} {'100.0%':<15} {f'{acc_majority:.2f}%':<24} {'-':<25}")
print(f"{'3. Suara Bulat (Unanimous)':<28} {f'{coverage_pct:.1f}% ({n_decided}/{n_total})':<15} {f'{acc_on_decided:.2f}%':<24} {f'{unanimous_errors} sampel':<25}")
print("=" * 80)
print(f"Catatan: Aturan Suara Bulat mengorbankan {n_abstain} sampel ({100-coverage_pct:.1f}%) menjadi status 'Ambigu'.")