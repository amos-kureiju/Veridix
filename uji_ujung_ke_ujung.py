r"""
uji_ujung_ke_ujung.py - gambar -> OCR (jalur aplikasi) -> gerbang OCR -> pembersihan -> model (3 seed).
UJI FUNGSIONAL, BUKAN evaluasi akurasi. Tidak menyentuh lockbox.
Memakai fungsi yang SAMA dengan endpoint /detect/image dan /detect/text.

    .\.venv\Scripts\python.exe uji_ujung_ke_ujung.py gambar1.png [gambar2.png ...]
    .\.venv\Scripts\python.exe uji_ujung_ke_ujung.py --lime gambar.png   (tambah LIME; lambat di CPU)

Keluaran: hasil_ujung_ke_ujung_<waktu>.json (semua gambar, termasuk yang ditolak).
"""
import os, sys, time, json
from datetime import datetime

sys.path.insert(0, os.getcwd())

# Urutan impor dipertahankan: modul OCR dimuat sebelum model (variabel lingkungan Paddle dan torch).
from src.utils.ocr_extractor import extract_text_from_image
from src.utils.text_preprocessor import clean_ocr_artifacts

MIN_KARAKTER_OCR = 50   # sama dengan endpoint /detect/image

args = sys.argv[1:]
LIME = "--lime" in args
args = [a for a in args if a != "--lime"]
if not args:
    sys.exit("Beri minimal satu jalur gambar.")


def angka(x, fmt="{:.3f}"):
    """Format angka bila valid; selain itu tanda tidak tersedia (bukan 0)."""
    return fmt.format(x) if isinstance(x, (int, float)) and x == x else "-"


_pred = None
def model():
    """Muat model hanya saat ada teks yang lolos OCR."""
    global _pred
    if _pred is None:
        from src.ml.inference import get_predictor
        t = time.perf_counter()
        _pred = get_predictor()
        print(f"     (model dimuat {time.perf_counter() - t:.1f} dtk)")
    return _pred


hasil = []
for path in args:
    print("=" * 80)
    print("Gambar:", path)
    rec = {"gambar": path, "tahap_akhir": None, "keputusan": None}
    hasil.append(rec)

    if not os.path.isfile(path):
        rec.update(tahap_akhir="berkas_tidak_ada", keputusan="DILEWATI")
        print("     berkas tidak ditemukan"); continue

    with open(path, "rb") as fh:
        isi = fh.read()

    t0 = time.perf_counter()
    try:
        r = extract_text_from_image(isi)            # kontrak aplikasi: bytes
    except Exception as e:
        rec.update(tahap_akhir="ocr_galat", keputusan="GAGAL", galat=f"{type(e).__name__}: {e}")
        print("     OCR melempar galat:", rec["galat"]); continue
    rec["waktu_ocr_dtk"] = round(time.perf_counter() - t0, 2)

    fitur = r.get("fitur") if isinstance(r.get("fitur"), dict) else {}
    baris = r.get("lines") or []
    print(f"OCR: berhasil={r.get('success')} | {rec['waktu_ocr_dtk']:.1f} dtk | baris={len(baris)}")
    if not r.get("success", False):
        rec.update(tahap_akhir="ocr_gagal", keputusan="DITOLAK", alasan=r.get("message"))
        print("     ", r.get("message")); continue

    print(f"     kata={fitur.get('n_kata', '-')} | conf rata2={angka(fitur.get('conf_rata2'))} "
          f"| conf min={angka(fitur.get('conf_min'))} | pemenggalan hubung={fitur.get('n_pemenggalan_hubung', '-')}")
    rec["fitur_ocr"] = fitur
    teks_mentah = (r.get("text") or "").strip()
    rec["teks_ocr_mentah"] = teks_mentah
    print("Teks OCR:", teks_mentah[:300])

    if not r.get("dapat_dinilai", True):
        alasan = r.get("alasan") or r.get("reason") or []
        alasan = alasan if isinstance(alasan, str) else "; ".join(map(str, alasan))
        rec.update(tahap_akhir="gerbang_ocr", keputusan="TIDAK DAPAT DINILAI", alasan=alasan)
        print("KEPUTUSAN: TIDAK DAPAT DINILAI (gerbang OCR) ->", alasan); continue

    if len(teks_mentah) < MIN_KARAKTER_OCR:
        rec.update(tahap_akhir="teks_terlalu_pendek", keputusan="DITOLAK",
                   alasan=f"kurang dari {MIN_KARAKTER_OCR} karakter ({len(teks_mentah)})")
        print("KEPUTUSAN: DITOLAK ->", rec["alasan"]); continue

    teks = clean_ocr_artifacts(teks_mentah)         # langkah yang sama dengan endpoint
    rec["teks_setelah_pembersihan"] = teks

    t1 = time.perf_counter()
    h = model().nilai(teks, explain=LIME, debug=True)
    rec["waktu_model_dtk"] = round(time.perf_counter() - t1, 2)
    print(f"KEPUTUSAN: {h.get('status')} | {h.get('label')} | suara hoaks={h.get('votes_hoax', '-')} "
          f"| model {rec['waktu_model_dtk']:.1f} dtk")

    rec.update(tahap_akhir="model", keputusan=h.get("label"), status=h.get("status"),
               votes_hoax=h.get("votes_hoax"), terpotong=h.get("terpotong"))
    if not h.get("success"):
        rec["alasan"] = h.get("reason")
        print("     alasan:", h.get("reason"))
    else:
        rec["teks_dinilai"] = h.get("teks_dinilai")
        rec["debug_prob_per_seed"] = h.get("debug", {}).get("prob_hoax_per_seed")
        print("     teks dinilai:", (h.get("teks_dinilai") or "")[:200])
        print("     (debug) P(hoaks) per seed:", rec["debug_prob_per_seed"], "<- jangan tampilkan ke pengguna")
        if LIME:
            rec["explanation"] = h.get("explanation")
            print("     LIME:", json.dumps(h.get("explanation"), ensure_ascii=False)[:400])

ringkas = {}
for rec in hasil:
    ringkas[rec["tahap_akhir"]] = ringkas.get(rec["tahap_akhir"], 0) + 1
print("=" * 80)
print("Ringkasan tahap akhir:", ringkas, f"| total gambar: {len(hasil)}")

nama = f"hasil_ujung_ke_ujung_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(nama, "w", encoding="utf-8") as fh:
    json.dump({"waktu": datetime.now().isoformat(timespec="seconds"), "lime": LIME,
               "min_karakter_ocr": MIN_KARAKTER_OCR, "ringkasan": ringkas, "gambar": hasil},
              fh, ensure_ascii=False, indent=2, default=str)
print("Tersimpan:", nama)