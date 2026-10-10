"""
01b_rebuild_dataset_final.py — Versi Final Bebas Bias & Kebocoran
Menerapkan:
  1. Eksklusi Komdigi (99.9% debunker).
  2. Isolasi Label Noise Kompas -> eval_kompas_cekfakta.csv (hoaks non-Mafindo).
  3. Whitelist Label 1 -> label1_ambigu.csv.
  4. Ekspor tag BENAR murni ter-dedup -> eval_benar.csv.
  5. Deduplikasi judul mentah lintas sumber (membuang duplikasi TBH vs HoaxArchive).
  6. Penyatuan graf judul identik lintas split (comp pada a1+a2).
  7. Seleksi strata otomatis apriori (Preset B -> C -> A).
  8. Output terisolasi ke folder trial.
"""

import os, re, sys, json, hashlib, platform, datetime
import numpy as np, pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.stats import ks_2samp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import accuracy_score

sys.path.insert(0, os.getcwd())
import text_pipeline as tp
assert tp.PIPELINE_VERSION == "tp-1.5", "text_pipeline.py belum versi tp-1.5"

SEED = 42
RAW_DIR = os.environ.get("RAW_DIR") or ("../data/raw" if os.path.exists("../data/raw") else "data/raw")
OUT_DIR = os.environ.get("OUT_DIR") or ("../data/processed_v2_trial" if os.path.exists("../data") else "data/processed_v2_trial")
os.makedirs(OUT_DIR, exist_ok=True)
print("OUT_DIR =", os.path.abspath(OUT_DIR))

CFG = dict(
    MIN_WORDS=10, MAX_WORDS=60, NEAR_DUP_COS=0.90, GROUP_COS=0.70,
    LEN_BINS=[0, 20, 30, 40, 50, 60, 10_000],
    YEAR_BINS=[2016, 2019, 2021, 2022, 2023],
    N_FOLDS=20, TRAIN_FOLDS=14, VAL_FOLDS=2, DEVTEST_FOLDS=2, LOCKBOX_FOLDS=2, SEED=SEED
)

STRATA_PRESETS = {
    "A_lama":             ["sub_topic", "len_bin"],
    "B_tahun":            ["sub_topic", "len_bin", "year_bin"],
    "C_tahun_tanpa_len":  ["sub_topic", "year_bin"],
}
MIN_TRAIN_OK = 1500

