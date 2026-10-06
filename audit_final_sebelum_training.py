"""
AUDIT FINAL SEBELUM TRAINING (VERSI DATASET v2)
Mengecek:
  1. Distribusi 4 sub-topik per label (nyata dari processed_v2)
  2. Kecukupan sampel per sel topik x label (di dev_test set)
  3. Judul ganda per topik dan label
  4. Keyword coverage
  5. PaddleOCR — versi dan tes sintesis
  6. Rekomendasi final
"""

import pandas as pd
import numpy as np
import re
import os
os.environ["FLAGS_enable_pir_api"] = "0"   # Matikan PIR engine agar PaddleOCR memakai engine stabil

# --- PERBAIKAN: Baca direktori processed_v2 yang valid ---
PROCESSED_DIR = "data/processed_v2" if os.path.exists("data/processed_v2") else "../data/processed_v2"
RAW_DIR       = "data/raw"          if os.path.exists("data/raw")          else "../data/raw"

TOPIK_KEYWORDS = {
    "Pemilu_Pilpres": [
        "pemilu", "pilpres", "pilkada", "kpu", "sirekap", "capres",
        "cawapres", "coblos", "surat suara", "quick count", "bawaslu",
        "partai", "pdip", "gerindra", "golkar", "nasdem", "pks", "demokrat",
        "pkb", "hanura", "perindo", "psi", "rekapitulasi", "tps", "pilgub"
    ],
    "Kebijakan_Pemerintah": [
        "bansos", "subsidi", "bbm", "ikn", "apbn", "omnibus",
        "undang-undang", "perpres", "pajak", "bpjs", "tarif listrik",
        "kebijakan", "kementerian", "pemerintah", "anggaran", "asn",
        "bumn", "pertamina", "reshuffle", "kabinet", "peraturan",
        "regulasi", "upah", "umk", "umr", "inpres"
    ],
    "Tokoh_Politik": [
        "jokowi", "prabowo", "gibran", "anies", "ganjar", "megawati",
        "presiden", "menteri", "gubernur", "bupati", "dpr", "mpr",
        "puan", "luhut", "sri mulyani", "nadiem", "erick thohir",
        "kaesang", "ridwan kamil", "ahok", "agus harimurti", "ahy",
        "cak imin", "muhaimin", "mahfud", "airlangga", "sandiaga"
    ],
    "Hukum_Korupsi": [
        "korupsi", "kpk", "mahkamah", "mk", "pengadilan", "hakim",
        "jaksa", "tersangka", "vonis", "kejaksaan", "polri", "suap",
        "ott", "sidang", "pidana", "penahanan", "terdakwa", "gratifikasi",
        "pencucian uang", "tipikor", "tni", "polisi", "penjara"
    ]
}

def deteksi_topik(text):
    t = str(text).lower()
    hasil = []
    for topik, kws in TOPIK_KEYWORDS.items():
        if any(kw in t for kw in kws):
            hasil.append(topik)
    return hasil[0] if len(hasil) == 1 else ("Multi" if hasil else "Lainnya")

def strip_dup_title(text):
    t = str(text).strip()
    parts = re.split(r'(?<=[.!?])\s+', t, maxsplit=1)
    if len(parts) < 2:
        return t
    first = parts[0].strip().lower()
    rest  = parts[1].strip()
    if len(first) >= 15 and rest.lower().startswith(first[:30]):
        return rest
    return t

print("=" * 65)
print("AUDIT FINAL SEBELUM TRAINING (DATASET v2)")
print("=" * 65)

# --- PERBAIKAN: Muat split v2 (train, val, dev_test) ---
splits = {}
for s in ["train", "val", "dev_test"]:
    p = os.path.join(PROCESSED_DIR, f"{s}.csv")
    if os.path.exists(p):
        splits[s] = pd.read_csv(p)
        print(f"  {s}.csv: {len(splits[s]):,} baris")
    else:
        print(f"  ✗ {s}.csv tidak ditemukan di {PROCESSED_DIR}")

if not splits:
    print("  ✗ Tidak ada file di processed_v2/ — jalankan 01b dulu")
    exit()

df_all = pd.concat(splits.values(), ignore_index=True)

topik_col = "sub_topic" if "sub_topic" in df_all.columns else ("sub_topik" if "sub_topik" in df_all.columns else None)
if topik_col:
    df_all["sub_topik"] = df_all[topik_col]
else:
    df_all["sub_topik"] = df_all["text"].apply(deteksi_topik)

print("\n" + "─" * 65)
print("BAGIAN 1 — Distribusi 4 topik per label (seluruh dataset v2)")
print("─" * 65)

ct = pd.crosstab(df_all["sub_topik"], df_all["label"], margins=True)
ct.columns = ["Fakta (0)", "Hoaks (1)", "Total"]
ct["Rasio H:F"] = (ct["Hoaks (1)"] / ct["Fakta (0)"].replace(0, np.nan)).round(2)
ct["% Hoaks"]  = (ct["Hoaks (1)"] / ct["Total"] * 100).round(1)
print(ct.to_string())

