# =============================================================================
# 01b_rebuild_dataset — versi final (pipeline tp-1.5)
# Tiap "# %%" = satu sel notebook. Default OUT_DIR = folder TRIAL (processed_v2 tidak disentuh).
# =============================================================================

# %% [1] KONFIGURASI -----------------------------------------------------------
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
assert tp.PIPELINE_VERSION == "tp-1.5", "text_pipeline.py belum versi tp-1.5 (restart kernel / reload)"

SEED = 42
RAW_DIR = os.environ.get("RAW_DIR") or ("../data/raw" if os.path.exists("../data/raw") else "data/raw")
OUT_DIR = os.environ.get("OUT_DIR") or ("../data/processed_v2_trial" if os.path.exists("../data") else "data/processed_v2_trial")
os.makedirs(OUT_DIR, exist_ok=True)
print("OUT_DIR =", os.path.abspath(OUT_DIR))

CFG = dict(MIN_WORDS=10, MAX_WORDS=60, NEAR_DUP_COS=0.90, GROUP_COS=0.70,
           LEN_BINS=[0, 20, 30, 40, 50, 60, 10_000],
           YEAR_BINS=[2016, 2019, 2021, 2022, 2023],      # (2016,2019],(2019,2021],2022,2023 -> cakupan 2017-2023
           N_FOLDS=20, TRAIN_FOLDS=14, VAL_FOLDS=2, DEVTEST_FOLDS=2, LOCKBOX_FOLDS=2, SEED=SEED)

# Pilih strata SETELAH melihat sel simulasi [6a]. Perubahan di sini adalah keputusan desain: catat di PROTOKOL.
STRATA_PRESETS = {
    "A_lama":             ["sub_topic", "len_bin"],
    "B_tahun":            ["sub_topic", "len_bin", "year_bin"],
    "C_tahun_tanpa_len":  ["sub_topic", "year_bin"],       # pakai bersama LEN_MATCH_TRUNC = True
}
STRATA_NAME = "B_tahun"
STRATA = STRATA_PRESETS[STRATA_NAME]
LEN_MATCH_TRUNC = False        # True = fakta dipotong mengikuti sebaran panjang hoaks per sub-topik (asimetris; wajib dicatat)
MIN_TRAIN_OK = 1500            # peringatan bila train di bawah ini

