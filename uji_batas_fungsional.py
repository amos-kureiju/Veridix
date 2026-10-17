"""
uji_batas_fungsional.py — perilaku sistem pada masukan ekstrem. Ekspektasi ditetapkan DI BERKAS INI sebelum dijalankan.
    python uji_batas_fungsional.py --stub     alur tanpa torch (backend tiruan; menguji validasi, domain, praproses, keluaran)
    python uji_batas_fungsional.py            sistem sebenarnya (memuat model; semua pemeriksaan integritas aktif)
    python uji_batas_fungsional.py --lime     tambahan: satu kasus dengan penjelasan LIME (lambat di CPU)
Hasil: hasil_uji_batas.csv. Keluar dengan kode 1 bila ada kasus gagal.
Karakter Unicode dibangun dengan kode titik agar aman dari masalah penyandian berkas.
"""
import os
import sys
import time
import json

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
from src.ml.inference import Penilai  # noqa: E402

STUB = "--stub" in sys.argv
LIME = "--lime" in sys.argv


class _StubBackend:
    seeds = [42, 123, 999]

    def seed_probs_each(self, texts):
        return np.array([[0.95, 0.90, 0.99] if "viral" in t.lower() else [0.05, 0.10, 0.02] for t in texts])


if STUB:
    penilai = Penilai(_StubBackend())
else:
    from src.ml.inference import get_predictor
    penilai = get_predictor()

SIRILIK = {ord("a"): "\u0430", ord("o"): "\u043e", ord("e"): "\u0435", ord("c"): "\u0441", ord("p"): "\u0440"}
DASAR = "Beredar informasi bahwa KPU merencanakan pemilu dipercepat tanpa persetujuan DPR RI dan pemerintah."
DINILAI = {"dinilai", "ambigu"}

KASUS = [
    ("TC01", "Teks kosong", "", {"ditolak"}),
    ("TC02", "Hanya simbol dan spasi", "   ... ??? !!! @@@ ###   ", {"ditolak"}),
    ("TC03", "Satu kata", "Presiden", {"ditolak"}),
    ("TC04", "Angka saja", "12345 67890 2024 2026 9999", {"ditolak"}),
    ("TC05", "Pendek (< 10 kata)", "Jokowi resmikan jalan tol baru di pulau Jawa.", {"ditolak"}),
    ("TC06", "Non-politik (resep)", "Cara memasak rendang daging sapi empuk khas Padang dengan santan kelapa kental dan rempah pilihan keluarga.", {"di_luar_domain"}),
    ("TC07", "Bahasa Inggris (>= 10 kata)", "The election commission announced the official results of the presidential race today in capital city.", {"ditolak"}),
    ("TC08", "'pan' huruf kecil (wajan)", "Gunakan pan anti lengket untuk menggoreng telur dadar agar matang merata tanpa minyak berlebih.", {"di_luar_domain"}),
    ("TC09", "'PAN' huruf besar (partai)", "Partai PAN menggelar rapat konsolidasi pemilu bersama jajaran pengurus daerah untuk strategi pilpres.", DINILAI),
    ("TC10", "Homoglif Sirilik", DASAR.translate(SIRILIK), DINILAI),
    ("TC11", "Zero-width tersembunyi", "KPU\u200b RI\u200c menegaskan\u200d bahwa surat suara pemilu telah didistribusikan ke seluruh daerah secara transparan.", DINILAI),
    ("TC12", "Teks sangat panjang", "Pemerintah menyatakan bahwa anggaran pemilu sudah disetujui oleh DPR untuk seluruh daerah. " * 40, DINILAI),
    ("TC13", "URL dan emoji", "Beredar pesan berantai bahwa KPU memindahkan surat suara pemilu ke gudang lain \U0001F631\U0001F525 baca selengkapnya di https://contoh.example/abc agar seluruh warga tahu", DINILAI),
    ("TC14", "Teks berderau ala OCR", "Beredar tangkapan layar : KPU RI me- netapkan bahwa surat suara no- mor 02 sudah ter- coblos sebanyak 5 juta lembar di gudang logistik.", DINILAI),
    ("TC15", "Masukan bukan string (angka)", 12345, {"ditolak"}),
    ("TC16", "Masukan None", None, {"ditolak"}),
    ("TC17", "Politik normal (12 kata)", "Presiden Jokowi menegaskan bahwa pemerintah tetap memprioritaskan bansos tepat sasaran tahun ini.", DINILAI),
]

EXTRA = {   # pemeriksaan tambahan per kasus
    "TC10": lambda r: r.get("input_flags", {}).get("had_homoglyph") is True and "\u0430" not in r.get("teks_dinilai", ""),
    "TC11": lambda r: r.get("input_flags", {}).get("had_invisible") is True and "\u200b" not in r.get("teks_dinilai", ""),
    "TC12": lambda r: r.get("terpotong") is True and len(r.get("teks_dinilai", "").split()) <= 60,
    "TC13": lambda r: "http" not in r.get("teks_dinilai", ""),
}

print("=" * 88)
print(f"UJI BATAS FUNGSIONAL | mode: {'TIRUAN (stub)' if STUB else 'SISTEM SEBENARNYA'}")
print("=" * 88)
rows, semua = [], True
for kid, nama, teks, boleh in KASUS:
    t0 = time.time()
    try:
        r = penilai.nilai(teks, explain=False)
        galat = ""
    except Exception as e:                        # sistem tidak boleh crash pada masukan apa pun
        r, galat = {"status": "CRASH", "label": "-"}, f"{type(e).__name__}: {e}"
    ok = r["status"] in boleh and (EXTRA[kid](r) if kid in EXTRA and not galat else True)
    semua &= ok
    kebocoran = any(k in json.dumps(r, ensure_ascii=False) for k in ("prob_hoax", "probabilitas")) and "debug" not in r
    print(f"[{'LULUS' if ok else 'GAGAL'}] {kid} {nama:<30} -> {r['status']:<15} {r['label'][:34]:<34} {r.get('votes_hoax', '')}"
          + (f" | {r.get('reason', '')[:60]}" if not r.get("success", False) else "") + (f" | {galat}" if galat else ""))
    rows.append(dict(id=kid, nama=nama, status=r["status"], label=r["label"], lulus=ok, galat=galat,
                     alasan=r.get("reason", ""), votes_hoax=r.get("votes_hoax", ""), detik=round(time.time() - t0, 3)))

if LIME and not STUB:
    t0 = time.time()
    r = penilai.nilai(DASAR, explain=True)
    print("\nLIME:", r.get("explanation", {}).get("explanation_available"), r.get("explanation", {}).get("error", ""),
          f"| {time.time() - t0:.1f} dtk |", [(t["word"], t["influence"]) for t in r.get("explanation", {}).get("tokens", [])[:5]])

pd.DataFrame(rows).to_csv("hasil_uji_batas.csv", index=False)
print("=" * 88)
print("Tersimpan: hasil_uji_batas.csv |", "SEMUA KASUS LULUS" if semua else "ADA KASUS GAGAL")
if not STUB:
    print("Latensi per kasus (detik, tanpa LIME):", [r["detik"] for r in rows])
sys.exit(0 if semua else 1)