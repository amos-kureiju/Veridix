"""
analisis_aturan_ensemble.py — membandingkan aturan keputusan antar-seed dari prediksi YANG SUDAH ADA
(prediksi_val_dev.csv). Tidak memuat model, tidak menyentuh lockbox.

Aturan yang dibandingkan (semua dihitung dari tiga seed CE terpilih):
  per-seed     : tiap seed sendiri (acuan protokol)
  mayoritas    : hoaks bila >= 2 dari 3 seed
  rerata-prob  : hoaks bila rerata probabilitas >= 0,5
  bulat-suara  : memutuskan hanya bila 3/3 atau 0/3; selain itu "ambigu" (ditahan)
Untuk "bulat-suara" dilaporkan CAKUPAN (porsi yang diputuskan) dan akurasi pada yang diputuskan, serta berapa
persen kesalahan mayoritas yang tertahan di kelompok ambigu. Pilih aturan dari VAL, catat di protokol SEBELUM lockbox.
Jalankan:  python analisis_aturan_ensemble.py [prediksi_val_dev.csv]
"""
import sys
import numpy as np
import pandas as pd

PATH = sys.argv[1] if len(sys.argv) > 1 else "prediksi_val_dev.csv"
SEEDS, LOSS = [42, 123, 999], "ce"
df = pd.read_csv(PATH)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(c - h, 0), min(c + h, 1)


def fmt(k, n):
    if n == 0:
        return "   n=0"
    lo, hi = wilson(k, n)
    return f"{k/n*100:5.1f}% [{lo*100:4.1f}-{hi*100:4.1f}] (n={n})"


rows = []
for nama, d in (("val", df[df.split == "val"]), ("dev_test", df[df.split == "dev_test"]), ("val+dev (eksploratif)", df)):
    y = d.label.to_numpy()
    P = np.column_stack([d[f"pred_{LOSS}_{s}"] for s in SEEDS]).astype(int)
    PR = np.column_stack([d[f"prob_{LOSS}_{s}"] for s in SEEDS])
    votes = P.sum(axis=1)
    mayor = (votes >= 2).astype(int)
    meanp = (PR.mean(axis=1) >= 0.5).astype(int)
    putus = np.isin(votes, (0, 3))
    n = len(y)
    print("=" * 92); print(f"{nama} (n={n})"); print("=" * 92)
    for j, s in enumerate(SEEDS):
        print(f"  per-seed {s:<4}       akurasi {fmt(int((P[:, j] == y).sum()), n)}")
    print(f"  mayoritas (>=2/3)    akurasi {fmt(int((mayor == y).sum()), n)}")
    print(f"  rerata-prob >= 0,5   akurasi {fmt(int((meanp == y).sum()), n)}")
    kk = int((mayor[putus] == y[putus]).sum())
    print(f"  bulat-suara          cakupan {putus.mean()*100:5.1f}% ({int(putus.sum())}/{n}) | akurasi pada yang diputuskan {fmt(kk, int(putus.sum()))}")
    amb = ~putus
    salah_mayor = mayor != y
    tahan = int((salah_mayor & amb).sum()); total_salah = int(salah_mayor.sum())
    print(f"  ambigu (ditahan)     n={int(amb.sum())} | mayoritas benar di dalamnya: {int((mayor[amb] == y[amb]).sum())}/{int(amb.sum())} "
          f"| kesalahan mayoritas yang tertahan: {tahan}/{total_salah}"
          + (f" ({tahan/total_salah*100:.0f}%)" if total_salah else ""))
    rows.append(dict(split=nama, n=n, acc_mayoritas=(mayor == y).mean(), acc_rerata_prob=(meanp == y).mean(),
                     cakupan_bulat=putus.mean(), acc_bulat_diputuskan=(mayor[putus] == y[putus]).mean() if putus.any() else np.nan,
                     ambigu_n=int(amb.sum()), salah_mayoritas_tertahan=tahan, salah_mayoritas_total=total_salah))

pd.DataFrame(rows).to_csv("hasil_aturan_ensemble.csv", index=False)
print("\nTersimpan: hasil_aturan_ensemble.csv")
print("Cara membaca: bulat-suara berguna bila persen kesalahan yang tertahan jauh lebih besar daripada porsi ambigu "
      "(artinya penahanan memilih kasus yang memang sulit). Bila sebanding, ia hanya mengurangi cakupan.")
print("val dipakai memilih aturan; dev_test sudah dipakai mendiagnosis pipeline, jadi hanya pemeriksaan tambahan.")