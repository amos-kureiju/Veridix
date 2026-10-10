"""
audit_pra_beku.py
Audit diagnostik pra-pembekuan sesuai permintaan reviewer:
  (a) Irisan judul turnbackhoax vs hoax_archive
  (b) Judul sama yang bocor melintasi split (train vs dev vs lockbox)
  (c) Rincian residu penanda sumber per pola
  (d) Probe 8 kata TANPA kata framing media
  (+) 20 sampel KLARIFIKASI dan BELUM TERBUKTI dari label 1
  (+) Rincian pohon keputusan C4 per fitur riil dari build trial
"""
import os, re
import pandas as pd, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
import text_pipeline as tp

RAW_DIR = "data/raw" if os.path.exists("data/raw") else "../data/raw"
TRIAL_DIR = "data/processed_v2_trial" if os.path.exists("data/processed_v2_trial") else "../data/processed_v2_trial"

print("=" * 80)
print("AUDIT DIAGNOSTIK PRA-PEMBEKUAN (DATA TRIAL)")
print("=" * 80)

# ── 1. CEK (a): IRISAN TURNBACKHOAX VS HOAX_ARCHIVE ─────────────────────────
SOURCES = [
    dict(name="turnbackhoax.id", label=1, file="dataset_turnbackhoax_10_cleaned", title=["Title"]),
    dict(name="hoax_archive_15k", label=1, file="hoax_dataset_with_text", title=["judul"]),
]

def pick(row, names):
    for n in names:
        if n in row.index and pd.notna(row[n]) and str(row[n]).strip() not in ("", "nan", "None"):
            return str(row[n]).strip()
    return ""

nk = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"^\s*(?:\[[^\]]{1,25}\]\s*)+", "", str(s).lower()))

dfs_raw = {}
for s in SOURCES:
    files = sorted(f for f in os.listdir(RAW_DIR) if f.startswith(s["file"]))
    if files:
        p = os.path.join(RAW_DIR, files[0])
        d = pd.read_excel(p) if p.endswith((".xlsx", ".xls")) else pd.read_csv(p)
        dfs_raw[s["name"]] = pd.Series([pick(r, s["title"]) for _, r in d.iterrows()]).dropna()

tb = set(dfs_raw["turnbackhoax.id"].map(nk))
ha = set(dfs_raw["hoax_archive_15k"].map(nk))
print("\n[a] IRISAN JUDUL MENTAH (DUPLIKASI ARSIP MAFINDO):")
print(f"  • Irisan Judul Sama  : {len(tb & ha):,} judul")
print(f"  • Total TurnBackHoax : {len(tb):,} judul unik")
print(f"  • Total Hoax Archive : {len(ha):,} judul unik")
print(f"  • Rasio Duplikasi    : {len(tb & ha) / max(len(tb), 1) * 100:.1f}% judul TurnBackHoax ada di Hoax Archive!")

# ── 2. CEK (b): JUDUL SAMA LINTAS SPLIT DI TRIAL ────────────────────────────
p_full = os.path.join(TRIAL_DIR, "dataset_v2_full.csv")
if os.path.exists(p_full):
    d = pd.read_csv(p_full)
    d["k"] = d.title.map(nk)
    cross_split_titles = int((d.groupby("k").split.nunique() > 1).sum())
    print("\n[b] KEBOCORAN JUDUL SAMA LINTAS SPLIT (TRAIN vs VAL vs DEV):")
    print(f"  • Jumlah judul sama di lebih dari 1 split: {cross_split_titles} judul")

# ── 3. CEK (c): RINCIAN RESIDU PENANDA SUMBER ────────────────────────────────
if os.path.exists(p_full):
    pats = {
        "TEMPO.CO": r"TEMPO\.CO",
        "CNN Indonesia": r"CNN Indonesia",
        "KOMPAS.com": r"KOMPAS\.com",
        "ADVERTISEMENT": r"ADVERTISEMENT",
        "lihat juga": r"[Ll]ihat [Jj]uga",
        "baca juga": r"[Bb]aca [Jj]uga",
        "===": r"={3,}"
    }
    res_list = []
    for k_pat, p_pat in pats.items():
        m = d.text.astype(str).str.contains(p_pat)
        res_list.append({
            "pola": k_pat,
            "fakta_muncul": int(m[d.label == 0].sum()),
            "hoaks_muncul": int(m[d.label == 1].sum())
        })
    print("\n[c] RINCIAN RESIDU PENANDA SUMBER PER POLA (DATA TRIAL):")
    print(pd.DataFrame(res_list).to_string(index=False))

