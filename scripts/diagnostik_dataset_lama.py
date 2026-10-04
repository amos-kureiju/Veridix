"""
scripts/diagnostik_dataset_lama.py
Audit Forensik Independen Data Lama INSPECT-AI:
1. Mengukur disparitas panjang kata (Length Confound) per label.
2. Mengukur prevalensi judul ganda dengan detektor robust (tahan elipsis & typo).
3. Uji Fisher's Exact Test korelasi format terhadap prediksi salah/benar.
4. Uji pohon keputusan: Seberapa akurat label bisa ditebak HANYA dari panjang kata?
"""

import os
import re
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, fisher_exact
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score

print("=" * 85)
print("🔬 AUDIT FORENSIK INDEPENDEN: DATASET LAMA (TRAIN, VAL, TEST)")
print("=" * 85)

# 1. Lokasi Dataset
DATA_DIR = "data/processed" if os.path.exists("data/processed") else "../data/processed"
splits = {}
for s in ["train", "val", "test"]:
    p = os.path.join(DATA_DIR, f"{s}.csv")
    if os.path.exists(p):
        splits[s] = pd.read_csv(p)
        print(f"✓ Berhasil memuat {s}.csv: {len(splits[s]):,} baris")
    else:
        print(f"❌ File {p} tidak ditemukan!")

if not splits:
    raise FileNotFoundError("Tidak ada file dataset yang ditemukan di data/processed!")

# -----------------------------------------------------------------------------
# [A] AUDIT DISPARITAS PANJANG KATA (LENGTH SHORTCUT AUDIT)
# -----------------------------------------------------------------------------
print("\n" + "-" * 85)
print("[A] DISTRIBUSI PANJANG KATA PER LABEL (MEMBUKTIKAN ASIMETRI 45/60 vs 80 KATA)")
print("-" * 85)

for s_name, df in splits.items():
    df['wc'] = df['text'].astype(str).str.split().str.len()
    f_wc = df[df.label == 0]['wc']
    h_wc = df[df.label == 1]['wc']
    
    ks_stat, ks_pval = ks_2samp(f_wc, h_wc)
    
    print(f"\n• SPLIT: {s_name.upper()} (Total {len(df):,} baris)")
    print(f"  - Fakta (0) : Mean={f_wc.mean():.1f} kata | Median={f_wc.median():.1f} | Min={f_wc.min()} | Max={f_wc.max()} | Std={f_wc.std():.1f}")
    print(f"  - Hoaks (1) : Mean={h_wc.mean():.1f} kata | Median={h_wc.median():.1f} | Min={h_wc.min()} | Max={h_wc.max()} | Std={h_wc.std():.1f}")
    print(f"  - Uji Kolmogorov-Smirnov : Statistik={ks_stat:.4f} (p-value={ks_pval:.1e})")
    if ks_stat > 0.15:
        print(f"  ⚠️ PERINGATAN: Disparitas panjang sangat tinggi! Model dapat menebak label dari jumlah kata.")

# -----------------------------------------------------------------------------
# [B] TEBAK LABEL HANYA DARI PANJANG KATA (DECISION TREE ON LENGTH)
# -----------------------------------------------------------------------------
print("\n" + "-" * 85)
print("[B] UJI DECISION TREE: AKURASI TEBAKAN JIKA HANYA MELIHAT JUMLAH KATA & KARAKTER")
print("-" * 85)

tr_df = splits['train']
te_df = splits['test']

def extract_len_features(df):
    t = df['text'].astype(str)
    return np.c_[
        t.str.split().str.len(),          # jumlah kata
        t.str.len(),                      # jumlah karakter
        t.str.count(r'[.!?]'),            # jumlah kalimat
        t.str.count(r',')                 # jumlah koma
    ]

X_tr_len = extract_len_features(tr_df)
X_te_len = extract_len_features(te_df)

dt = DecisionTreeClassifier(max_depth=3, random_state=42)
dt.fit(X_tr_len, tr_df['label'])
acc_len = accuracy_score(te_df['label'], dt.predict(X_te_len)) * 100

print(f"• Akurasi di Test Set HANYA bermodalkan fitur panjang (tanpa membaca kata): {acc_len:.2f}%")
print(f"  (Jika > 60%, panjang teks adalah 'jalan pintas' aktif yang dieksploitasi IndoBERT).")

