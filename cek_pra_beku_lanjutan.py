import os, re
import pandas as pd

R = "data/raw" if os.path.exists("data/raw") else "../data/raw"
O = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"
assert os.path.exists(R), f"Folder {R} tidak ditemukan!"
assert os.path.exists(O), f"Folder {O} tidak ditemukan!"

# ── 1. SEMUA TAG DI DATA MENTAH HOAKS ─────────────────────────────────────────
print("=" * 80)
print("1. 30 TAG TERBANYAK DI DATA MENTAH HOAKS:")
print("=" * 80)
for f_prefix, col in [("dataset_turnbackhoax_10_cleaned", "Title"), ("hoax_dataset_with_text", "judul")]:
    fn = [x for x in os.listdir(R) if x.startswith(f_prefix)][0]
    p_file = os.path.join(R, fn)
    d_raw = pd.read_excel(p_file) if p_file.endswith((".xlsx", ".xls")) else pd.read_csv(p_file)
    t = d_raw[col].astype(str)
    tag = t.str.extract(r"^\s*[\[\(\{]([^\]\)\}]{1,25})[\]\)\}]")[0].str.upper().str.strip()
    print(f"\n--- Sumber: {f_prefix} ---")
    print(tag.value_counts().head(30).to_dict())

# ── 2. PREFIKS DESKRIPTIF PADA JUDUL PER LABEL & SUMBER ──────────────────────
print("\n" + "=" * 80)
print("2. PREFIKS DESKRIPTIF PADA JUDUL (TANGKAPAN LAYAR, ARTIKEL, INFOGRAFIK, DLL):")
print("=" * 80)
d = pd.read_csv(f"{O}/dataset_v2_full.csv")
PFX = re.compile(
    r"^\W*(?:(?:gambar|foto|video)?\s*(?:tangkapan|tangkap)\s+layar|sampul|artikel|berita populer|infografik)\b",
    re.I
)
print(d.assign(p=d.title.astype(str).map(lambda s: bool(PFX.match(s)))).groupby(["label", "source"]).p.agg(["sum", "mean"]))

# ── 3. POSISI NAMA MEDIA PADA TEKS FAKTA ─────────────────────────────────────
print("\n" + "=" * 80)
print("3. POSISI & KONTEKS NAMA MEDIA PADA TEKS FAKTA (CNN Indonesia / KOMPAS.com):")
print("=" * 80)
rx = re.compile(r"CNN Indonesia|KOMPAS\.com", re.I)
count_match = 0
for idx, r in d[d.label == 0].iterrows():
    m = rx.search(str(r.text))
    if m:
        count_match += 1
        print(f"[{count_match}] Posisi {m.start():>3} | ...{r.text[max(0, m.start() - 30):m.end() + 25]!r}")
if count_match == 0:
    print("Tidak ditemukan kemunculan nama media pada teks fakta.")