r"""
evaluasi_set_luar.py — menilai SET UJI BARU lewat jalur APLIKASI yang sama (validasi, domain, praproses, 3 seed):
pasangan kontrafaktual, transkripsi set 2x2, atau teks hasil OCR. Tidak menyentuh lockbox.

CSV wajib: id, text, label (0 = fakta, 1 = hoaks). Kolom lain (mis. gaya, sel, sumber, split) boleh dipakai untuk rincian.
    .\.venv\Scripts\python.exe evaluasi_set_luar.py set.csv --by gaya
    .\.venv\Scripts\python.exe evaluasi_set_luar.py set.csv --by gaya,sumber --out hasil_set.csv
    python evaluasi_set_luar.py set.csv --stub      (alur tanpa model, untuk uji skrip)
Tetapkan kriteria SEBELUM menjalankan, dan jalankan SEKALI per set uji.
Yang dilaporkan: cakupan (dinilai / ditolak / luar cakupan / ambigu), akurasi pada yang dinilai dengan interval Wilson,
recall hoaks, spesifisitas fakta, serta "akurasi ketat" (non-dinilai dihitung salah) agar penolakan tidak menyembunyikan kegagalan.
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
    by = args[args.index("--by") + 1].split(","); 
if "--out" in args:
    out_path = args[args.index("--out") + 1]
pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--by", "--out"))]
if not pos:
    sys.exit("Beri jalur CSV.")
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
    pred = (1 if h["label"] == "BERPOLA HOAKS" else 0) if h["status"] == "dinilai" else None
    rows.append(dict(id=r["id"], status=h["status"], votes_hoax=h.get("votes_hoax", ""), pred=pred))
res = df.merge(pd.DataFrame(rows), on="id", how="left")
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
d = res[res.status == "dinilai"]
for lab, nama in ((1, "recall hoaks"), (0, "spesifisitas fakta")):
    dd = d[d.label == lab]
    if len(dd):
        k = int((dd.pred == lab).sum()); lo, hi = wilson(k, len(dd))
        print(f"{nama:<20} {k}/{len(dd)} = {k/len(dd)*100:.1f}% [{lo*100:.0f}-{hi*100:.0f}]")
print(f"\nCakupan keseluruhan: dinilai {len(d)}/{len(res)} = {len(d)/len(res)*100:.1f}%")
print(f"Baris per teks tersimpan: {out_path}")