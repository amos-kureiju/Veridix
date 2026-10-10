"""
cek_deskriptor_kutip.py — Cek Deskriptor Judul & Tanda Kutip (Read-Only)
Mengukur sebaran prefiks deskriptif Mafindo dan tanda kutip pembungkus
untuk menentukan nilai UNWRAP sebelum build trial terakhir.
"""
import os, re
import pandas as pd

O = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"
assert os.path.exists(O), f"Folder {O} tidak ditemukan! Pastikan dataset_v2_full.csv ada."

DESC = re.compile(
    r'^\W*(?:(?:video|foto|gambar|screenshot|tangkapan\s+layar|tangkap\s+layar|sampul|pesan\s+berantai'
    r'|artikel(?:\s+(?!berjudul)\S+){0,3}?\s+berjudul|berita(?:\s+\S+){0,2}?\s+tentang)\b'
    r'|artikel(?:\s+\S+){0,3}?\s+(?=[“"]))\W*', re.I
)

p_file = os.path.join(O, "dataset_v2_full.csv")
d = pd.read_csv(p_file)
t = d.title.astype(str)

d["deskriptor"] = [bool(DESC.match(x)) for x in t]
d["kutip"] = t.str.match(r'^\s*[“"]')

print("=" * 80)
print("HASIL PENGUKURAN DESKRIPTOR & TANDA KUTIP PER SUMBER:")
print("=" * 80)
tbl = d.groupby(["label", "source"])[["deskriptor", "kutip"]].agg(["sum", "mean"]).round(3)
print(tbl.to_string())

print("\n" + "=" * 80)
print("RINGKASAN PER LABEL:")
print("=" * 80)
summary = d.groupby("label")[["deskriptor", "kutip"]].agg(["sum", "mean"]).round(3)
print(summary.to_string())

# Hitung selisih proporsi tanda kutip
kutip_fakta = d[d.label == 0]["kutip"].mean() * 100
kutip_hoaks = d[d.label == 1]["kutip"].mean() * 100
selisih_kutip = abs(kutip_hoaks - kutip_fakta)

print("\n" + "=" * 80)
print(f"Proporsi Kutip Fakta : {kutip_fakta:.1f}%")
print(f"Proporsi Kutip Hoaks : {kutip_hoaks:.1f}%")
print(f"Selisih Proporsi     : {selisih_kutip:.1f} poin persentase")
print("=" * 80)
if selisih_kutip > 10.0:
    print(f">> ATURAN TERPENUHI: Selisih ({selisih_kutip:.1f} poin) > 10 poin. Nilai UNWRAP = True wajib diaktifkan.")
else:
    print(f">> ATURAN TIDAK TERPENUHI: Selisih ({selisih_kutip:.1f} poin) <= 10 poin. Nilai UNWRAP = False dipertahankan.")
print("=" * 80)