"""
cek_sebelum_beku_agent.py
Mengumpulkan data empiris sesuai perintah agen/reviewer:
  1. Tag apa saja yang terbuang ke label1_ambigu.csv
  2. Tabel sub-topik x split x label
  3. Paparan C1 parafrasa per sumber
  4. Kemiripan TF-IDF Cosine eval set vs train
  5. Pemeriksaan ke-20 baris yang memuat nama media
"""
import os, re
import pandas as pd, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import text_pipeline as tp

O = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"
assert os.path.exists(O), f"Folder {O} tidak ditemukan!"

d  = pd.read_csv(f"{O}/dataset_v2_full.csv")
am = pd.read_csv(f"{O}/label1_ambigu.csv")
eb = pd.read_csv(f"{O}/eval_benar.csv")
ek = pd.read_csv(f"{O}/eval_kompas_cekfakta.csv")

nk = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"^\s*(?:\[[^\]]{1,25}\]\s*)+", "", str(s).lower()))

print("=" * 80)
print("1. TAG APA SAJA YANG TERBUANG KE label1_ambigu.csv:")
print("=" * 80)
tg = am.title.str.extract(r"^\s*[\[\(\{]([^\]\)\}]{1,25})[\]\)\}]")[0].str.upper().fillna("(tanpa tag)")
print(tg.value_counts().head(20).to_string())
print("\nSebaran Sumber pada label1_ambigu:")
print(am.groupby("source").size().to_string())

print("\n" + "=" * 80)
print("2. TABEL SUB-TOPIK x SPLIT x LABEL (PASCA PENYEIMBANGAN):")
print("=" * 80)
print(pd.crosstab([d.sub_topic, d.split], d.label).to_string())

print("\n" + "=" * 80)
print("3. PAPARAN C1 PARAFRASA (dup_title_para) PER SUMBER:")
print("=" * 80)
print(d.assign(p=d.text.map(tp.dup_title_para)).groupby(["label", "source"]).p.mean().mul(100).round(2).to_string())

print("\n" + "=" * 80)
print("4. KEMIRIPAN TF-IDF COSINE EVAL SET VS DATA LATIH (TRAIN):")
print("=" * 80)
tr_df = d[d.split == "train"]
v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(tr_df.title.astype(str))
for nm, e in [("eval_benar", eb), ("eval_kompas", ek)]:
    sim_mat = (v.transform(e.title.astype(str)) @ v.transform(tr_df.title.astype(str)).T).max(axis=1).toarray().ravel()
    print(f"  • {nm:<15} : cos > 0.70 = {int((sim_mat > 0.70).sum()):>3} sampel | cos > 0.90 = {int((sim_mat > 0.90).sum()):>3} sampel")

print("\n" + "=" * 80)
print("5. PEMERIKSAAN KE-20 TEKS YANG MEMUAT 'CNN Indonesia' ATAU 'KOMPAS.com':")
print("=" * 80)
matches = d[d.text.astype(str).str.contains(r"CNN Indonesia|KOMPAS\.com", case=False, na=False)][["label", "source", "text"]]
print(f"Total baris ditemukan: {len(matches)}")
for idx, r in matches.iterrows():
    lbl = "FAKTA" if r["label"] == 0 else "HOAKS"
    print(f"\n[{lbl}] ({r['source']}):")
    print(f"  {r['text'][:180]}...")