SOURCES = [
    dict(name="turnbackhoax.id",   label=1, file="dataset_turnbackhoax_10_cleaned", title=["Title"], body=["Clean Narasi", "Narasi"], date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="komdigi.go.id",     label=1, file="komdigi_hoaks",                   title=["title"], body=["body_text", "excerpt"],   date=["published_at"]),
    dict(name="hoax_archive_15k",  label=1, file="hoax_dataset_with_text",          title=["judul"], body=["teks", "deskripsi"],     date=["tanggal"]),
    dict(name="tempo.co",          label=0, file="dataset_tempo_6k_cleaned",        title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="cnnindonesia.com",  label=0, file="dataset_cnn_10k_cleaned",         title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="kompas.com",        label=0, file="dataset_kompas_4k_cleaned",       title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
]
EXCLUDE_SOURCES = ["komdigi.go.id"]

LOG = []
def log(step, df, note=""):
    g = df.groupby(["source", "label"]).size()
    for (s, l), n in g.items():
        LOG.append(dict(step=step, source=s, label=int(l), n=int(n), note=note))
    print(f"[{step:<28}] total={len(df):>7,} | per label={df.label.value_counts().sort_index().to_dict()}  {note}")

def show_retention():
    d = pd.DataFrame(LOG).groupby(["step", "label"]).n.sum().unstack().fillna(0)
    d = d.loc[list(dict.fromkeys(r["step"] for r in LOG))]
    out = d.astype(int).join((d.div(d.iloc[0]) * 100).round(1).add_suffix("_%dari_mentah"))
    print("\nRETENSI PER LANGKAH:")
    print(out.to_string())

# ── 1. MUAT DATA MENTAH ──────────────────────────────────────────────────────
QUOTE_EXTRACT = re.compile(
    r'(?:narasi|klaim|unggahan|postingan|berisi\s+informasi)[^“"\n]{0,80}?[“"]([^”"]{15,600})[”"]', re.I)

def extract_hoax_claim(judul, teks):
    m = QUOTE_EXTRACT.search(str(teks))
    if m and len(m.group(1).split()) >= 6:
        return m.group(1).strip()
    return ""

def pick(row, names):
    for n in names:
        if n in row.index:
            v = row[n]
            if pd.notna(v) and str(v).strip() not in ("", "nan", "None"):
                return str(v).strip()
    return ""

def load_source(s):
    files = sorted(f for f in os.listdir(RAW_DIR) if f.startswith(s["file"] + ".")) or \
            sorted(f for f in os.listdir(RAW_DIR) if f.startswith(s["file"]))
    if not files:
        print(f"!! BERKAS TIDAK DITEMUKAN untuk {s['name']}: {s['file']}"); return pd.DataFrame()
    p = os.path.join(RAW_DIR, files[0])
    d = pd.read_excel(p) if p.endswith((".xlsx", ".xls")) else pd.read_csv(p)
    titles = [pick(r, s["title"]) for _, r in d.iterrows()]
    bodies = [pick(r, s["body"]) for _, r in d.iterrows()]
    date_raws = [pick(r, s["date"]) for _, r in d.iterrows()]
    if s["name"] == "hoax_archive_15k":
        bodies = [extract_hoax_claim(t, b) for t, b in zip(titles, bodies)]
    out = pd.DataFrame({"title": titles, "body": bodies, "date_raw": date_raws})
    _parsed = pd.to_datetime(out["date_raw"], errors="coerce", format="mixed")
    _years = out["date_raw"].astype(str).str.extract(r'\b(20\d\d)\b')[0]
    out["date"] = _parsed.fillna(pd.to_datetime(_years + "-01-01", errors="coerce"))
    out["source"], out["label"], out["file"] = s["name"], s["label"], files[0]
    print(f"{s['name']:<18} {files[0]:<45} baris={len(out):>6,} | isi kosong={(out.body=='').mean()*100:5.1f}% | tanggal terbaca={out.date.notna().mean()*100:5.1f}%")
    return out

raw = pd.concat([load_source(s) for s in SOURCES], ignore_index=True)
log("1_raw", raw)

raw = raw[~raw.source.isin(EXCLUDE_SOURCES)].reset_index(drop=True)
log("1c_sumber_dikeluarkan", raw, str(EXCLUDE_SOURCES))

# ── 2. CEK LABEL NOISE & WHITELIST LABEL 1 ───────────────────────────────────
HOAX_LIKE = {"HOAKS", "HOAX", "SALAH", "DISINFORMASI", "KLARIFIKASI", "HASUT"}
HOAX_RX   = r"HOAX|HOAKS|DISINFORMASI|MISINFORMASI|FALSE|SALAH|FITNAH|HASUT|PENIPUAN"
tag = raw.title.str.extract(r"^\s*[\[\(\{]([^\]\)\}]{1,25})[\]\)\}]")[0].str.upper().str.strip()

# 2a. Evaluasi "BENAR" (hanya tag BENAR murni ter-dedup)
ev_benar = raw[(raw.label == 1) & (tag == "BENAR")].drop_duplicates(subset=["title"]).copy()
ev_benar.to_csv(os.path.join(OUT_DIR, "eval_benar.csv"), index=False, encoding="utf-8-sig")
print(f"✓ Diekspor {len(ev_benar)} baris tag 'BENAR' ter-dedup ke eval_benar.csv")

# 2b. Label Noise Kompas Cek-Fakta -> eval_kompas_cekfakta.csv (hoaks non-Mafindo independen)
t0 = raw.title.str.replace(r"^\s*(?:\[[^\]]{1,25}\]\s*)+", "", regex=True)
fc = (raw.label == 0) & (tag.isin(HOAX_LIKE) | t0.str.match(r"(?i)\s*(?:cek\s+fakta|beredar\s+hoaks?|hoaks\s+atau\s+fakta|infografik:\s*hoaks|kumpulan\s+hoaks)"))
raw[fc].to_csv(os.path.join(OUT_DIR, "eval_kompas_cekfakta.csv"), index=False, encoding="utf-8-sig")
print(f"✓ Diekspor {int(fc.sum())} artikel cek-fakta Kompas ke eval_kompas_cekfakta.csv (sebagai set uji non-Mafindo)")

# 2c. Whitelist Label 1: Pisahkan klaim yang tidak memiliki tag hoaks jelas ke label1_ambigu.csv
amb = (raw.label == 1) & ~tag.fillna("").str.contains(HOAX_RX)
raw[amb].to_csv(os.path.join(OUT_DIR, "label1_ambigu.csv"), index=False, encoding="utf-8-sig")
print(f"✓ Dipisahkan {int(amb.sum())} baris label 1 ambigu ke label1_ambigu.csv")

# Buang dari data latih: fc, amb, dan baris tag BENAR
ev_mask = (raw.label == 1) & (tag == "BENAR")
raw = raw[~(fc | amb | ev_mask)].reset_index(drop=True)
log("1d_label_noise_dibuang", raw)

# 2d. Deduplikasi Judul Mentah Lintas-Sumber (Membuang duplikasi TurnBackHoax vs HoaxArchive)
nk = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"^\s*(?:\[[^\]]{1,25}\]\s*)+", "", str(s).lower()))
raw["tkey"] = raw.title.map(nk)
raw["_bl"] = raw.body.str.split().str.len()
raw = raw.sort_values("_bl", ascending=False, kind="stable")
dup = raw.tkey.ne("") & raw.duplicated(["label", "tkey"], keep="first")
print("Judul duplikat dibuang per sumber:", raw[dup].groupby("source").size().to_dict())
raw = raw[~dup].drop(columns=["_bl"]).sort_index().reset_index(drop=True)
log("1e_judul_duplikat", raw)

