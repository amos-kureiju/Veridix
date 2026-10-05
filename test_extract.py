import os
import re
import pandas as pd

raw_dir = "data/raw" if os.path.exists("data/raw") else "../data/raw"
f_hoax = [f for f in os.listdir(raw_dir) if f.startswith("hoax_dataset_with_text")][0]
df_h = pd.read_csv(os.path.join(raw_dir, f_hoax), nrows=50)

LEADING_TAG = re.compile(r"^\s*(?:[\[\(\{][^\]\)\}]{1,25}[\]\)\}]\s*:?\s*)+")

# Menangkap kutipan klaim setelah kata narasi / klaim / informasi
QUOTE_EXTRACT = re.compile(
    r'(?:berisi\s+(?:informasi|narasi|klaim)|narasi|klaim)\s*[:\s]*["\'\u201c\u2018]([^"\'\u201d\u2019]{15,600})["\'\u201d\u2019]',
    re.I
)

def extract_hoax_claim(judul, teks):
    judul_clean = LEADING_TAG.sub("", str(judul)).strip()
    m = QUOTE_EXTRACT.search(str(teks))
    if m:
        extracted = m.group(1).strip()
        if len(extracted.split()) >= 6:
            return extracted, "KUTIPAN_TEKS"
    return judul_clean, "FALLBACK_JUDUL"

print("=" * 85)
print("HASIL VALIDASI 50 SAMPEL: EKSTRAKSI HIBRIDA KLAIM HOAKS")
print("=" * 85)

stats = {"KUTIPAN_TEKS": 0, "FALLBACK_JUDUL": 0}
for i, r in df_h.iterrows():
    hasil, sumber = extract_hoax_claim(r.get("judul", ""), r.get("teks", ""))
    stats[sumber] += 1
    if i < 10:  # Tampilkan 10 sampel pertama untuk inspeksi mata
        print(f"\n[Sampel #{i+1}] ({sumber}) - {len(hasil.split())} kata:")
        print(f"  >>> {hasil}")

print("\n" + "=" * 85)
print(f"Statistik 50 Sampel: {stats}")
print("=" * 85)