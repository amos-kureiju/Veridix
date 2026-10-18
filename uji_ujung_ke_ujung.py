r"""
uji_ujung_ke_ujung.py — gambar -> OCR (PaddleOCR 3.x) -> gerbang OCR -> jalur aplikasi (validasi, domain, praproses, 3 seed).
UJI FUNGSIONAL, BUKAN evaluasi akurasi. Tidak menyentuh lockbox. Memakai jalur praproses/inferensi yang SAMA dengan aplikasi.
    .\.venv\Scripts\python.exe uji_ujung_ke_ujung.py gambar1.png [gambar2.png ...]
    .\.venv\Scripts\python.exe uji_ujung_ke_ujung.py --lime gambar.png        (tambahkan penjelasan LIME; lambat di CPU)
"""
import os, sys, time, json
sys.path.insert(0, os.getcwd())
import ocr_paddle3 as op            # HARUS pertama: variabel lingkungan + torch dimuat sebelum paddle
from src.ml.inference import get_predictor

args = sys.argv[1:]
LIME = "--lime" in args
args = [a for a in args if a != "--lime"]
if not args:
    sys.exit("Beri minimal satu jalur gambar.")

pred = get_predictor()
for path in args:
    print("=" * 80); print("Gambar:", path)
    t0 = time.time(); r = op.extract_text_from_image(path); t_ocr = time.time() - t0
    print(f"OCR: berhasil={r['success']} | {t_ocr:.1f} dtk | baris={len(r['lines'])}")
    if not r["success"]:
        print("    ", r["message"]); continue
    f = r["fitur"]
    print(f"     kata={f['n_kata']} | conf rata2={f['conf_rata2']:.3f} | conf min={f['conf_min']:.3f} | pemenggalan hubung={f['n_pemenggalan_hubung']}")
    print("Teks OCR:", r["text"][:300])
    if not r["dapat_dinilai"]:
        print("KEPUTUSAN: TIDAK DAPAT DINILAI (gerbang OCR) ->", "; ".join(r["alasan"])); continue
    t1 = time.time(); h = pred.nilai(r["text"], explain=LIME, debug=True); t_model = time.time() - t1
    print(f"KEPUTUSAN: {h['status']} | {h['label']} | suara hoaks={h.get('votes_hoax', '-')} | model {t_model:.1f} dtk")
    if not h["success"]:
        print("     alasan:", h["reason"])
    else:
        print("     teks dinilai:", h["teks_dinilai"][:200])
        print("     (debug) P(hoaks) per seed:", h["debug"]["prob_hoax_per_seed"], "<- jangan tampilkan ke pengguna")
        if LIME:
            print("     LIME:", json.dumps(h["explanation"], ensure_ascii=False)[:400])