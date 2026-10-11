import os, sys
import pandas as pd

sys.path.insert(0, os.getcwd())
import text_pipeline as tp

O = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"
assert os.path.exists(O), f"Folder {O} tidak ditemukan!"

d = pd.read_csv(f"{O}/dataset_v2_full.csv")
t = d.title.astype(str)

print("=" * 80)
print("HASIL VERIFIKASI NORMALISASI JUDUL PADA DATASET PROCESSED:")
print("=" * 80)
print("Judul belum ternormalisasi :", int((t.map(tp.norm_title) != t).sum()), "dari", len(d))

tbl = d.assign(
    kutip=t.str.match(r'^\s*[“"]'),
    dsc=t.map(lambda s: bool(tp.DESC.match(s)))
).groupby("label")[["kutip", "dsc"]].sum()

print("\nDistribusi residu tanda kutip dan deskriptor:")
print(tbl.to_string())
print("=" * 80)