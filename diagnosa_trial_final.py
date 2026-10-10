"""
diagnosa_trial_final.py
Diagnostik pasca-build trial (hanya membaca):
  1. Probe linier 8 kata vs penuh pada title, body, dan text.
  2. Koefisien 15 token paling condong ke fakta & hoaks.
  3. Pengecekan teks yang memuat 'CNN Indonesia' atau 'KOMPAS.com'.
"""
import os, numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

OUT_DIR = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"
p_full = os.path.join(OUT_DIR, "dataset_v2_full.csv")
assert os.path.exists(p_full), f"Berkas {p_full} belum ada! Jalankan 01b dulu."

d = pd.read_csv(p_full)
d = d[d.body.fillna("").str.len() > 0].copy()

print("=" * 80)
print("DISTRIBUSI LABEL PER SPLIT (DATA DENGAN BODY TERISI):")
print(d.groupby("split").label.value_counts().unstack().to_string())

tr, te = d[d.split == "train"], d[d.split == "dev_test"]

def probe(col, n=None):
    f = (lambda s: " ".join(str(s).split()[:n])) if n else str
    v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    m = LogisticRegression(max_iter=2000).fit(v.fit_transform(tr[col].map(f)), tr.label)
    return (m.predict(v.transform(te[col].map(f))) == te.label).mean() * 100, v, m

print("\n" + "=" * 80)
print("AKURASI PROBE LINIER (8 KATA VS PENUH):")
for col in ("title", "body", "text"):
    p_8 = probe(col, 8)[0]
    p_all = probe(col)[0]
    print(f"  {col:<10} 8 kata: {p_8:5.1f}% | penuh: {p_all:5.1f}%")

_, v, m = probe("text", 8)
fn = np.array(v.get_feature_names_out())
c = m.coef_[0]
print("\n" + "=" * 80)
print("15 TOKEN PALING CONDONG KE HOAKS (8 KATA):")
print(list(fn[np.argsort(c)[-15:]][::-1]))
print("\n15 TOKEN PALING CONDONG KE FAKTA (8 KATA):")
print(list(fn[np.argsort(c)[:15]]))

print("\n" + "=" * 80)
print("TEKS YANG MEMUAT 'CNN Indonesia' ATAU 'KOMPAS.com':")
matches = d[d.text.str.contains(r"CNN Indonesia|KOMPAS\.com", case=False, na=False)][["label", "source", "text"]]
print(f"Total ditemukan: {len(matches)} baris")
if len(matches) > 0:
    for idx, r in matches.head(10).iterrows():
        print(f"  [{r['label']}] ({r['source']}) : {r['text'][:140]}...")