# ── 3. BENTUK TEKS ───────────────────────────────────────────────────────────
raw["title_c"] = raw.title.map(tp.clean)
raw["body_c"]  = [tp.strip_leading_title(t, tp.clean(b)) for t, b in zip(raw.title_c, raw.body)]
raw["text"]    = [tp.build_text(t, b) for t, b in zip(raw.title, raw.body)]
raw["n_words_raw"] = raw.text.str.split().str.len()

df = raw[raw.text.str.len() > 0].copy()
log("2_teks_terbentuk", df)
df = df[df.n_words_raw >= CFG["MIN_WORDS"]].copy()
log("2b_min_kata", df, f">= {CFG['MIN_WORDS']} kata")

# ── 4. SUB-TOPIK POLITIK ─────────────────────────────────────────────────────
SUB_TOPIC_RULES = {
    "pemilu": ["pemilu", "pilpres", "pilkada", "kpu", "bawaslu", "surat suara", "sirekap", "coblos", "capres", "cawapres", "cawagub", "caleg", "debat", "partai", "pdip", "gerindra", "golkar", "nasdem", "pks", "demokrat", "kpud", "panwaslu", "koalisi", "oposisi", "cawe-cawe", "dinasti", "legislatif"],
    "kebijakan": ["bansos", "subsidi", "bbm", "ikn", "apbn", "apbd", "pajak", "omnibus", "undang-undang", "perpres", "perda", "tarif listrik", "bpjs", "kebijakan pemerintah", "asn", "bumn", "pertamina", "bulog", "beras bansos", "makan siang", "kemensos", "kemenkeu", "kemendagri", "reshuffle", "kabinet", "istana negara", "anggaran"],
    "tokoh": ["jokowi", "prabowo", "gibran", "anies", "ganjar", "megawati", "menteri", "presiden", "pejabat", "mahfud", "gubernur", "bupati", "walikota", "dpr", "mpr", "dprd", "puan", "erick thohir", "bahlil", "kaesang", "ridwan kamil", "ahok", "khofifah", "kades", "sri mulyani", "luhut", "nadiem", "basuki", "tito karnavian", "yasonna", "paspampres"],
    "hukum": ["korupsi", "kpk", "mk", "mahkamah", "polri", "kejaksaan", "tangkap", "ott", "sidang", "vonis", "hakim", "polisi", "tni", "aparat", "kejagung", "jaksa", "kasasi", "mahkamah agung", "yudikatif"],
}
NOISE = ["hujan es", "imunitas", "kanker", "diabetes", "ramuan", "vaksin hpv", "stroke", "gempa bumi", "tsunami", "cuaca ekstrem",
         "pelatih timnas", "liga 1", "piala aff", "frank de boer", "ronaldo", "messi", "shin tae-yong", "pesulap", "zodiak",
         "air kelapa", "janin", "kehamilan", "rahim", "kolesterol", "asam urat", "lowongan", "loker", "rekrutmen", "pendaftaran kerja",
         "pt pertamina persero loker", "seleksi bumn"]