# ── 4. CEK (d): PROBE 8 KATA TANPA KATA FRAMING ──────────────────────────────
p_tr = os.path.join(TRIAL_DIR, "train.csv")
p_te = os.path.join(TRIAL_DIR, "dev_test.csv")
if os.path.exists(p_tr) and os.path.exists(p_te):
    tr_df = pd.read_csv(p_tr)
    te_df = pd.read_csv(p_te)
    
    nf8 = lambda df_in: df_in.text.map(lambda t: tp.FRAMING_PREFIX.sub("", str(t))).str.split().str[:8].str.join(" ")
    v2 = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    m2 = LogisticRegression(max_iter=2000, class_weight="balanced").fit(v2.fit_transform(nf8(tr_df)), tr_df.label)
    acc_nf8 = accuracy_score(te_df.label, m2.predict(v2.transform(nf8(te_df)))) * 100
    print("\n[d] PROBE 8 KATA TANPA KATA FRAMING (AKURASI DEV_TEST):")
    print(f"  • Akurasi 8 kata murni (tanpa Video/Foto/dll) : {acc_nf8:.2f}%")

    # ── RINCIAN FITUR C4 RIIL DARI RUN TRIAL ────────────────────────────────
    def lenfeat(df_in):
        t = df_in.text.astype(str); w = t.str.split().str.len()
        return np.c_[w, t.str.len(), t.str.count(r"[.!?]"), t.str.count(",")]
    
    names_c4 = ["n_kata", "n_karakter", "n_titik/tanya/seru", "n_koma"]
    Xtr = lenfeat(tr_df); Xte = lenfeat(te_df)
    print("\n[+] RINCIAN FITUR C4 RIIL (DARI TRIAL SAAT INI):")
    for idx_f, nm_f in enumerate(names_c4):
        clf_c4 = DecisionTreeClassifier(max_depth=3, random_state=0).fit(Xtr[:, [idx_f]], tr_df.label)
        a_f = accuracy_score(te_df.label, clf_c4.predict(Xte[:, [idx_f]])) * 100
        mean_f0 = Xtr[tr_df.label == 0, idx_f].mean()
        mean_f1 = Xtr[tr_df.label == 1, idx_f].mean()
        print(f"  • {nm_f:<20} akurasi={a_f:5.1f}% | rata2 fakta={mean_f0:7.2f} | rata2 hoaks={mean_f1:7.2f}")

# ── 5. SAMPEL KLARIFIKASI & BELUM TERBUKTI DARI LABEL 1 ─────────────────────
f_all_h = sorted(f for f in os.listdir(RAW_DIR) if f.startswith("dataset_turnbackhoax") or f.startswith("hoax_dataset"))
all_hoax_raw = []
for fh in f_all_h:
    p = os.path.join(RAW_DIR, fh)
    d = pd.read_excel(p) if p.endswith((".xlsx", ".xls")) else pd.read_csv(p)
    t_c = "Title" if "Title" in d.columns else "judul"
    b_c = "Clean Narasi" if "Clean Narasi" in d.columns else ("teks" if "teks" in d.columns else None)
    if t_c in d.columns:
        all_hoax_raw.append(d[[t_c] + ([b_c] if b_c else [])].rename(columns={t_c: "title", b_c: "body"}))

if all_hoax_raw:
    df_hr = pd.concat(all_hoax_raw, ignore_index=True)
    tag_r = df_hr.title.str.extract(r"^\s*[\[\(\{]([^\]\)\}]{1,25})[\]\)\}]")[0].str.upper().str.strip()
    
    print("\n" + "=" * 80)
    print("[+] 10 SAMPEL TAG 'KLARIFIKASI' (LABEL 1 MENTAH):")
    print("=" * 80)
    for i, t in enumerate(df_hr[tag_r == "KLARIFIKASI"]["title"].dropna().head(10)):
        print(f"  [{i+1}] {t}")

    print("\n" + "=" * 80)
    print("[+] 10 SAMPEL TAG 'BELUM TERBUKTI' (LABEL 1 MENTAH):")
    print("=" * 80)
    for i, t in enumerate(df_hr[tag_r == "BELUM TERBUKTI"]["title"].dropna().head(10)):
        print(f"  [{i+1}] {t}")