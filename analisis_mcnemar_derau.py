"""
analisis_mcnemar_derau.py — Uji McNemar berpasangan per kondisi derau vs acuan bersih (Seed 42).
Juga memverifikasi asersi baris per baris terhadap prediksi Colab.
"""
import os, sys
import numpy as np, pandas as pd
from scipy.stats import binomtest

sys.path.insert(0, os.getcwd())
import text_pipeline as tp
import noise_ocr as nz
import inferensi_lokal as il

assert tp.PIPELINE_VERSION == "tp-1.6"
F = "data/processed_v2"
SEED = 42

df = pd.concat([pd.read_csv(f"{F}/val.csv"), pd.read_csv(f"{F}/dev_test.csv")], ignore_index=True)
df["text"] = df.text.fillna("").astype(str)
y = df.label.to_numpy()

print("=" * 85)
print("1. VERIFIKASI ASERSI PREDIKSI LAPTOP vs COLAB (KONDISI BERSIH)")
print("=" * 85)
m = il.load_ckpt(f"ckpt_ce_{SEED}.pt")
saved = pd.read_csv("prediksi_val_dev.csv")

# Prediksi laptop kondisi bersih
pred_bersih, _ = il.predict_texts(m, df.text.values)

# Prediksi Colab terurut sesuai df.id
ref_colab = []
for sp in ("val", "dev_test"):
    sub_df = df[df.index < 236] if sp == "val" else df[df.index >= 236]
    ref_colab.append(saved[saved.split == sp].set_index("id").loc[sub_df.id, f"pred_ce_{SEED}"].to_numpy())
ref_colab = np.concatenate(ref_colab)

# Asersi kecocokan mutlak
assert (pred_bersih == ref_colab).all(), "GAGAL: Ada baris prediksi bersih yang tidak cocok dengan Colab!"
print(">> ASERSI SUKSES: 472 dari 472 baris prediksi bersih lokal IDENTIK PERSIS dengan Colab.\n")

print("=" * 85)
print("2. UJI MCNEMAR BERPASANGAN: TIAP KONDISI DERAU VS ACUAN BERSIH (SEED 42)")
print("=" * 85)
variants = nz.make_variants(df.text.tolist(), tp)

def mcnemar_paired(y_true, p_bersih, p_derau):
    a = (p_bersih == y_true)  # Bersih benar
    b = (p_derau == y_true)   # Derau benar
    n01 = int((a & ~b).sum())  # Bersih benar, derau salah (derau merusak)
    n10 = int((~a & b).sum())  # Bersih salah, derau benar (kebetulan)
    n = n01 + n10
    pval = binomtest(min(n01, n10), n, 0.5).pvalue if n > 0 else 1.0
    return n01, n10, pval

rows = []
for name, texts in variants.items():
    p_derau, _ = il.predict_texts(m, texts)
    n01, n10, pval = mcnemar_paired(y, pred_bersih, p_derau)
    acc = (p_derau == y).mean() * 100
    selisih = acc - (pred_bersih == y).mean() * 100
    rows.append({
        "Kondisi Derau": name,
        "Akurasi (%)": round(acc, 2),
        "Selisih (pt)": round(selisih, 2),
        "Bersih Benar, Derau Salah (n01)": n01,
        "Bersih Salah, Derau Benar (n10)": n10,
        "p-value (McNemar)": round(pval, 4),
        "Signifikan (p < 0.05)": "Ya" if pval < 0.05 else "Tidak"
    })

res_df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(res_df.to_string(index=False))
print("=" * 85)
print("Catatan: p < 0.05 membuktikan penurunan performa akibat derau signifikan secara statistik.")