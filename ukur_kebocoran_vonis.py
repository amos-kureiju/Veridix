"""
ukur_kebocoran_vonis.py — Mengukur residu kata-vonis dan pola 'Penjelasan & Fakta'
(Hanya membaca, tidak mengubah data).
"""
import os, re
import pandas as pd

O = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"
assert os.path.exists(O), f"Folder {O} tidak ditemukan! Pastikan dataset_v2_full.csv ada."

d = pd.read_csv(f"{O}/dataset_v2_full.csv")

VERD = (
    r"(?<!\w)(?:hoaks|hoax|palsu|keliru|tidak benar|menyesatkan|disinformasi|"
    r"misinformasi|klarifikasi|bohong|faktanya|periksa fakta|cek fakta|"
    r"penjelasan|fakta sebenarnya|tidak terbukti|tidak ditemukan)(?!\w)"
)
rx = re.compile(VERD, re.I)

d["vonis"] = d.text.astype(str).str.contains(rx)

print("=" * 80)
print("1. RESIDU KATA VONIS PER LABEL:")
print("=" * 80)
print(d.groupby("label").vonis.agg(["sum", "mean"]).round(3).to_string())

print("\n" + "=" * 80)
print("2. RESIDU KATA VONIS PER LABEL & SUMBER:")
print("=" * 80)
print(d.groupby(["label", "source"]).vonis.agg(["sum", "mean"]).round(3).to_string())

h = d[(d.label == 1) & d.vonis]
print("\n" + "=" * 80)
print(f"3. 15 KATA VONIS TERBANYAK PADA HOAKS (TOTAL {len(h)} SAMPEL):")
print("=" * 80)
if len(h) > 0:
    print(h.text.astype(str).map(lambda t: rx.search(t).group(0).lower()).value_counts().head(15).to_dict())

    print("\n" + "=" * 80)
    print("4. 20 SAMPEL KONTEKS KATA VONIS PADA HOAKS:")
    print("=" * 80)
    for i, t in enumerate(h.text.astype(str).head(20)):
        m = rx.search(t)
        cuplikan = t[max(0, m.start() - 40):m.end() + 40]
        print(f"[{i+1:>2}] ...{cuplikan!r}...")

print("\n" + "=" * 80)
print("5. POLA KHUSUS: 'PENJELASAN &/DAN FAKTA' ATAU 'FAKTANYA :':")
print("=" * 80)
pola_bocor = r"(?i)penjelasan\s*(?:&|dan|/)\s*fakta|fakta\s*:|faktanya\s*:"
print(d.assign(p=d.text.astype(str).str.contains(pola_bocor)).groupby("label").p.sum().to_string())