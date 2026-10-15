"""
uji_ujung_ke_ujung.py — gambar -> OCR (PaddleOCR 3.x) -> gerbang kualitas -> praproses -> model (per seed).
Ini UJI FUNGSIONAL sistem, BUKAN evaluasi akurasi. Tidak menyentuh lockbox.
Jalankan dari root proyek:
    .\\.venv\\Scripts\\python.exe uji_ujung_ke_ujung.py data\\sample_probe.png [gambar2.png ...]
    .\\.venv\\Scripts\\python.exe uji_ujung_ke_ujung.py --seed 42 gambar.png      (satu model saja, lebih cepat)
Urutan impor penting (torch sebelum paddle; ocr_paddle3 mengurusnya).
"""
import os, sys, time
sys.path.insert(0, os.getcwd())
from src.utils import ocr_extractor as op            # harus pertama: set variabel lingkungan + muat torch sebelum paddle
import text_pipeline as tp
import inferensi_lokal as il

assert tp.PIPELINE_VERSION == "tp-1.6"
args = sys.argv[1:]
SEEDS = [42, 123, 999]
if "--seed" in args:
    i = args.index("--seed"); SEEDS = [int(args[i + 1])]; del args[i:i + 2]
if not args:
    sys.exit("Beri minimal satu jalur gambar.")

_MODELS = {}
def model(seed):
    if seed not in _MODELS:
        _MODELS[seed] = il.load_ckpt(f"ckpt_ce_{seed}.pt")
    return _MODELS[seed]

def praproses(text):                  # sama dengan jalur inferensi saat pelatihan: clean -> ensure_end -> cap 60 kata
    t = tp.clean(text)
    return tp.cap_sentences(tp.ensure_end(t), 60) if t else t

for path in args:
    print("=" * 78); print("Gambar:", path)
    t0 = time.time(); r = op.extract_text_from_image(path); t_ocr = time.time() - t0
    print(f"OCR   : berhasil={r['success']} | {t_ocr:.1f} dtk | baris={len(r['lines'])}")
    if not r["success"]:
        print("        ", r["message"]); continue
    f = r["fitur"]
    print(f"        kata={f['n_kata']} | conf rata2={f['conf_rata2']:.3f} | conf min={f['conf_min']:.3f} | pemenggalan hubung={f['n_pemenggalan_hubung']}")
    print("Teks OCR:", r["text"][:300])
    if not r["dapat_dinilai"]:
        print("KEPUTUSAN: TIDAK DAPAT DINILAI ->", "; ".join(r["alasan"])); continue
    x = praproses(r["text"])
    if not x:
        print("KEPUTUSAN: TIDAK DAPAT DINILAI -> teks kosong setelah pembersihan"); continue
    print("Setelah praproses:", x[:300])
    hasil = []
    for s in SEEDS:
        t1 = time.time(); p, pr = il.predict_texts(model(s), [x])
        hasil.append((s, int(p[0]), float(pr[0]), time.time() - t1))
        print(f"  seed {s:<4} -> {'HOAKS' if p[0] else 'FAKTA'} | P(hoaks)={pr[0]:.3f} | {hasil[-1][3]:.1f} dtk")
    if len({h[1] for h in hasil}) > 1:
        print("  CATATAN: seed TIDAK sepakat -> perlakukan sebagai tidak pasti.")
    print("  Peringatan: probabilitas model cenderung ekstrem (mendekati 0 atau 1) bahkan ketika salah; jangan dibaca sebagai keyakinan.")