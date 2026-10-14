# Memeriksa bahwa bobot yang terunduh di laptop adalah bobot yang menghasilkan prediksi yang sama dengan bobot yang diunduh di Colab.
import os, sys, hashlib
import numpy as np, pandas as pd

sys.path.insert(0, os.getcwd())
import inferensi_lokal as il

F = "data/processed_v2"
SEEDS = [42, 123, 999]
assert not any("lockbox" in p.lower() for p in (F,)), "jangan arahkan ke lockbox"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

va = pd.read_csv(f"{F}/val.csv"); te = pd.read_csv(f"{F}/dev_test.csv")
saved = pd.read_csv("prediksi_val_dev.csv")
print(f"Perangkat: {il.DEVICE} | val={len(va)} dev={len(te)} | baris prediksi Colab={len(saved)}")

print("\n=== SHA-256 CHECKPOINT ===")
for s in SEEDS:
    f = f"ckpt_ce_{s}.pt"
    print(f"{f:<16} {os.path.getsize(f)/1e6:6.1f} MB  {sha(f)}")

print("\n=== PREDIKSI LAPTOP vs COLAB ===")
rev = None
for s in SEEDS:
    m = il.load_ckpt(f"ckpt_ce_{s}.pt"); rev = il.base_model_revision(m)
    for nm, d, sp in (("val", va, "val"), ("dev_test", te, "dev_test")):
        p, _ = il.predict_texts(m, d.text.values)
        ref = saved[saved.split == sp].set_index("id").loc[d.id, f"pred_ce_{s}"].to_numpy()
        print(f"seed {s:<4} {nm:<9} akurasi laptop {np.mean(p == d.label.values)*100:6.2f}% | "
              f"kecocokan dengan Colab {np.mean(p == ref)*100:6.2f}% ({int((p != ref).sum())} beda dari {len(d)})")
    del m

print("\nRevisi model pralatih (config._commit_hash):", rev)
print("Catat revisi ini + tiga hash di protokol. Bila None, simpan salinan lokal model dasar (snapshot_download) dan hash-nya.")