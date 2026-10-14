# ketahanan terhadap derau SIMULASI ala OCR pada val+dev_test (n=472). TIDAK menyentuh lockbox.
import os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.getcwd())
import text_pipeline as tp
import noise_ocr as nz
import inferensi_lokal as il

assert tp.PIPELINE_VERSION == "tp-1.6"
F = "data/processed_v2"
SEEDS = [int(s) for s in sys.argv[1:]] or [42, 123, 999]

df = pd.concat([pd.read_csv(f"{F}/val.csv"), pd.read_csv(f"{F}/dev_test.csv")], ignore_index=True)
df["text"] = df.text.fillna("").astype(str)
print(f"Evaluasi pada val+dev_test: n={len(df)} | seed: {SEEDS} | perangkat: {il.DEVICE}")
variants = nz.make_variants(df.text.tolist(), tp)

per_seed = []
for s in SEEDS:
    m = il.load_ckpt(f"ckpt_ce_{s}.pt")
    res = nz.evaluate(lambda texts: il.predict_texts(m, texts)[0], df, tp, variants)
    res["seed"] = s; per_seed.append(res); print(f"  seed {s} selesai")
    del m

R = pd.concat(per_seed)
g = R.groupby("kondisi", sort=False)
out = g.agg(akurasi=("akurasi", "mean"), akurasi_min=("akurasi", "min"), akurasi_maks=("akurasi", "max"),
            recall_hoaks=("recall_hoaks", "mean"), spesifisitas_fakta=("spesifisitas_fakta", "mean"),
            share_hoaks=("share_diprediksi_hoaks", "mean")).reset_index()
base = float(out.loc[0, "akurasi"])
out["selisih_vs_bersih"] = out.akurasi - base
n = len(df)
out["ci95"] = [f"[{nz.wilson(round(a * n), n)[0]*100:4.1f}-{nz.wilson(round(a * n), n)[1]*100:4.1f}]" for a in out.akurasi]

pd.set_option("display.width", 220)
show = out.copy()
for c in ("akurasi", "akurasi_min", "akurasi_maks", "recall_hoaks", "spesifisitas_fakta", "share_hoaks"): show[c] = (show[c] * 100).round(1)
show["selisih_vs_bersih"] = (show.selisih_vs_bersih * 100).round(1)
print("\n(angka dalam %, rerata lintas seed; CI = Wilson perkiraan untuk n=472)")
print(show.to_string(index=False))
out.to_csv("hasil_derau_ocr.csv", index=False)
print("\nTersimpan: hasil_derau_ocr.csv")
print("Baca: turunnya spesifisitas fakta dengan share_hoaks naik = derau mendorong vonis HOAKS (seperti contoh 'me- mastikan').")