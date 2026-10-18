"""
kalibrasi_gerbang_domain.py — seberapa sering gerbang sistem (validasi masukan + guardrail domain) menolak teks yang
SEBENARNYA ada di korpus latih/val/dev_test? Seharusnya hampir nol, dan TIDAK asimetris antara hoaks dan fakta.
Hanya membaca data beku; TIDAK menyentuh lockbox.
Jalankan dari root proyek:  .\\.venv\\Scripts\\python.exe kalibrasi_gerbang_domain.py

Catatan metode: filter korpus dahulu diterapkan pada teks PENUH sebelum dipotong 60 kata, sedangkan berkas CSV hanya
menyimpan teks yang sudah dipotong. Karena itu kata kunci domain bisa hilang akibat pemotongan, jadi angka penolakan
domain di sini adalah BATAS ATAS dari penolakan yang sebenarnya.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
from src.utils.input_validation import validate_input_text  # noqa: E402
from src.utils.political_guardrail import check_political_domain  # noqa: E402

F = os.environ.get("DATA_DIR", "data/processed_v2")
d = pd.concat([pd.read_csv(f"{F}/{s}.csv").assign(split=s) for s in ("train", "val", "dev_test")], ignore_index=True)
d["text"] = d.text.fillna("").astype(str)

hasil = []
for t in d.text:
    v = validate_input_text(t)
    if not v["ok"]:
        hasil.append(("ditolak", v["reason"].split("(")[0].strip(), v["stopword_ratio"], ""))
        continue
    ok, topik, _ = check_political_domain(v["text"])
    hasil.append(("lolos" if ok else "di_luar_domain", "" if ok else f"topik={topik}", v["stopword_ratio"], topik))
d["gerbang"], d["alasan"], d["sw"], d["topik"] = zip(*hasil)
d["lolos"] = d.gerbang == "lolos"

print("=" * 90); print(f"n teks beku = {len(d)} (train+val+dev_test)"); print("=" * 90)
print("\nPORSI LOLOS GERBANG per label (0 = fakta, 1 = hoaks):")
print((d.groupby("label").lolos.mean() * 100).round(1).to_string())
sel = abs(d[d.label == 1].lolos.mean() - d[d.label == 0].lolos.mean()) * 100
print(f"\nSelisih hoaks vs fakta: {sel:.1f} poin" + ("  <-- ASIMETRI: gerbang mengubah komposisi kelas yang dinilai" if sel > 5 else ""))
print("\nPORSI LOLOS per sumber:"); print((d.groupby(["label", "source"]).lolos.mean() * 100).round(1).to_string())
print("\nALASAN PENOLAKAN (jumlah) per label:")
print(d[~d.lolos].groupby(["label", "gerbang", "alasan"]).size().to_string() or "(tidak ada)")

sw = d[d.sw.notna()].copy(); sw["sw"] = sw.sw.astype(float)
print("\nRASIO KATA FUNGSI (semua teks yang lolos validasi awal), persentil:")
print(sw.groupby("label").sw.quantile([0.01, 0.05, 0.5]).unstack().round(3).to_string())
print("\nBILA AMBANG MIN_STOPWORD_RATIO = x, porsi teks korpus yang akan DITOLAK sebagai 'bukan Indonesia':")
for x in (0.02, 0.04, 0.06, 0.08, 0.10):
    print(f"  x={x:.2f}: fakta {(sw[sw.label == 0].sw < x).mean()*100:4.1f}% | hoaks {(sw[sw.label == 1].sw < x).mean()*100:4.1f}%")
print("\nSUB-TOPIK teks yang lolos (porsi per label):")
print(pd.crosstab(d[d.lolos].topik, d[d.lolos].label, normalize="columns").round(3).to_string())
print("\nPilih MIN_STOPWORD_RATIO yang menolak ~0% teks korpus pada KEDUA label, lalu catat di protokol.")