SOURCES = [
    dict(name="turnbackhoax.id",   label=1, file="dataset_turnbackhoax_10_cleaned", title=["Title"], body=["Clean Narasi", "Narasi"], date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="komdigi.go.id",     label=1, file="komdigi_hoaks",                   title=["title"], body=["body_text", "excerpt"],   date=["published_at"]),
    dict(name="hoax_archive_15k",  label=1, file="hoax_dataset_with_text",          title=["judul"], body=["teks", "deskripsi"],     date=["tanggal"]),
    dict(name="tempo.co",          label=0, file="dataset_tempo_6k_cleaned",        title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="cnnindonesia.com",  label=0, file="dataset_cnn_10k_cleaned",         title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
    dict(name="kompas.com",        label=0, file="dataset_kompas_4k_cleaned",       title=["Title"], body=["FullText", "text_new"],  date=["Timestamp", "Date", "Tanggal", "date"]),
]
EXTRA_SOURCES = []
USE_TITLE_ONLY_SOURCES = False
EXCLUDE_SOURCES = ["komdigi.go.id"]     # isi = tulisan pemeriksa fakta ("Penjelasan : Beredar ..."); 99,9% terpotong DEBUNK_CUT

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
    print("\nRETENSI PER LANGKAH (filter yang menghantam satu label jauh lebih keras harus dibenarkan tertulis di PROTOKOL):")
    print(out.to_string())

# %% [2] MUAT DATA MENTAH ------------------------------------------------------
# Ekstraksi klaim hoax_archive: HANYA kutipan klaim. Tidak ada fallback ke teks (teks diawali kalimat vonis).
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

raw = pd.concat([load_source(s) for s in SOURCES + EXTRA_SOURCES], ignore_index=True)
log("1_raw", raw)

no_body = raw.assign(e=(raw.body == "")).groupby("source").e.mean()
title_only = no_body[no_body > 0.95].index.tolist()
if title_only and not USE_TITLE_ONLY_SOURCES:
    print(f"\n>> Sumber tanpa isi dikeluarkan: {title_only}")
    raw = raw[~raw.source.isin(title_only)].reset_index(drop=True)
    log("1b_tanpa_sumber_judul_saja", raw)

raw = raw[~raw.source.isin(EXCLUDE_SOURCES)].reset_index(drop=True)
log("1c_sumber_dikeluarkan", raw, str(EXCLUDE_SOURCES))

# %% [2b] BACA 15 HASIL EKSTRAKSI hoax_archive (celah 80 karakter bisa menangkap kutipan dari bagian bantahan)
_h = raw[(raw.source == "hoax_archive_15k") & (raw.body != "")]
print(f"hoax_archive dengan klaim terekstrak: {len(_h):,}")
for _, r in _h.sample(min(15, len(_h)), random_state=1).iterrows():
    print("  J:", r.title[:90], "\n  K:", r.body[:120], "\n")

# %% [2c] CEK LABEL NOISE (tag di awal judul) ---------------------------------
BENAR_TAGS = {"BENAR", "VALID", "EDUKASI"}                                   # sesuaikan dengan tabel yang tercetak
HOAX_LIKE  = {"HOAKS", "HOAX", "SALAH", "DISINFORMASI", "KLARIFIKASI", "HASUT"}
tag = raw.title.str.extract(r"^\s*[\[\(\{]([^\]\)\}]{1,25})[\]\)\}]")[0].str.upper().str.strip()
print(raw.assign(tag=tag).groupby(["label", "source", "tag"], dropna=False).size().to_string())
print("\nJudul fakta berawalan tag:"); print(raw[(raw.label == 0) & tag.notna()][["source", "title"]].head(20).to_string())

ev_mask   = (raw.label == 1) & tag.isin(BENAR_TAGS)
# ✅ GANTI BLOK TERSEBUT DI [2c] MENJADI:
t0 = raw.title.str.replace(r"^\s*(?:\[[^\]]{1,25}\]\s*)+", "", regex=True)
fc = (raw.label == 0) & (tag.isin(HOAX_LIKE) | t0.str.match(r"(?i)\s*(?:cek\s+fakta|beredar\s+hoaks?)"))
kw = (raw.label == 0) & raw.title.str.contains(r"hoaks|hoax|disinformasi|klarifikasi|cek fakta", case=False)

print("\n[2c] DIBUANG sebagai artikel cek-fakta berlabel 0:", int(fc.sum()))
print(raw[fc].groupby("source").size().to_string())
print("\n[2c] MENGANDUNG KATA KUNCI TAPI DIPERTAHANKAN (Berita Kebijakan tentang Hoaks):")
print(raw[kw & ~fc][["source", "title"]].to_string())

fact_noise = fc
print(f"\nBaris berlabel 'benar' (hanya evaluasi): {int(ev_mask.sum())} | fakta bertag hoaks-like (dibuang): {int(fact_noise.sum())}")
raw[ev_mask].to_csv(os.path.join(OUT_DIR, "eval_benar.csv"), index=False, encoding="utf-8-sig")
raw = raw[~(ev_mask | fact_noise)].reset_index(drop=True)
log("1d_label_noise_dibuang", raw)

# %% [3] BENTUK TEKS -----------------------------------------------------------
raw["title_c"] = raw.title.map(tp.clean)
raw["body_c"]  = [tp.strip_leading_title(t, tp.clean(b)) for t, b in zip(raw.title_c, raw.body)]
raw["text"]    = [tp.build_text(t, b) for t, b in zip(raw.title, raw.body)]
raw["n_words_raw"] = raw.text.str.split().str.len()

print("Tag kategori di awal judul/isi (dibuang untuk SEMUA kelas):")
print(raw.assign(tag_judul=raw.title.map(tp.has_leading_tag), tag_isi=raw.body.map(tp.has_leading_tag))
         .groupby(["label", "source"])[["tag_judul", "tag_isi"]].sum().to_string())

RESIDU = re.compile(r"TEMPO\.CO|CNN Indonesia|KOMPAS\.com|ADVERTISEMENT|SCROLL TO CONTINUE|[Ll]ihat [Jj]uga|[Bb]aca [Jj]uga|={3,}")
print("\nResidu penanda sumber/antarmuka di teks akhir (harus ~0), per sumber:")
print(raw.assign(r=raw.text.str.contains(RESIDU)).groupby(["label", "source"]).r.agg(["sum", "mean"]).round(3).to_string())

df = raw[raw.text.str.len() > 0].copy()
log("2_teks_terbentuk", df)
df = df[df.n_words_raw >= CFG["MIN_WORDS"]].copy()
log("2b_min_kata", df, f">= {CFG['MIN_WORDS']} kata")

# %% [4] SUB-TOPIK -------------------------------------------------------------
SUB_TOPIC_RULES = {
    "pemilu": ["pemilu", "pilpres", "pilkada", "kpu", "bawaslu", "surat suara", "sirekap", "coblos", "capres", "cawapres", "cawagub", "caleg", "debat", "partai", "pdip", "gerindra", "golkar", "nasdem", "pks", "demokrat", "kpud", "panwaslu", "koalisi", "oposisi", "cawe-cawe", "dinasti", "legislatif"],
    # "kementerian", "pemerintah", "negara" DIHAPUS (terlalu umum, menarik semua teks politik ke 'kebijakan')
    "kebijakan": ["bansos", "subsidi", "bbm", "ikn", "apbn", "apbd", "pajak", "omnibus", "undang-undang", "perpres", "perda", "tarif listrik", "bpjs", "kebijakan pemerintah", "asn", "bumn", "pertamina", "bulog", "beras bansos", "makan siang", "kemensos", "kemenkeu", "kemendagri", "reshuffle", "kabinet", "istana negara", "anggaran"],
    "tokoh": ["jokowi", "prabowo", "gibran", "anies", "ganjar", "megawati", "menteri", "presiden", "pejabat", "mahfud", "gubernur", "bupati", "walikota", "dpr", "mpr", "dprd", "puan", "erick thohir", "bahlil", "kaesang", "ridwan kamil", "ahok", "khofifah", "kades", "sri mulyani", "luhut", "nadiem", "basuki", "tito karnavian", "yasonna", "paspampres"],
    "hukum": ["korupsi", "kpk", "mk", "mahkamah", "polri", "kejaksaan", "tangkap", "ott", "sidang", "vonis", "hakim", "polisi", "tni", "aparat", "kejagung", "jaksa", "kasasi", "mahkamah agung", "yudikatif"],
}
# corona/covid/pandemi TIDAK ditambahkan: confound zaman ditangani lewat strata year_bin.
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
print(pd.crosstab(df.sub_topic, df.label).to_string())
df = df[~df.sub_topic.isin(["umum", "bukan_politik"])].copy()
log("3_filter_politik", df)

# %% [5] PANJANG, DEDUP, GRUP --------------------------------------------------
if LEN_MATCH_TRUNC:
    rng = np.random.default_rng(SEED)
    nw = df.text.str.split().str.len().clip(upper=CFG["MAX_WORDS"])
    pool = {k: nw[(df.label == 1) & (df.sub_topic == k)].to_numpy() for k in df.sub_topic.unique()}
    def _cap(t, lab, k):
        if lab == 1 or len(pool[k]) == 0:
            return tp.cap_sentences(t, CFG["MAX_WORDS"])
        return tp.cap_sentences(t, max(CFG["MIN_WORDS"], int(rng.choice(pool[k]))))
    df["text"] = [_cap(t, l, k) for t, l, k in zip(df.text, df.label, df.sub_topic)]
else:
    df["text"] = df.text.map(lambda t: tp.cap_sentences(t, CFG["MAX_WORDS"]))
df["n_words"] = df.text.str.split().str.len()
df = df[df.n_words >= CFG["MIN_WORDS"]].reset_index(drop=True)
log("4_batas_panjang_sama", df, f"maks {CFG['MAX_WORDS']} kata | LEN_MATCH_TRUNC={LEN_MATCH_TRUNC}")

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
print(f"\nPasangan mirip (cos >= {CFG['GROUP_COS']}): {len(I):,}")
hi = V >= CFG["NEAR_DUP_COS"]
keep = np.ones(n, bool)
cross = hi & (lab[I] != lab[J])
keep[I[cross]] = False; keep[J[cross]] = False
same = hi & (lab[I] == lab[J])
if same.any():
    c = comp(n, I[same], J[same]); first = pd.Series(np.arange(n)).groupby(c).transform("min").to_numpy()
    touched = np.zeros(n, bool); touched[I[same]] = True; touched[J[same]] = True
    keep &= ~(touched & (np.arange(n) != first))
print(f"Near-duplicate: beda-label dibuang={int(cross.sum()):,} pasangan | total baris dibuang={int((~keep).sum()):,}")

old_idx = np.flatnonzero(keep); remap = -np.ones(n, int); remap[old_idx] = np.arange(len(old_idx))
m = keep[I] & keep[J]
df = df.loc[keep].reset_index(drop=True)
g = comp(len(df), remap[I[m]], remap[J[m]])
df["group_id"] = g
sizes = pd.Series(g).value_counts()
print(f"Grup: {len(sizes):,} | terbesar={sizes.iloc[0]} | ukuran>1: {(sizes>1).sum():,}")
log("4c_dedup_near", df)

# %% [6] AUDIT SEBELUM PENYEIMBANGAN -------------------------------------------
def audit(d, title):
    print("\n" + "=" * 78); print(title); print("=" * 78)
    a = d.assign(strict=d.text.map(tp.dup_title_strict), para=d.text.map(tp.dup_title_para),
                 endp=d.text.str.endswith((".", "!", "?")), w=d.text.str.split().str.len()).groupby("label")
    print(pd.DataFrame({"n": a.size(), "judul_ganda_harafiah_%": a.strict.mean()*100, "parafrasa_judul_lead_%": a.para.mean()*100,
                        "berakhir_tanda_%": a.endp.mean()*100, "kata_mean": a.w.mean(), "kata_sd": a.w.std(),
                        "kata_median": a.w.median(), "kata_max": a.w.max()}).round(2).to_string())
    print("\nsub_topik x label:"); print(pd.crosstab(d.sub_topic, d.label).to_string())
    print("\nsumber x label:");   print(pd.crosstab(d.source, d.label).to_string())
    if d.date.notna().any():
        print("\ntahun x label:"); print(pd.crosstab(d.date.dt.year, d.label).to_string())
    print("\nKata pembuka teratas per label:")
    for l in (0, 1):
        print(f"  label {l}:", d[d.label == l].text.str.split().str[0].str.lower().value_counts().head(8).to_dict())

audit(df, "AUDIT SEBELUM PENYEIMBANGAN")

# %% [6a] SIMULASI UKURAN (hanya membaca; memakai df SEBELUM penyeimbangan) ------
df["len_bin"]  = pd.cut(df.n_words, bins=CFG["LEN_BINS"]).astype(str)
yb = pd.cut(df.date.dt.year, CFG["YEAR_BINS"])
df["year_bin"] = yb.astype(str).where(yb.notna(), other=np.nan)       # di luar 2017-2023 -> NaN (tidak punya pasangan)

def match_n(d, keys):
    d = d.dropna(subset=keys)
    c = d.groupby(keys + ["label"], observed=True).size().unstack("label", fill_value=0)
    for l in (0, 1):
        if l not in c.columns: c[l] = 0
    return int(2 * c[[0, 1]].min(axis=1).sum())

print("Ukuran setelah penyeimbangan menurut strata (sebelum split 70/10/10/10):")
for nm, keys in STRATA_PRESETS.items():
    n_ = match_n(df, keys)
    flag = "  <-- dipilih" if nm == STRATA_NAME else ""
    print(f"  {nm:<20} {'+'.join(keys):<32} pasangan={n_:>6,}  train≈{int(n_*0.7):,}{flag}")
print("Ukuran pra-seimbang per label:", df.label.value_counts().to_dict())

# %% [6b] PENYEIMBANGAN TERKENDALI + SPLIT --------------------------------------
if "year_bin" in STRATA:
    nb = len(df); df = df[df.year_bin.notna()].reset_index(drop=True)
    log("5b_dalam_cakupan_2017_2023", df, f"dibuang {nb-len(df):,} di luar 2017-2023 / tanpa tanggal")

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
print(f"Ukuran: {len(df):,} -> {len(bal):,} (kehilangan {(1-len(bal)/len(df))*100:.1f}%)")

sgkf = StratifiedGroupKFold(n_splits=CFG["N_FOLDS"], shuffle=True, random_state=SEED)
fold = np.full(len(bal), -1)
for k, (_, te_idx) in enumerate(sgkf.split(bal, bal.label, bal.group_id)):
    fold[te_idx] = k
edges = np.cumsum([CFG["TRAIN_FOLDS"], CFG["VAL_FOLDS"], CFG["DEVTEST_FOLDS"]])
bal["split"] = np.select([fold < edges[0], fold < edges[1], fold < edges[2]], ["train", "val", "dev_test"], "lockbox")
bal["id"] = [f"POL2-{i+1:06d}" for i in range(len(bal))]
sz = pd.crosstab(bal.split, bal.label).assign(total=lambda x: x.sum(axis=1)); print(sz.to_string())
if sz.loc["train", "total"] < MIN_TRAIN_OK:
    print(f"\n!! PERINGATAN: train {sz.loc['train','total']} < {MIN_TRAIN_OK}. Coba preset lain (lihat [6a]); catat pilihan di PROTOKOL.")
print("\nLOCKBOX disegel: hanya jumlahnya yang dilihat.")

# %% [7] VERIFIKASI KRITERIA ---------------------------------------------------
res = []
dev = bal[bal.split != "lockbox"]
tr_, va_, te_ = (bal[bal.split == s] for s in ("train", "val", "dev_test"))

for s, d in (("train", tr_), ("val", va_), ("dev_test", te_)):
    r  = d.groupby("label").text.apply(lambda x: x.map(tp.dup_title_strict).mean() * 100)
    res.append((f"C1 judul ganda harafiah [{s}]", abs(r[0] - r[1]), 5, abs(r[0] - r[1]) <= 5))
    rp = d.groupby("label").text.apply(lambda x: x.map(tp.dup_title_para).mean() * 100)
    print(f"INFO parafrasa judul-lead [{s}]: fakta={rp[0]:.1f}% hoaks={rp[1]:.1f}%  (bukan kriteria; wajar pada jurnalisme)")
ks = ks_2samp(dev[dev.label == 0].n_words, dev[dev.label == 1].n_words).statistic
res.append(("C2 KS panjang kata", ks, 0.10, ks <= 0.10))
e = dev.groupby("label").text.apply(lambda x: x.str.endswith((".", "!", "?")).mean() * 100)
res.append(("C3 berakhir tanda baca", abs(e[0] - e[1]), 5, abs(e[0] - e[1]) <= 5))

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

first8 = lambda d: d.text.str.split().str[:8].str.join(" ")
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
lr = LogisticRegression(max_iter=2000).fit(vec.fit_transform(first8(tr_)), tr_.label)
acc8 = accuracy_score(te_.label, lr.predict(vec.transform(first8(te_))))
print(f"\nINFO akurasi 8 kata pertama (TF-IDF+LR, dev_test): {acc8*100:.2f}%  <- bila tinggi, gaya/sumber masih membedakan kelas (catat sebagai keterbatasan)")
print("INFO sumber x label (ketimpangan sumber tidak bisa diperbaiki kode):"); print(pd.crosstab(dev.source, dev.label).to_string())

have = [l for l in (0, 1) if dev[dev.label == l].date.notna().any()]
if len(have) == 2:
    yr = pd.crosstab(dev.date.dt.year, dev.label); yr = yr.div(yr.sum(axis=0), axis=1)
    print(f"INFO tumpang-tindih distribusi tahun: {float(np.minimum(yr[0], yr[1]).sum())*100:.1f}%")
yrs = dev.text.str.findall(r"\b(20[12]\d)\b")
ym = pd.DataFrame({l: pd.Series([y for ys in yrs[dev.label == l] for y in set(ys)]).value_counts() / (dev.label == l).sum() * 100 for l in (0, 1)}).fillna(0).round(1).sort_index()
print("\nINFO tahun yang DISEBUT dalam teks (% teks):"); print(ym.to_string())
show_retention()
audit(dev, "AUDIT SETELAH PENYEIMBANGAN (tanpa lockbox)")
ALL_OK = all(ok for *_, ok in res)
print("\nSEMUA KRITERIA LULUS" if ALL_OK else "\nADA KRITERIA GAGAL -> jangan longgarkan ambang; catat sebagai keterbatasan di PROTOKOL.")

# %% [7b] DIAGNOSA TAMBAHAN (hanya dev, bukan lockbox) -------------------------
def frag(t):
    p = re.split(r'(?<=[.!?])\s+', str(t).strip(), maxsplit=1)
    return len(p) > 1 and p[1][:1].islower()
print("Teks dimulai di tengah kalimat (% per label x sumber):")
print(dev.assign(frag=dev.text.map(frag)).groupby(["label", "source"]).frag.mean().mul(100).round(1).to_string())

print("\n15 contoh PARAFRASA judul-lead per sumber (baca: parafrasa wajar atau artefak?):")
for s, gsrc in dev.groupby("source"):
    x = gsrc[gsrc.text.map(tp.dup_title_para)].head(15)
    print(f"\n== {s}: {len(x)} contoh")
    for t in x.text: print("  -", t[:200])

print("\nSisa judul ganda HARAFIAH (harus ~0):")
print(dev.assign(s=dev.text.map(tp.dup_title_strict)).groupby(["label", "source"]).s.sum().to_string())

def loso(d):
    out = {}
    for s in d.source.unique():
        te, tr = d[d.source == s], d[d.source != s]
        if tr.label.nunique() < 2 or len(te) < 30: continue
        v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        mdl = LogisticRegression(max_iter=2000, class_weight="balanced").fit(v.fit_transform(tr.text), tr.label)
        y = te.label.iloc[0]; out[s] = (y, round((mdl.predict(v.transform(te.text)) == y).mean() * 100, 1), len(te))
    return pd.DataFrame(out, index=["label", "recall_%", "n"]).T
print("\nLOSO (TF-IDF+LR balanced; indikator kasar, bukan IndoBERT):"); print(loso(dev).to_string())

# %% [8] SIMPAN + MANIFEST -----------------------------------------------------
bal = bal.drop(columns=["title", "body"], errors="ignore").rename(columns={"title_c": "title", "body_c": "body"})
cols = ["id", "text", "title", "body", "label", "sub_topic", "source", "group_id", "date"]
for sp in ("train", "val", "dev_test"):
    bal[bal.split == sp][cols].to_csv(os.path.join(OUT_DIR, f"{sp}.csv"), index=False, encoding="utf-8-sig")
bal[bal.split != "lockbox"][cols + ["split"]].to_csv(os.path.join(OUT_DIR, "dataset_v2_full.csv"), index=False, encoding="utf-8-sig")
LOCK_DIR = os.path.join(OUT_DIR, "LOCKBOX"); os.makedirs(LOCK_DIR, exist_ok=True)
bal[bal.split == "lockbox"][cols].to_csv(os.path.join(LOCK_DIR, "lockbox.csv"), index=False, encoding="utf-8-sig")
open(os.path.join(LOCK_DIR, "JANGAN_DIBUKA.txt"), "w", encoding="utf-8").write(
    "Set uji tersegel. Dibuka SATU KALI untuk pelaporan akhir, setelah model, ambang, dan analisis dikunci di PROTOKOL.\n"
    "Tidak boleh dipakai untuk tuning, pemilihan model, atau diagnosis. Catat pembukaan di PROTOKOL (tanggal + hash).\n")
pd.DataFrame(LOG).to_csv(os.path.join(OUT_DIR, "audit_log_per_langkah.csv"), index=False)
pd.DataFrame(res, columns=["kriteria", "nilai", "ambang", "lulus"]).to_csv(os.path.join(OUT_DIR, "hasil_kriteria.csv"), index=False)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()

cfg_out = dict(CFG, pipeline_version=tp.PIPELINE_VERSION, strata=STRATA, len_match_trunc=LEN_MATCH_TRUNC,
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
print("Tersimpan di:", os.path.abspath(OUT_DIR)); print(sorted(os.listdir(OUT_DIR)))