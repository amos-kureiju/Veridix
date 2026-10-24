"""
evaluasi_set_luar.py — Versi Perbaikan Audit.
- Menggabungkan baris berbasis indeks (kebal duplikasi ID).
- Menyimpan rincian prediksi per-seed (pred_42, pred_123, pred_999).
- Menghitung akurasi ketat, recall ketat, dan spesifisitas ketat di bagian akhir.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
from src.ml.inference import Penilai  # noqa: E402

args = sys.argv[1:]
STUB = "--stub" in args
by = []
out_path = "hasil_set_luar.csv"
if "--by" in args:
    by = args[args.index("--by") + 1].split(",")
if "--out" in args:
    out_path = args[args.index("--out") + 1]
pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--by", "--out"))]
if not pos:
    sys.exit("Beri jalur berkas CSV.")
df = pd.read_csv(pos[0])
for k in ("id", "text", "label"):
    assert k in df.columns, f"kolom wajib tidak ada: {k}"
for k in by:
    assert k in df.columns, f"kolom --by tidak ada: {k}"


class _Stub:
    seeds = [42, 123, 999]
    def seed_probs_each(self, texts):
        return np.array([[0.95, 0.9, 0.99] if ("viral" in t.lower() or "hoaks" in t.lower()) else [0.05, 0.1, 0.02] for t in texts])


if STUB:
    pen = Penilai(_Stub())
else:
    from src.ml.inference import get_predictor
    pen = get_predictor()


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(c - h, 0), min(c + h, 1)


rows = []
for _, r in df.iterrows():
    h = pen.nilai(str(r["text"]) if pd.notna(r["text"]) else "", explain=False)
    pred_final = (1 if h["label"] == "BERPOLA HOAKS" else 0) if h["status"] == "dinilai" else None
    
    # Ambil probabilitas/prediksi per seed jika tersedia
    seed_probs = h.get("consensus_details", {}).get("seed_probabilities", {})
    row_dict = {
        "status": h["status"],
        "votes_hoax": h.get("votes_hoax", ""),
        "pred": pred_final,
        "pred_42": (1 if seed_probs.get(42, 0) >= 0.5 else 0) if seed_probs else None,
        "pred_123": (1 if seed_probs.get(123, 0) >= 0.5 else 0) if seed_probs else None,
        "pred_999": (1 if seed_probs.get(999, 0) >= 0.5 else 0) if seed_probs else None,
    }
    rows.append(row_dict)

# Penggabungan berbasis indeks baris (kebal terhadap ID ganda)
res = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
res.to_csv(out_path, index=False)

grp = by + ["label"]
print("=" * 100); print(f"Set: {pos[0]} | n={len(res)} | rincian menurut: {grp}"); print("=" * 100)
for key, g in res.groupby(grp):
    n = len(g); d = g[g.status == "dinilai"]; nd = len(d)
    benar = int((d.pred == d.label).sum())
    lo, hi = wilson(benar, nd)
    ket = (f"label={key[-1]}" if len(grp) == 1 else f"{dict(zip(grp, key if isinstance(key, tuple) else (key,)))}")
    print(f"{ket}\n   n={n} | dinilai={nd} ambigu={(g.status=='ambigu').sum()} luar_cakupan={(g.status=='di_luar_domain').sum()} ditolak={(g.status=='ditolak').sum()}"
          f" | akurasi pada yang dinilai {benar}/{nd}" + (f" = {benar/nd*100:.1f}% [{lo*100:.0f}-{hi*100:.0f}]" if nd else "")
          + f" | akurasi ketat {benar}/{n} = {benar/n*100:.1f}%" + ("   <-- n<30: interval sangat lebar" if n < 30 else ""))

# Ringkasan Kinerja (Kinerja pada yang Dinilai vs Kinerja Ketat)
d = res[res.status == "dinilai"]
print("-" * 100)
for lab, nama in ((1, "recall hoaks"), (0, "spesifisitas fakta")):
    dd = d[d.label == lab]
    total_label = (res.label == lab).sum()
    if len(dd):
        k = int((dd.pred == lab).sum()); lo, hi = wilson(k, len(dd))
        print(f"{nama:<22} (dinilai) {k}/{len(dd)} = {k/len(dd)*100:.1f}% [{lo*100:.0f}-{hi*100:.0f}]"
              f" | ketat: {k}/{total_label} = {k/total_label*100:.1f}%")

print(f"\nCakupan keseluruhan: dinilai {len(d)}/{len(res)} = {len(d)/len(res)*100:.1f}%")
print(f"Baris per teks tersimpan: {out_path}")