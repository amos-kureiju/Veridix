"""
cek_reviewer_n2_n6.py
Mengekstrak data N2 (tag per sumber) dan N6 (simulasi jumlah pasangan strata)
untuk dikirim ke reviewer sebelum rebuild.
"""
import os, re
import pandas as pd, numpy as np

RAW_DIR = "data/raw" if os.path.exists("data/raw") else "../data/raw"
SOURCES = [
    dict(name="turnbackhoax.id",   label=1, file="dataset_turnbackhoax_10_cleaned", title=["Title"], body=["Clean Narasi", "Narasi"], date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="komdigi.go.id",     label=1, file="komdigi_hoaks",                   title=["title"], body=["body_text", "excerpt"],   date=["published_at"]),
    dict(name="hoax_archive_15k",  label=1, file="hoax_dataset_with_text",          title=["judul"], body=["teks", "deskripsi"],     date=["tanggal"]),
    dict(name="tempo.co",          label=0, file="dataset_tempo_6k_cleaned",        title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="cnnindonesia.com",  label=0, file="dataset_cnn_10k_cleaned",         title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="kompas.com",        label=0, file="dataset_kompas_4k_cleaned",       title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
]

def pick(row, names):
    for n in names:
        if n in row.index and pd.notna(row[n]) and str(row[n]).strip() not in ("", "nan", "None"):
            return str(row[n]).strip()
    return ""

dfs = []
for s in SOURCES:
    files = sorted(f for f in os.listdir(RAW_DIR) if f.startswith(s["file"]))
    if files:
        p = os.path.join(RAW_DIR, files[0])
        d = pd.read_excel(p) if p.endswith((".xlsx", ".xls")) else pd.read_csv(p)
        out = pd.DataFrame({
            "title": [pick(r, s["title"]) for _, r in d.iterrows()],
            "body":  [pick(r, s["body"])  for _, r in d.iterrows()],
            "date":  pd.to_datetime([pick(r, s["date"]) for _, r in d.iterrows()], errors="coerce", format="mixed"),
            "source": s["name"], "label": s["label"]
        })
        dfs.append(out)

raw = pd.concat(dfs, ignore_index=True)

print("=" * 80)
print("1. HASIL N2: DISTRIBUSI TAG PER LABEL & SUMBER (MENCARI LABEL NOISE)")
print("=" * 80)
tag = raw.title.str.extract(r"^\s*[\[\(\{]([^\]\)\}]{1,25})[\]\)\}]")[0].str.upper()
print(raw.assign(tag=tag).groupby(["label", "source", "tag"], dropna=False).size().to_string())

print("\n" + "=" * 80)
print("2. CONTOH JUDUL KOMPAS YANG MEMUAT TAG [ ... ]:")
print("=" * 80)
print(raw[(raw.source == "kompas.com") & tag.notna()].title.head(15).to_string())

# Simulasi N6 pada dataset saat ini
p_cur = "data/processed_v2/dataset_v2_full.csv"
if os.path.exists(p_cur):
    df_cur = pd.read_csv(p_cur)
    df_cur["n_words"] = df_cur["text"].astype(str).str.split().str.len()
    df_cur["len_bin"] = pd.cut(df_cur.n_words, bins=[0, 20, 30, 40, 50, 60, 10_000]).astype(str)
    df_cur["year_bin"] = pd.cut(pd.to_datetime(df_cur.date, errors="coerce").dt.year, [0, 2019, 2021, 2022, 2023, 3000]).astype(str)

    def match_n(d, keys):
        c = d.groupby(keys + ["label"], observed=True).size().unstack("label", fill_value=0)
        return int(2 * c.min(axis=1).sum())

    print("\n" + "=" * 80)
    print("3. HASIL N6: SIMULASI JUMLAH PASANGAN STRATA")
    print("=" * 80)
    for keys in (["sub_topic"], ["sub_topic", "len_bin"], ["sub_topic", "year_bin"], ["sub_topic", "len_bin", "year_bin"]):
        n_ = match_n(df_cur, keys)
        print(f"{'+'.join(keys):<36} pasangan={n_:>6,}  train≈{int(n_*0.7):,}")