wb = lambda words: re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.I)
RULES_WB = {k: wb(v) for k, v in SUB_TOPIC_RULES.items()}; NOISE_WB = wb(NOISE)

def topic_wb(t):
    if NOISE_WB.search(t): return "bukan_politik"
    for k, rx in RULES_WB.items():
        if rx.search(t): return k
    return "umum"

df["sub_topic"] = df.text.map(topic_wb)
df = df[~df.sub_topic.isin(["umum", "bukan_politik"])].copy()
log("3_filter_politik", df)

# ── 5. SIMETRI PANJANG & DEDUPLIKASI GRAF DENGAN PENYATUAN JUDUL ────────────
df["text"] = df.text.map(lambda t: tp.cap_sentences(t, CFG["MAX_WORDS"]))
df["n_words"] = df.text.str.split().str.len()
df = df[df.n_words >= CFG["MIN_WORDS"]].reset_index(drop=True)
log("4_batas_panjang_sama", df, f"maks {CFG['MAX_WORDS']} kata")

before = len(df)
df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)
log("4b_duplikat_persis", df, f"dibuang {before-len(df):,}")

def similarity_edges(texts, thr, chunk=500):
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.5, sublinear_tf=True, dtype=np.float32)
    X = vec.fit_transform(texts).tocsr(); XT = X.T.tocsr()
    I, J, V = [np.empty(0, int)], [np.empty(0, int)], [np.empty(0, np.float32)]
    for s in range(0, X.shape[0], chunk):
        S = (X[s:s + chunk] @ XT).tocoo()
        m = (S.data >= thr) & (S.row + s < S.col)
        I.append(S.row[m] + s); J.append(S.col[m]); V.append(S.data[m])
    return np.concatenate(I), np.concatenate(J), np.concatenate(V)

def comp(n, I, J):
    return connected_components(coo_matrix((np.ones(len(I)), (I, J)), shape=(n, n)), directed=False)[1]

n = len(df); lab = df.label.to_numpy()
I, J, V = similarity_edges(df.text.tolist(), CFG["GROUP_COS"])
hi = V >= CFG["NEAR_DUP_COS"]
keep = np.ones(n, bool)
cross = hi & (lab[I] != lab[J])
keep[I[cross]] = False; keep[J[cross]] = False
same = hi & (lab[I] == lab[J])
if same.any():
    c = comp(n, I[same], J[same]); first = pd.Series(np.arange(n)).groupby(c).transform("min").to_numpy()
    touched = np.zeros(n, bool); touched[I[same]] = True; touched[J[same]] = True
    keep &= ~(touched & (np.arange(n) != first))

old_idx = np.flatnonzero(keep); remap = -np.ones(n, int); remap[old_idx] = np.arange(len(old_idx))
m = keep[I] & keep[J]
df = df.loc[keep].reset_index(drop=True)
g = comp(len(df), remap[I[m]], remap[J[m]])
df["group_id"] = g

# Penyatuan Grup Berdasarkan Judul Identik (Mencegah Kebocoran Lintas Split)
tk = df.title_c.map(nk)
tk = tk.where(tk != "", pd.Series("_e" + df.index.astype(str), index=df.index))
def chain(keys):
    I_, J_ = [], []
    for idx in pd.Series(np.arange(len(keys))).groupby(keys.to_numpy(), observed=True).agg(list):
        I_ += idx[:-1]; J_ += idx[1:]
    return np.array(I_, int), np.array(J_, int)