# -----------------------------------------------------------------------------
# [C] DETEKSI JUDUL GANDA ROBUST (FUZZY TOKEN OVERLAP TAHAN ELIPSIS & TYPO)
# -----------------------------------------------------------------------------
print("\n" + "-" * 85)
print("[C] PREVALENSI JUDUL GANDA: DETEKTOR KAKU VS DETEKTOR ROBUST (TOKEN OVERLAP)")
print("-" * 85)

def dup_exact(t):
    """Detektor kaku lama"""
    t = str(t).strip()
    first = re.split(r'(?<=[.!?])\s+', t, maxsplit=1)[0].lower().strip(" .")
    return len(first) >= 15 and t.lower().count(first) >= 2

def dup_robust(t, min_token_overlap=0.75):
    """Detektor robust: tahan elipsis (...), koma, dan perbedaan minor"""
    t = str(t).strip()
    parts = re.split(r'(?<=[.!?])\s+', t, maxsplit=1)
    if len(parts) < 2:
        return False
    
    first_tokens = set(re.findall(r'\b\w{3,}\b', parts[0].lower()))
    if len(first_tokens) < 4:
        return False
    
    # Ambil 15 kata pertama di bagian badan teks
    rest_head = " ".join(parts[1].split()[:len(parts[0].split()) + 5])
    rest_tokens = set(re.findall(r'\b\w{3,}\b', rest_head.lower()))
    
    overlap = len(first_tokens & rest_tokens) / len(first_tokens)
    return overlap >= min_token_overlap

for s_name, df in splits.items():
    exact_f = df[df.label == 0]['text'].map(dup_exact).mean() * 100
    exact_h = df[df.label == 1]['text'].map(dup_exact).mean() * 100
    
    robust_f = df[df.label == 0]['text'].map(dup_robust).mean() * 100
    robust_h = df[df.label == 1]['text'].map(dup_robust).mean() * 100
    
    print(f"• {s_name.upper():<5} :")
    print(f"  - Detektor Kaku   : Fakta = {exact_f:5.2f}% | Hoaks = {exact_h:5.2f}% | Selisih = {exact_f - exact_h:5.2f}%")
    print(f"  - Detektor Robust : Fakta = {robust_f:5.2f}% | Hoaks = {robust_h:5.2f}% | Selisih = {robust_f - robust_h:5.2f}%")

# -----------------------------------------------------------------------------
# [D] UJI FISHER: APAKAH JUDUL GANDA BERKORELASI DENGAN PREDIKSI BENAR/SALAH?
# -----------------------------------------------------------------------------
print("\n" + "-" * 85)
print("[D] UJI FISHER'S EXACT: KORELASI FORMAT JUDUL GANDA TERHADAP KELAS")
print("-" * 85)

te = splits['test']
is_fakta = (te['label'] == 0).values
has_dup  = te['text'].map(dup_robust).values

# Tabel Kontingensi 2x2
#                  Judul Ganda   Bukan Judul Ganda
# Fakta (Label 0)       a                b
# Hoaks (Label 1)       c                d
a = np.sum(is_fakta & has_dup)
b = np.sum(is_fakta & ~has_dup)
c = np.sum(~is_fakta & has_dup)
d = np.sum(~is_fakta & ~has_dup)

odds_ratio, p_fisher = fisher_exact([[a, b], [c, d]])

print(f"Tabel Kontingensi (Test Set, N={len(te):,}):")
print(f"  • Fakta : Judul Ganda = {a:>5} | Bukan = {b:>5}")
print(f"  • Hoaks : Judul Ganda = {c:>5} | Bukan = {d:>5}")
print(f"• Odds Ratio Fisher : {odds_ratio:.2f}")
print(f"• p-value Fisher    : {p_fisher:.2e}")
if p_fisher < 0.001:
    print("  ⚠️ KESIMPULAN SIGNIFIKAN: Format judul ganda berkorelasi sangat kuat dan tidak seimbang antar label!")

print("\n" + "=" * 85)
print("✓ AUDIT FORENSIK SELESAI!")
print("=" * 85)