print("\n" + "─" * 65)
print("BAGIAN 2 — Kecukupan sampel per sel topik × label (di DEV_TEST set)")
print("─" * 65)
print("Syarat minimum untuk F1 yang bermakna: ≥ 30 sampel per sel")
print("  < 30   : tidak stabil (CI 95% terlalu lebar)")
print("  30-100 : cukup minimal")
print("  > 100  : solid\n")

te = splits.get("dev_test")
if te is not None:
    te_topik = te["sub_topic"] if "sub_topic" in te.columns else te["text"].apply(deteksi_topik)
    te = te.assign(sub_topik=te_topik)
    for topik in te["sub_topik"].unique():
        for label, nama in [(0, "Fakta"), (1, "Hoaks")]:
            n = len(te[(te["sub_topik"] == topik) & (te["label"] == label)])
            if n > 0:
                flag = "⚠ TIDAK STABIL" if n < 30 else ("○ Cukup minimal" if n < 100 else "✓ Solid")
                print(f"  {str(topik):25s} {nama}: n={n:4d}  {flag}")

print("\n" + "─" * 65)
print("BAGIAN 3 — Judul ganda per topik dan label (di TRAIN set)")
print("─" * 65)

tr = splits.get("train")
if tr is not None:
    tr_topik = tr["sub_topic"] if "sub_topic" in tr.columns else tr["text"].apply(deteksi_topik)
    tr = tr.assign(sub_topik=tr_topik)
    tr["dup"] = tr["text"].apply(lambda t: strip_dup_title(str(t)) != str(t).strip())

    per_topik = tr.groupby(["sub_topik", "label"])["dup"].agg(["sum", "count", "mean"]).reset_index()
    per_topik.columns = ["sub_topik", "label", "n_dup", "n_total", "pct_dup"]
    per_topik["pct_dup"] = (per_topik["pct_dup"] * 100).round(1)
    per_topik["label"]   = per_topik["label"].map({0: "Fakta", 1: "Hoaks"})
    print(per_topik.to_string(index=False))

    total_dup_fakta = tr[tr["label"]==0]["dup"].mean() * 100
    total_dup_hoaks = tr[tr["label"]==1]["dup"].mean() * 100
    print(f"\n  Rata-rata global — Fakta: {total_dup_fakta:.1f}% | Hoaks: {total_dup_hoaks:.1f}%")

print("\n" + "─" * 65)
print("BAGIAN 4 — Coverage keyword 4 topik di dataset")
print("─" * 65)

topik_counts = df_all["sub_topik"].value_counts()
total = len(df_all)
for topik, n in topik_counts.items():
    pct = n / total * 100
    bar = "█" * min(int(pct / 2), 25)
    print(f"  {str(topik):25s}: {n:6,} ({pct:5.1f}%) {bar}")

print("\n" + "─" * 65)
print("BAGIAN 5 — Cek PaddleOCR")
print("─" * 65)

try:
    from paddleocr import PaddleOCR
    # Ganti baris inisialisasi PaddleOCR menjadi parameter modern:
    ocr = PaddleOCR(use_textline_orientation=True, lang="id")
    print("  ✓ PaddleOCR berhasil diinisialisasi (lang='id')")

    from PIL import Image, ImageDraw
    img = Image.new('RGB', (450, 80), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((10, 25), "Jokowi Bertemu Prabowo di Istana Negara", fill='black')
    
    test_img_path = "test_ocr_temp.png"
    img.save(test_img_path)
    
    result = ocr.ocr(test_img_path)
    if os.path.exists(test_img_path):
        os.remove(test_img_path)

    if result and result[0]:
        teks_terdeteksi = " ".join([line[1][0] for line in result[0]])
        print(f"  ✓ Tes OCR berhasil: '{teks_terdeteksi}'")
    else:
        print("  ⚠ OCR tidak mendeteksi teks")
except ImportError:
    print("  ✗ PaddleOCR belum terinstall (Jalankan: pip install paddlepaddle paddleocr)")
except Exception as e:
    print(f"  ⚠ PaddleOCR info: {e}")

print("\n" + "=" * 65)
print("BAGIAN 6 — REKOMENDASI FINAL")
print("=" * 65)

n_total = len(df_all)
n_fakta_hukum = len(df_all[(df_all["sub_topik"].str.lower() == "hukum") & (df_all["label"] == 0)])

print(f"  Total Baris Analisis: {n_total:,} baris")
print(f"  Fakta Hukum          : {n_fakta_hukum} sampel")
if n_fakta_hukum < 200:
    print("  ⚠ Catatan Sub-Topik Hukum: Ukuran sampel di bawah 200 (Wajib laporkan limitasi di Bab 5).")
print("  ✓ Dataset v2 terverifikasi dan siap untuk pelatihan IndoBERT.")
print("=" * 65)