a1, b1 = chain(df.group_id); a2, b2 = chain(tk)
df["group_id"] = comp(len(df), np.r_[a1, a2], np.r_[b1, b2])
log("4c_dedup_near", df)

# ── 6. SIMULASI & SELEKSI STRATA OTOMATIS BERBASIS PROTOKOL APRIORI ──────────
df["len_bin"]  = pd.cut(df.n_words, bins=CFG["LEN_BINS"]).astype(str)
yb = pd.cut(df.date.dt.year, CFG["YEAR_BINS"])
df["year_bin"] = yb.astype(str).where(yb.notna(), other=np.nan)

def match_n(d, keys):
    d = d.dropna(subset=keys)
    c = d.groupby(keys + ["label"], observed=True).size().unstack("label", fill_value=0)
    for l in (0, 1):
        if l not in c.columns: c[l] = 0
    return int(2 * c[[0, 1]].min(axis=1).sum())

print("\n" + "=" * 80)
print("[6a] SIMULASI UKURAN SEBELUM PENYEIMBANGAN (PADA df AKTUAL):")
for nm, keys in STRATA_PRESETS.items():
    n_ = match_n(df, keys)
    print(f"  {nm:<20} {'+'.join(keys):<32} pasangan={n_:>6,}  train≈{int(n_*0.7):,}")

# Eksekusi Pohon Keputusan Apriori
n_b = match_n(df, STRATA_PRESETS["B_tahun"])
if int(n_b * 0.7) >= MIN_TRAIN_OK:
    STRATA_NAME = "B_tahun"
    LEN_MATCH_TRUNC = False
else:
    n_c = match_n(df, STRATA_PRESETS["C_tahun_tanpa_len"])
    if int(n_c * 0.7) >= MIN_TRAIN_OK:
        STRATA_NAME = "C_tahun_tanpa_len"
        LEN_MATCH_TRUNC = True
    else:
        STRATA_NAME = "A_lama"
        LEN_MATCH_TRUNC = False

STRATA = STRATA_PRESETS[STRATA_NAME]
print(f"\n>> KEPUTUSAN PROTOKOL: Dipilih '{STRATA_NAME}' (Strata: {' x '.join(STRATA)} | LEN_MATCH_TRUNC={LEN_MATCH_TRUNC})")

if LEN_MATCH_TRUNC:
    rng = np.random.default_rng(SEED)
    nw = df.text.str.split().str.len().clip(upper=CFG["MAX_WORDS"])
    pool = {k: nw[(df.label == 1) & (df.sub_topic == k)].to_numpy() for k in df.sub_topic.unique()}
    def _cap(t, lab, k):
        if lab == 1 or len(pool[k]) == 0: return tp.cap_sentences(t, CFG["MAX_WORDS"])
        return tp.cap_sentences(t, max(CFG["MIN_WORDS"], int(rng.choice(pool[k]))))
    df["text"] = [_cap(t, l, k) for t, l, k in zip(df.text, df.label, df.sub_topic)]
    df["n_words"] = df.text.str.split().str.len()
    df["len_bin"] = pd.cut(df.n_words, bins=CFG["LEN_BINS"]).astype(str)

if "year_bin" in STRATA:
    nb = len(df); df = df[df.year_bin.notna()].reset_index(drop=True)
    log("5b_dalam_cakupan_2017_2023", df, f"dibuang {nb-len(df):,} di luar cakupan tahun")

def coarsened_match(d, keys, seed):
    parts = []
    for _, gk in d.groupby(keys, observed=True):
        c = gk.label.value_counts()
        if len(c) < 2: continue
        k = int(c.min())
        parts += [gg.sample(k, random_state=seed) for _, gg in gk.groupby("label")]
    return pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)

bal = coarsened_match(df, STRATA, SEED)
assert len(bal) == match_n(df, STRATA), "simulasi match_n tidak cocok dengan hasil coarsened_match"
log("6_seimbang", bal, f"strata = {'x'.join(STRATA)}")
print(f"Ukuran Bal: {len(df):,} -> {len(bal):,} (kehilangan {(1-len(bal)/len(df))*100:.1f}%)")

sgkf = StratifiedGroupKFold(n_splits=CFG["N_FOLDS"], shuffle=True, random_state=SEED)
fold = np.full(len(bal), -1)
for k, (_, te_idx) in enumerate(sgkf.split(bal, bal.label, bal.group_id)):
    fold[te_idx] = k
