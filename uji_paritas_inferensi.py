r"""
uji_paritas_inferensi.py — jalur APLIKASI (BackendIndoBERT: satu model dasar + penukaran bobot per seed) harus memberi
prediksi IDENTIK dengan prediksi Colab per seed (prediksi_val_dev.csv) pada val dan dev_test. Tidak menyentuh lockbox.
Jalankan dari root proyek:
    .\.venv\Scripts\python.exe uji_paritas_inferensi.py            (472 teks x 3 seed; beberapa menit di CPU)
    .\.venv\Scripts\python.exe uji_paritas_inferensi.py --n 100    (100 teks pertama tiap split; lebih cepat)
Bila ada selisih, jangan dijalankan di aplikasi sebelum penyebabnya diketahui.
"""
import os, sys, time
import numpy as np, pandas as pd

sys.path.insert(0, os.getcwd())
from src.ml.inference import BackendIndoBERT, SEEDS  # noqa: E402

F = "data/processed_v2"
N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else None
saved = pd.read_csv("prediksi_val_dev.csv")

t0 = time.time()
be = BackendIndoBERT()            # semua pemeriksaan integritas (hash, kunci, revisi) berjalan di sini
print("Audit integritas:", {k: (v[:12] + "...") if isinstance(v, str) else v for k, v in be.audit.items()})
print(f"Model dimuat dalam {time.time() - t0:.1f} dtk | perangkat {be.device}")

semua = True
for sp, nama in (("val", "val"), ("dev_test", "dev_test")):
    d = pd.read_csv(f"{F}/{sp}.csv")
    if N:
        d = d.head(N)
    d["text"] = d.text.fillna("").astype(str)
    t1 = time.time()
    P = np.vstack([be.seed_probs_each(d.text.tolist()[i:i + 128]) for i in range(0, len(d), 128)])
    ref = saved[saved.split == sp].set_index("id")
    for j, s in enumerate(SEEDS):
        pred = (P[:, j] >= 0.5).astype(int)
        r = ref.loc[d.id, f"pred_ce_{s}"].to_numpy()
        beda = int((pred != r).sum())
        semua &= beda == 0
        print(f"{nama:<9} seed {s:<4} selisih dengan Colab: {beda}/{len(d)} | akurasi {np.mean(pred == d.label.values)*100:.2f}%")
    print(f"  ({time.time() - t1:.0f} dtk untuk {len(d)} teks x {len(SEEDS)} seed)")
print("\nSTATUS:", "PARITAS PENUH (0 selisih)" if semua else "ADA SELISIH: selidiki sebelum dipakai")
sys.exit(0 if semua else 1)