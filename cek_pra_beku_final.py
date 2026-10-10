"""
cek_pra_beku_final.py — Cek Pra-Pembekuan (Read-Only)
Memeriksa:
  1. Akuntansi baris BENAR vs Ambigu.
  2. Distribusi sumber, panjang kata, isi kosong, dan tahun per label pasca-seimbang.
  3. Residu kata-vonis riil pada teks akhir.
  4. Residu nama media per label & sumber.
  5. Integritas eval set (tidak boleh bocor ke train) dan cek judul lintas split.
"""
import os, re
import pandas as pd

O = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"
assert os.path.exists(O), f"Folder {O} tidak ditemukan! Pastikan build trial sudah selesai."

d  = pd.read_csv(f"{O}/dataset_v2_full.csv")
eb = pd.read_csv(f"{O}/eval_benar.csv")
am = pd.read_csv(f"{O}/label1_ambigu.csv")
ek = pd.read_csv(f"{O}/eval_kompas_cekfakta.csv")

nk = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"^\s*(?:\[[^\]]{1,25}\]\s*)+", "", str(s).lower()))

print("=" * 80)
print("1. AKUNTANSI LABEL NOISE (BENAR vs AMBIGU):")
print("=" * 80)
irisan_eb_am = len(set(eb.title.map(nk)) & set(am.title.map(nk)))
print(f"Total eval_benar: {len(eb)} | Total label1_ambigu: {len(am)} | Irisan judul sama: {irisan_eb_am}")

print("\n" + "=" * 80)
print("2. SUMBER, PANJANG, ISI KOSONG, DAN TAHUN (DATASET v2 FULL TRIAL):")
print("=" * 80)
d["w"] = d.text.astype(str).str.split().str.len()
print("\n[A] Tabel Split x Sumber x Label:")
print(pd.crosstab([d.split, d.source], d.label).to_string())

print("\n[B] Karakteristik per Sumber (Ukuran, Median Kata, Rasio Body Kosong):")
print(d.groupby(["label", "source"]).agg(
    n=("w", "size"),
    median_kata=("w", "median"),
    body_kosong=("body", lambda s: round((s.fillna("") == "").mean(), 2))
).to_string())

print("\n[C] Distribusi Tahun per Label:")
print(pd.crosstab(d.date.astype(str).str[:4], d.label).to_string())

print("\n" + "=" * 80)
print("3. RESIDU KATA-VONIS RIIL PADA TEKS AKHIR (% TEKS):")
print("=" * 80)
VERD = r"(?<!\w)(?:hoaks|hoax|palsu|keliru|tidak benar|menyesatkan|disinformasi|misinformasi|klarifikasi|bohong|faktanya|periksa fakta|cek fakta|penjelasan|fakta sebenarnya|tidak terbukti|tidak ditemukan)(?!\w)"
print((d.assign(v=d.text.astype(str).str.contains(VERD, case=False)).groupby("label").v.mean() * 100).round(1).to_dict())

print("\n" + "=" * 80)
print("4. RESIDU NAMA MEDIA (CNN Indonesia & KOMPAS.com):")
print("=" * 80)
m = d[d.text.astype(str).str.contains(r"CNN Indonesia|KOMPAS\.com", case=False, na=False)]
print(m.groupby(["label", "source"]).size().to_string())

print("\n" + "=" * 80)
print("5. INTEGRITAS EVAL SET & KEBOCORAN JUDUL:")
print("=" * 80)
tr = set(d.title.map(nk))
print("eval_benar di train :", len(set(eb.title.map(nk)) & tr))
print("eval_kompas di train:", len(set(ek.title.map(nk)) & tr))
print("Judul sama lintas split:", int((d.assign(k=d.title.map(nk)).groupby("k").split.nunique() > 1).sum()))