edges = np.cumsum([CFG["TRAIN_FOLDS"], CFG["VAL_FOLDS"], CFG["DEVTEST_FOLDS"]])
bal["split"] = np.select([fold < edges[0], fold < edges[1], fold < edges[2]], ["train", "val", "dev_test"], "lockbox")
bal["id"] = [f"POL2-{i+1:06d}" for i in range(len(bal))]

sz = pd.crosstab(bal.split, bal.label).assign(total=lambda x: x.sum(axis=1))
print(sz.to_string())

# ── 7. VERIFIKASI KRITERIA ───────────────────────────────────────────────────
res = []
dev = bal[bal.split != "lockbox"]
tr_, va_, te_ = (bal[bal.split == s] for s in ("train", "val", "dev_test"))

for s, d in (("train", tr_), ("val", va_), ("dev_test", te_)):
    r  = d.groupby("label").text.apply(lambda x: x.map(tp.dup_title_strict).mean() * 100)
    res.append((f"C1 judul ganda harafiah [{s}]", abs(r.get(0, 0) - r.get(1, 0)), 5, abs(r.get(0, 0) - r.get(1, 0)) <= 5))
    rp = d.groupby("label").text.apply(lambda x: x.map(tp.dup_title_para).mean() * 100)
    print(f"INFO parafrasa judul-lead [{s}]: fakta={rp.get(0, 0):.1f}% | hoaks={rp.get(1, 0):.1f}%")

ks = ks_2samp(dev[dev.label == 0].n_words, dev[dev.label == 1].n_words).statistic
res.append(("C2 KS panjang kata", ks, 0.10, ks <= 0.10))
e = dev.groupby("label").text.apply(lambda x: x.str.endswith((".", "!", "?")).mean() * 100)
res.append(("C3 berakhir tanda baca", abs(e.get(0, 0) - e.get(1, 0)), 5, abs(e.get(0, 0) - e.get(1, 0)) <= 5))

def lenfeat(d):
    t = d.text; w = t.str.split().str.len()
    return np.c_[w, t.str.len(), t.str.count(r"[.!?]"), t.str.count(",")]
dt = DecisionTreeClassifier(max_depth=4, random_state=0).fit(lenfeat(tr_), tr_.label)
acc_len = accuracy_score(te_.label, dt.predict(lenfeat(te_)))
res.append(("C4 akurasi fitur panjang (dev_test)", acc_len, 0.60, acc_len <= 0.60))

viol = bal.groupby("group_id").split.nunique().gt(1).sum()
res.append(("C5 grup melintasi split", int(viol), 0, viol == 0))
tp_ = dev.groupby("label").sub_topic.value_counts(normalize=True).unstack(0).fillna(0)
dtopic = (tp_[0] - tp_[1]).abs().max() * 100
res.append(("C6 selisih proporsi sub-topik", dtopic, 2, dtopic <= 2))

print(f"\n{'Kriteria':<40}{'Nilai':>10}{'Ambang':>9}  Hasil")
for name, v, th, ok in res:
    print(f"{name:<40}{v:>10.3f}{th:>9}  {'LULUS' if ok else 'GAGAL'}")

# Diagnosis Riil C4 per Fitur
names_c4 = ["n_kata", "n_karakter", "n_titik/tanya/seru", "n_koma"]
Xtr = lenfeat(tr_); Xte = lenfeat(te_)
print("\n[+] RINCIAN FITUR C4 RIIL (DARI BUILD INI):")
for idx_f, nm_f in enumerate(names_c4):
    clf_c4 = DecisionTreeClassifier(max_depth=3, random_state=0).fit(Xtr[:, [idx_f]], tr_.label)
    a_f = accuracy_score(te_.label, clf_c4.predict(Xte[:, [idx_f]])) * 100
    mean_f0 = Xtr[tr_.label.values == 0, idx_f].mean()
    mean_f1 = Xtr[tr_.label.values == 1, idx_f].mean()
    print(f"  • {nm_f:<20} akurasi={a_f:5.1f}% | rata2 fakta={mean_f0:7.2f} | rata2 hoaks={mean_f1:7.2f}")

