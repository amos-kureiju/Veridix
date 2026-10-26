"""evaluasi_set_luar.py — Versi Perbaikan Audit Lengkap.

- Mencegah crash pada CSV kosong dan memvalidasi label (hanya 0 dan 1).
- Membaca 'seed_decisions' biner murni (kebal kesalahan pembulatan desimal).
- Menggabungkan baris berbasis indeks (kebal duplikasi ID).
- Melaporkan Akurasi Ketat, Recall Ketat, dan Spesifisitas Ketat secara konsisten.
"""

import os
import sys
from lime.lime_text import LimeTextExplainer
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
pos = [
    a
    for i, a in enumerate(args)
    if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--by", "--out"))
]
if not pos:
  sys.exit("Beri jalur berkas CSV.")

csv_path = pos[0]
if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
    sys.exit(f"Galat: Berkas '{csv_path}' tidak ditemukan atau kosong (0 byte).")

try:
    df = pd.read_csv(csv_path)
except Exception as e:
    sys.exit(f"Galat membaca CSV '{csv_path}': {e}")

if len(df) == 0:
    sys.exit(f"Berkas '{csv_path}' hanya berisi header tanpa baris data (0 baris).")

for k in ("id", "text", "label"):
    assert k in df.columns, f"Kolom wajib tidak ada: {k}"
for k in by:
    assert k in df.columns, f"Kolom --by tidak ada: {k}"

# Tolak bila ada label kosong (NaN) atau label bukan 0 dan 1
if df["label"].isna().any():
    sys.exit("Galat: Terdapat baris dengan label kosong (NaN/null). Seluruh baris wajib memiliki label 0 atau 1.")

invalid_labels = set(df["label"].unique()) - {0, 1}
if invalid_labels:
    sys.exit(f"Galat: Terdapat nilai label tidak valid: {invalid_labels}. Hanya menerima 0 atau 1.")


class _Stub:
  seeds = [42, 123, 999]

  def seed_probs_each(self, texts):
    return np.array([
        (
            [0.95, 0.90, 0.99]
            if ("viral" in t.lower() or "hoaks" in t.lower())
            else [0.05, 0.10, 0.02]
        )
        for t in texts
    ])


if STUB:
  pen = Penilai(_Stub())
else:
  from src.ml.inference import get_predictor

  pen = get_predictor()


def wilson(k, n, z=1.96):
  if n == 0:
    return (np.nan, np.nan)
  p = k / n
  den = 1 + z * z / n
  c = (p + z * z / (2 * n)) / den
  h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
  return max(c - h, 0), min(c + h, 1)


rows = []
for _, r in df.iterrows():
  t_val = str(r["text"]) if pd.notna(r["text"]) else ""
  h = pen.nilai(t_val, explain=False, debug=True)

  pred_final = (
      (1 if h["label"] == "BERPOLA HOAKS" else 0)
      if h["status"] == "dinilai"
      else None
  )

  # Ambil keputusan biner per-seed (0 atau 1) langsung dari engine
  decisions = h.get("seed_decisions", {})
    # Fallback yang aman (mendukung format kamus maupun list)
  if not decisions and "debug" in h:
        raw_p = h["debug"].get("prob_hoax_per_seed", {})
        if isinstance(raw_p, dict):
            decisions = {s: int(float(v) >= 0.5) for s, v in raw_p.items() if v is not None}
        elif isinstance(raw_p, (list, tuple)) and len(raw_p) == 3:
            decisions = {42: int(float(raw_p[0]) >= 0.5), 123: int(float(raw_p[1]) >= 0.5), 999: int(float(raw_p[2]) >= 0.5)}

  rows.append({
      "status": h["status"],
      "votes_hoax": h.get("votes_hoax", ""),
      "pred": pred_final,
      "pred_42": decisions.get(42),
      "pred_123": decisions.get(123),
      "pred_999": decisions.get(999),
  })

# Penggabungan berbasis indeks (kebal terhadap duplikasi ID)
res = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
res.to_csv(out_path, index=False)

grp = by + ["label"]
print("=" * 100)
print(f"Set: {pos[0]} | n={len(res)} | Rincian menurut: {grp}")
print("=" * 100)
for key, g in res.groupby(grp):
  n = len(g)
  d = g[g.status == "dinilai"]
  nd = len(d)
  benar = int((d.pred == d.label).sum())
  lo, hi = wilson(benar, nd)
  ket = (
      f"label={key[-1]}"
      if len(grp) == 1
      else f"{dict(zip(grp, key if isinstance(key, tuple) else (key,)))}"
  )
  acc_dinilai_str = (
      f"{benar}/{nd} = {benar/nd*100:.1f}% [{lo*100:.0f}-{hi*100:.0f}]"
      if nd > 0
      else "N/A (0 dinilai)"
  )
  print(
      f"{ket}\n   n={n} | dinilai={nd} ambigu={(g.status=='ambigu').sum()}"
      f" luar_cakupan={(g.status=='di_luar_domain').sum()}"
      f" ditolak={(g.status=='ditolak').sum()} | akurasi pada yang dinilai"
      f" {acc_dinilai_str} | akurasi ketat {benar}/{n} = {benar/n*100:.1f}%"
      + ("   <-- n<30: interval sangat lebar" if n < 30 else "")
  )

# Ringkasan Kinerja Keseluruhan
print("-" * 100)
d = res[res.status == "dinilai"]
for lab, nama in ((1, "recall hoaks"), (0, "spesifisitas fakta")):
  dd = d[d.label == lab]
  total_label = int((res.label == lab).sum())
  if total_label > 0:
    k = int((dd.pred == lab).sum())
    lo, hi = wilson(k, len(dd))
    rec_dinilai_str = (
        f"{k}/{len(dd)} = {k/len(dd)*100:.1f}% [{lo*100:.0f}-{hi*100:.0f}]"
        if len(dd) > 0
        else "N/A"
    )
    rec_ketat_str = f"{k}/{total_label} = {k/total_label*100:.1f}%"
    print(
        f"{nama:<22} (dinilai) {rec_dinilai_str:<26} | ketat: {rec_ketat_str}"
    )

print(
    f"\nCakupan keseluruhan: dinilai {len(d)}/{len(res)} ="
    f" {len(d)/len(res)*100:.1f}%"
)
print(f"Baris per teks tersimpan: {out_path}")