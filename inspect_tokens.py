"""
inspect_tokens.py
Inspeksi manual token mencurigakan (kategori, berjudul, judul, tangkapan layar, artikel)
pada naskah hoaks train.csv.
"""

import os
import re
import pandas as pd

p = "data/processed_v2/train.csv" if os.path.exists("data/processed_v2/train.csv") else "../data/processed_v2/train.csv"
assert os.path.exists(p), f"Berkas {p} tidak ditemukan!"

df = pd.read_csv(p)
hoax = df[df["label"] == 1]

keywords = ["kategori", "berjudul", "judul", "tangkapan layar", "artikel"]

print("=" * 85)
print("INSPEKSI MANUAL TOKEN MENCURIGAKAN PADA DATA HOAKS (TRAIN.CSV)")
print(f"Total Sampel Hoaks yang Diperiksa: {len(hoax):,} baris")
print("=" * 85)

for kw in keywords:
    rx = re.compile(r"\b" + re.escape(kw) + r"\b", re.I)
    sub = hoax[hoax["text"].astype(str).str.contains(rx, na=False)]
    total_muncul = len(sub)
    pct = (total_muncul / len(hoax)) * 100
    
    print(f"\n>>> KATA KUNCI: '{kw.upper()}' (Muncul di {total_muncul} hoaks / {pct:.1f}%):")
    if total_muncul == 0:
        print("    [Tidak ditemukan sampel]")
        continue
        
    for i, (_, row) in enumerate(sub.head(3).iterrows()):
        teks = str(row["text"]).strip()
        print(f"  [{i+1}] ({row.get('source', 'sumber?')}) : {teks[:180]}...")

print("\n" + "=" * 85)
print("INSPEKSI SELESAI")
print("=" * 85)