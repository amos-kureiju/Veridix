"""
inspeksi_audit_pembimbing.py — Membedah teks korpus yang tertolak oleh gerbang bahasa
(rasio kata fungsi < 0.02 pada teks >= 15 kata).
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.getcwd())
from src.utils.input_validation import validate_input_text

print("=" * 80)
print("INSPEKSI TEKS KORPUS YANG TERTOLAK GERBANG BAHASA (STOPWORD RATIO < 0.02)")
print("=" * 80)

F = "data/processed_v2"
corp = pd.concat([pd.read_csv(f"{F}/{s}.csv") for s in ("train", "val", "dev_test")], ignore_index=True)

ditolak_list = []
for i, r in corp.iterrows():
    v = validate_input_text(r["text"])
    # Tangkap kondisi spesifik: teks cukup panjang (>=15 kata) tetapi rasio kata fungsi < 0.02
    if not v["ok"] and v.get("stopword_ratio") is not None and v["stopword_ratio"] < 0.02 and v["n_words"] >= 15:
        ditolak_list.append({
            "label": int(r["label"]),
            "source": r.get("source", "-"),
            "n_words": v["n_words"],
            "sw_ratio": v["stopword_ratio"],
            "text": str(r["text"])
        })

df_tolak = pd.DataFrame(ditolak_list)
print(f"Total tertolak gerbang bahasa: {len(df_tolak)} teks")

if len(df_tolak) > 0:
    n_fakta = int((df_tolak.label == 0).sum())
    n_hoaks = int((df_tolak.label == 1).sum())
    print(f"Rincian: Fakta = {n_fakta} teks, Hoaks = {n_hoaks} teks\n")
    
    print("--- CONTOH HOAKS YANG TERTOLAK (Karakteristik Teks Sedikit Kata Fungsi) ---")
    hoaks_samples = df_tolak[df_tolak.label == 1].head(10).reset_index()
    for idx, r in hoaks_samples.iterrows():
        print(f"[{idx+1}] (Kata: {r['n_words']}, Rasio SW: {r['sw_ratio']:.4f}, Sumber: {r['source']})")
        print(f"     Teks: {repr(r['text'][:130])}")
    
    print("\n--- CONTOH FAKTA YANG TERTOLAK ---")
    fakta_samples = df_tolak[df_tolak.label == 0].reset_index()
    for idx, r in fakta_samples.iterrows():
        print(f"[{idx+1}] (Kata: {r['n_words']}, Rasio SW: {r['sw_ratio']:.4f}, Sumber: {r['source']})")
        print(f"     Teks: {repr(r['text'][:130])}")
else:
    print("Tidak ada teks korpus yang tertolak pada kriteria ini.")

print("=" * 80)