first8 = lambda d: d.text.str.split().str[:8].str.join(" ")
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
lr = LogisticRegression(max_iter=2000).fit(vec.fit_transform(first8(tr_)), tr_.label)
acc8 = accuracy_score(te_.label, lr.predict(vec.transform(first8(te_))))
print(f"\nINFO akurasi 8 kata pertama: {acc8*100:.2f}%")

have = [l for l in (0, 1) if dev[dev.label == l].date.notna().any()]
if len(have) == 2:
    yr = pd.crosstab(dev.date.dt.year, dev.label); yr = yr.div(yr.sum(axis=0), axis=1)
    print(f"INFO tumpang-tindih distribusi tahun: {float(np.minimum(yr[0], yr[1]).sum())*100:.1f}%")

show_retention()

# ── 8. SIMPAN + MANIFEST ─────────────────────────────────────────────────────
bal = bal.drop(columns=["title", "body"], errors="ignore").rename(columns={"title_c": "title", "body_c": "body"})
cols = ["id", "text", "title", "body", "label", "sub_topic", "source", "group_id", "date"]
for sp in ("train", "val", "dev_test"):
    bal[bal.split == sp][cols].to_csv(os.path.join(OUT_DIR, f"{sp}.csv"), index=False, encoding="utf-8-sig")
bal[bal.split != "lockbox"][cols + ["split"]].to_csv(os.path.join(OUT_DIR, "dataset_v2_full.csv"), index=False, encoding="utf-8-sig")
LOCK_DIR = os.path.join(OUT_DIR, "LOCKBOX"); os.makedirs(LOCK_DIR, exist_ok=True)
bal[bal.split == "lockbox"][cols].to_csv(os.path.join(LOCK_DIR, "lockbox.csv"), index=False, encoding="utf-8-sig")
open(os.path.join(LOCK_DIR, "JANGAN_DIBUKA.txt"), "w", encoding="utf-8").write(
    "Set uji tersegel. Dibuka SATU KALI untuk pelaporan akhir, setelah model, ambang, dan analisis dikunci di PROTOKOL.\n")
pd.DataFrame(LOG).to_csv(os.path.join(OUT_DIR, "audit_log_per_langkah.csv"), index=False)
pd.DataFrame(res, columns=["kriteria", "nilai", "ambang", "lulus"]).to_csv(os.path.join(OUT_DIR, "hasil_kriteria.csv"), index=False)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

ALL_OK = all(ok for *_, ok in res)
cfg_out = dict(CFG, pipeline_version=tp.PIPELINE_VERSION, strata_name=STRATA_NAME, strata=STRATA, len_match_trunc=LEN_MATCH_TRUNC,
               exclude_sources=EXCLUDE_SOURCES, python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__,
               created=datetime.datetime.now().isoformat(timespec="seconds"), raw_dir=RAW_DIR, all_criteria_passed=bool(ALL_OK))
json.dump(cfg_out, open(os.path.join(OUT_DIR, "config.json"), "w"), indent=2)

man = [{"berkas": f, "sha256": sha(os.path.join(OUT_DIR, f))} for f in sorted(os.listdir(OUT_DIR))
       if f not in ("MANIFEST_sha256.csv", "LOCKBOX") and os.path.isfile(os.path.join(OUT_DIR, f))]
man += [{"berkas": "RAW/" + f, "sha256": sha(os.path.join(RAW_DIR, f))} for f in sorted(raw["file"].unique())]
man += [{"berkas": "LOCKBOX/lockbox.csv", "sha256": sha(os.path.join(LOCK_DIR, "lockbox.csv"))}]
man += [{"berkas": "text_pipeline.py", "sha256": sha("text_pipeline.py")}]
if os.path.exists("01b_rebuild_dataset_final.py"):
    man += [{"berkas": "01b_rebuild_dataset_final.py", "sha256": sha("01b_rebuild_dataset_final.py")}]
pd.DataFrame(man).to_csv(os.path.join(OUT_DIR, "MANIFEST_sha256.csv"), index=False)
print("\nTersimpan di:", os.path.abspath(OUT_DIR))