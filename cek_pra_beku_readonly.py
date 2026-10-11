import os, re
import pandas as pd

O = "data/processed_v2_trial"
assert os.path.exists(O), f"Folder {O} tidak ditemukan!"

d = pd.read_csv(f"{O}/dataset_v2_full.csv")
d["text"] = d["text"].astype(str)
d["title"] = d["title"].astype(str)

print("=" * 80)
print("1. IDENTIFIKASI RESIDU PENANDA DEBUNKER (BACA-SAJA)")
print("=" * 80)
pat = r"(?i)penjelasan\s*(?:&|dan|/)\s*fakta|fakta\s*:|faktanya\s*:"
hoaks_bocor = d[(d.label == 1) & d.text.str.contains(pat, na=False)]
print(f"Total baris hoaks cocok pola_bocor: {len(hoaks_bocor)}")
for i, t in enumerate(hoaks_bocor.text, 1):
    print(f"\n[Residu {i}]:")
    print(repr(t[:300]))

print("\nPengecekan Pola PENJELASAN(\\d+):")
print(d[d.text.str.contains(r"(?i)penjelasan\s*\(\d+\)", na=False)].groupby("label").size().to_string())

print("\n" + "=" * 80)
print("2. UJI INDEPENDEN: JUDUL SAMA LINTAS SPLIT & CROSSTAB SUMBER")
print("=" * 80)
nk = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
d["k"] = d.title.map(nk)
judul_bocor = int((d.groupby("k").split.nunique() > 1).sum())
print(f"Judul sama lintas split: {judul_bocor}")
if judul_bocor > 0:
    print(">> PERINGATAN KERAS: Terdeteksi kebocoran judul lintas split!")
else:
    print(">> STATUS: VALID. Nol kebocoran judul lintas split (C5 Terverifikasi Independen).")

print("\nTabel Silang Split x Sumber per Label:")
print(pd.crosstab([d.split, d.source], d.label).to_string())

print("\n" + "=" * 80)
print("3. DISTRIBUSI 10 KATA PEMBUKA TERATAS PER LABEL")
print("=" * 80)
for l in (0, 1):
    nama_label = "Fakta (0)" if l == 0 else "Hoaks (1)"
    top_words = d[d.label == l].text.str.split().str[0].str.lower().value_counts().head(10).to_dict()
    print(f"{nama_label}: {top_words}")
print("=" * 80)