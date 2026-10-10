"""
diagnosa_reviewer.py
Mengumpulkan data empiris sesuai 4 poin permintaan reviewer.
"""
import os, sys, re
import pandas as pd, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# 1. Pastikan text_pipeline termuat ulang
import importlib
import text_pipeline as tp
importlib.reload(tp)

print("=" * 85)
print("1. UJI BUG clean() DENGAN STRING CONTOH REVIEWER")
print("=" * 85)
s = "Judul klaim.\n=== KATEGORI: KONTEN YANG MENYESATKAN ===\nNARASI: isi klaim yang harus tetap ada.\n=====\nPenjelasan: bantahan"
hasil_uji = tp.clean(s)
print("Input   :\n", repr(s))
print("Output  :\n", repr(hasil_uji))
if "isi klaim yang harus tetap ada" in hasil_uji and "KATEGORI" not in hasil_uji:
    print("✓ UJI LULUS: Narasi dipertahankan, metadata & penjelasan terbuang!")
else:
    print("❌ UJI GAGAL: Periksa kembali regex clean()!")

print("\n" + "=" * 85)
print("2. PENGUKURAN TEKS FAKTA TERPOTONG DI TENGAH KALIMAT (frag)")
print("=" * 85)
p_tr = "data/processed_v2/train.csv"
p_te = "data/processed_v2/dev_test.csv"
if os.path.exists(p_tr) and os.path.exists(p_te):
    tr = pd.read_csv(p_tr); te = pd.read_csv(p_te)
    d = pd.concat([tr, te], ignore_index=True)

    def frag(t):
        p = re.split(r'(?<=[.!?])\s+', str(t).strip(), maxsplit=1)
        return len(p) > 1 and p[1][:1].islower()

    d["frag"] = d.text.map(frag)
    print("Persentase Teks Terpotong (Awalan Huruf Kecil) per Label & Sumber:")
    print(d.groupby(["label", "source"]).frag.mean().mul(100).round(1).to_string())

print("\n" + "=" * 85)
print("3. CEK DATA MENTAH TEMPO: text_new VS FullText")
print("=" * 85)
tempo_path = "data/raw/dataset_tempo_6k_cleaned.csv"
if not os.path.exists(tempo_path):
    tempo_path = "../data/raw/dataset_tempo_6k_cleaned.csv"

if os.path.exists(tempo_path):
    x = pd.read_csv(tempo_path, nrows=5)
    for c in ["text_new", "FullText"]:
        if c in x.columns:
            print(f"\nKolom '{c}' (5 sampel pertama):")
            for i, val in enumerate(x[c].astype(str).str[:120]):
                print(f"  [{i+1}] {repr(val)}")

print("\n" + "=" * 85)
print("4. UJI LEAVE-ONE-SOURCE-OUT (DENGAN class_weight='balanced')")
print("=" * 85)
if os.path.exists(p_tr) and os.path.exists(p_te):
    full = pd.concat([tr, te], ignore_index=True)
    out = []
    for src in sorted(full.source.unique()):
        held = full[full.source == src]
        rest = full[full.source != src]
        v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        # Menggunakan class_weight='balanced' untuk mengatasi ketimpangan kelas saat satu sumber ditahan
        clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(
            v.fit_transform(rest.text.astype(str)), rest.label
        )
        rec = (clf.predict(v.transform(held.text.astype(str))) == held.label.iloc[0]).mean()
        out.append((src, int(held.label.iloc[0]), len(held), round(rec * 100, 2)))
    print(pd.DataFrame(out, columns=["sumber_ditahan", "label", "n", "recall_balanced_%"]).to_string(index=False))

print("\n" + "=" * 85)
print("5. 15 CONTOH JUDUL GANDA MENTAH (TURNBACKHOAX & HOAX_ARCHIVE)")
print("=" * 85)
if os.path.exists(p_tr):
    tr["dup"] = tr.text.map(tp.dup_title)
    for s_name in ["turnbackhoax.id", "hoax_archive_15k"]:
        sub_dup = tr[(tr.source == s_name) & tr.dup].head(8)
        print(f"\n--- Sumber: {s_name} (Contoh Judul Ganda) ---")
        for i, (_, r) in enumerate(sub_dup.iterrows()):
            print(f"[{i+1}] Title : {repr(str(r.get('title', ''))[:80])}")
            print(f"    Text  : {repr(str(r.get('text', ''))[:150])}\n")