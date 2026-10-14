"""
evaluasi_ood_dan_ocr.py — Pengujian OOD & Ketahanan Derau OCR (Hemat Memori RAM).
Memuat checkpoint satu per satu (sekuensial) agar aman di RAM laptop.
"""
import os, sys, gc
import numpy as np, pandas as pd
import torch

sys.path.insert(0, os.getcwd())
import inferensi_lokal as il
import text_pipeline as tp

SEEDS = [42, 123, 999]
F = "data/processed_v2"
assert not any("lockbox" in p.lower() for p in (F,)), "LOCKBOX TIDAK BOLEH DIAKSES DI SINI!"

print("=" * 80)
print("1. EVALUASI SET DI LUAR DISTRIBUSI (OOD) LINTAS 3 SEED")
print("=" * 80)

nk = lambda s: tp.re.sub(r"[^a-z0-9]", "", str(s).lower())
tr = pd.read_csv(f"{F}/train.csv")
va = pd.read_csv(f"{F}/val.csv")
te = pd.read_csv(f"{F}/dev_test.csv")
seen = set(tr.title.map(nk)) | set(va.title.map(nk)) | set(te.title.map(nk))
prep_title = lambda t: tp.ensure_end(tp.norm_title(str(t)))

def load_eval(path, filter_klaim=False):
    d = pd.read_csv(path)
    d["title"] = d.title.fillna("").astype(str)
    if filter_klaim:
        tag = d.title.str.match(r"(?i)^\s*\[(?:hoaks|hoax|salah|disinformasi)\]")
        if tag.sum() > 0:
            d = d[tag]
    d["k"] = d.title.map(nk)
    d = d.drop_duplicates("k")
    d = d[~d.k.isin(seen)]
    return d.assign(text=d.title.map(prep_title)).reset_index(drop=True)

eb = load_eval(f"{F}/eval_benar.csv")
ek = load_eval(f"{F}/eval_kompas_cekfakta.csv", filter_klaim=True)
print(f"Data OOD siap diuji: eval_benar (n={len(eb)}), eval_kompas (n={len(ek)})\n")

# Evaluasi OOD per seed secara sekuensial (hemat RAM)
hasil_eb = []
hasil_ek = []

for s in SEEDS:
    print(f"--> Memproses Checkpoint Seed {s}...")
    m = il.load_ckpt(f"ckpt_ce_{s}.pt")
    
    p_eb, _ = il.predict_texts(m, eb.text.values)
    p_ek, _ = il.predict_texts(m, ek.text.values)
    
    hasil_eb.append(np.mean(p_eb == 1) * 100)
    hasil_ek.append(np.mean(p_ek == 1) * 100)
    
    del m
    gc.collect()

print("\n--- HASIL EVALUASI OOD ---")
print("eval_benar (Klarifikasi Fakta Mafindo):")
print(f"  Per Seed (42, 123, 999) : {[round(x, 2) for x in hasil_eb]}%")
print(f"  Rerata ± Std             : {np.mean(hasil_eb):.2f}% ± {np.std(hasil_eb):.2f}% diprediksi HOAKS")

print("\neval_kompas (Klaim Hoaks non-Mafindo):")
print(f"  Per Seed (42, 123, 999) : {[round(x, 2) for x in hasil_ek]}%")
print(f"  Rerata ± Std             : {np.mean(hasil_ek):.2f}% ± {np.std(hasil_ek):.2f}% diprediksi HOAKS")

print("\n" + "=" * 80)
print("2. UJI KETAHANAN TEKS OCR NYATA (SIMULASI DERAU PADDLEOCR)")
print("=" * 80)

sampel_ocr = [
    {
        "label_asli": 1,
        "kategori": "Hoaks Poster Medsos (Derau Line-Break & Spasi)",
        "teks_ocr": "Beredar tangkapan layar :\nKPU RI me- netapkan bahwa surat suara no- mor 02\nsudah ter- coblos sebanyak 5 juta lembar di gudang logistik ."
    },
    {
        "label_asli": 1,
        "kategori": "Hoaks Pesan Berantai (Derau Typo Karakter)",
        "teks_ocr": "PENGUMUMAN RESM1 : Bank Indonesia mem- bagi- kan bantuan dana tunai 15 jt rupiah untk masyarakat ber- KTP Jawa Barat lewat tautan ini ."
    },
    {
        "label_asli": 0,
        "kategori": "Berita Fakta Formal (Kutipan Lede Berita)",
        "teks_ocr": "Presiden Joko Widodo menegaskan bahwa pemerintah tetap memprioritaskan penyaluran bantuan sosial tepat sasaran menjelang akhir tahun anggaran ."
    },
    {
        "label_asli": 0,
        "kategori": "Berita Fakta Kebijakan (Derau OCR)",
        "teks_ocr": "Kementerian Keuangan me- mastikan anggaran penanganan inflasi daerah telah disalurkan ke seluruh pemerintah daerah secara transparan ."
    }
]

teks_bersih_list = [tp.cap_sentences(tp.ensure_end(tp.norm_title(tp.clean(s["teks_ocr"]))), max_words=60) for s in sampel_ocr]

semua_pred_ocr = []
for s in SEEDS:
    m = il.load_ckpt(f"ckpt_ce_{s}.pt")
    _, pr = il.predict_texts(m, teks_bersih_list)
    semua_pred_ocr.append(pr)
    del m
    gc.collect()

avg_probs = np.mean(semua_pred_ocr, axis=0)

for s, t_bersih, p_hoax in zip(sampel_ocr, teks_bersih_list, avg_probs):
    pred_final = "HOAKS" if p_hoax >= 0.5 else "FAKTA"
    label_text = "HOAKS" if s["label_asli"] == 1 else "FAKTA"
    status_cocok = "BENAR" if pred_final == label_text else "SALAH"
    
    print(f"\n[{status_cocok}] {s['kategori']}")
    print(f"  Teks Bersih   : {t_bersih}")
    print(f"  Probabilitas  : Fakta = {(1-p_hoax)*100:.1f}% | Hoaks = {p_hoax*100:.1f}%")
    print(f"  Prediksi Akhir: {pred_final} (Label Sebenarnya: {label_text})")

print("\n" + "=" * 80)
print("EVALUASI OOD & KETAHANAN OCR SELESAI!")
print("=" * 80)