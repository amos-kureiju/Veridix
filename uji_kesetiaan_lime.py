"""
uji_kesetiaan_lime.py (v5, final) — Pengujian Kesetiaan LIME (Faithfulness Benchmark).

Ringkasan desain:
  * Skor P(hoaks) = rerata seed dari backend.seed_probs_each (matriks n_teks x n_seed),
    divalidasi ketat (bentuk, finite, 0-1). Tanpa fallback ke pen.nilai().
  * Metadata konfigurasi eksplisit: aturan voting dari pen.rule; seed MODEL dipisah dari
    seed inisialisasi LIME; jumlah sampel dari atribut explainer/payload LIME. Setiap nilai
    menyertakan sumbernya; yang tak terdeteksi ditandai dan bisa diisi via KONFIG_MANUAL.
  * Status kasus: ok | hasil_parsial | baseline_tidak_konsisten | pengukuran_gagal |
    lime_gagal | ditolak. Hanya status "ok" boleh masuk tabel utama laporan.
  * Variasi diskor dalam tiga kelompok (ablasi, kontrol k=1, kontrol k=2) sehingga kegagalan
    satu kelompok tidak menghapus kelompok lain (dasar status hasil_parsial).
  * Proporsi kontrol setara/lebih kuat bersifat deskriptif, bukan p-value.

Pemakaian:
  python uji_kesetiaan_lime.py --probe   # probe adapter + alur sintetis, tanpa model
  python uji_kesetiaan_lime.py           # probe, lalu benchmark nyata
"""
import os
import sys
import re
import json
import math
import time
import random
import platform
from datetime import datetime

import numpy as np
import pandas as pd

SCRIPT_VERSION = "5.1"
N_KONTROL = 10
PANJANG_MIN_KATA = 3
LABEL_MAP = {"BERPOLA HOAKS": 1, "TIDAK BERPOLA HOAKS": 0}  # selain ini -> None
TOLERANSI_BASELINE = 1e-6

# Catatan manual (menimpa deteksi otomatis, tetapi deteksi tetap dicatat & dibandingkan).
# seed_lime = 42 sesuai src/ml/inference.py (baris 120). Hapus jika sudah terdeteksi otomatis.
KONFIG_MANUAL = {"seed_lime": 42}

KORPUS_UJI = [
    {"id": "T01", "label_ground_truth": 1, "kategori": "Klaim Hoaks Logistik Pemilu",
     "teks": ("Beredar kabar viral jutaan surat suara pemilu di gudang logistik Tanjung Priok "
              "sudah dicoblos nomor dua secara curang sebelum hari pencoblosan nasional dimulai.")},
    {"id": "T02", "label_ground_truth": 1, "kategori": "Klaim Hoaks Anggaran Bansos",
     "teks": ("Terbongkar dokumen rahasia menteri keuangan diam-diam menyetujui pemotongan anggaran "
              "bantuan sosial rakyat demi mendanai proyek oligarki dan dinasti politik.")},
    {"id": "T03", "label_ground_truth": 0, "kategori": "Berita Fakta Kebijakan Kemenkeu",
     "teks": ("Kementerian Keuangan memastikan alokasi anggaran perlindungan sosial dan bantuan pangan "
              "tahun 2026 disalurkan secara transparan kepada pemerintah daerah penerima manfaat.")},
    {"id": "T04", "label_ground_truth": 0, "kategori": "Berita Fakta Peresmian Infrastruktur",
     "teks": ("Presiden Joko Widodo didampingi jajaran menteri meresmikan pembukaan jalan tol Trans Jawa "
              "guna memangkas durasi distribusi logistik dan mempercepat pertumbuhan ekonomi daerah.")},
]
# Semua kasus = skenario berlabel peneliti. Isi "sumber_label" (rujukan/prosedur verifikasi)
# sebelum label dipakai sebagai acuan akurasi.
for _k in KORPUS_UJI:
    _k.setdefault("sumber_label", None)


def punya_data(k):
    """True jika kasus sudah sampai tahap ablasi (punya hasil yang bisa diperiksa)."""
    return "ablasi_merah" in k


# ----------------------------------------------------------------------------------
# Utilitas teks
# ----------------------------------------------------------------------------------
def hapus_kata(text, word):
    pola = r"\b" + re.escape(word.strip()) + r"\b"
    baru, n = re.subn(pola, "", text)
    return re.sub(r"\s+", " ", baru).strip(), n


def hapus_daftar(text, words):
    s, total = text, 0
    for w in words:
        s, n = hapus_kata(s, w)
        total += n
    return s, total


def kata_unik(text, dikecualikan):
    seen, out = set(), []
    for w in re.findall(r"\b\w+\b", text):
        if len(w) >= PANJANG_MIN_KATA and w not in dikecualikan and w not in seen:
            seen.add(w)
            out.append(w)
    return out


# ----------------------------------------------------------------------------------
# Adapter skor: seed_probs_each -> (n_teks, n_seed) -> mean(axis=1)
# ----------------------------------------------------------------------------------
class GalatPengukuran(Exception):
    pass


def validasi_matriks(m, n_teks, n_seed):
    try:
        a = np.asarray(m, dtype=float)
    except (ValueError, TypeError) as e:
        raise GalatPengukuran(f"matriks tidak dapat dikonversi ke float: {e}")
    if a.ndim != 2:
        raise GalatPengukuran(f"matriks harus 2 dimensi, diterima ndim={a.ndim}")
    if a.shape != (n_teks, n_seed):
        raise GalatPengukuran(f"bentuk {a.shape} != yang diharapkan {(n_teks, n_seed)}")
    if not np.isfinite(a).all():
        raise GalatPengukuran("matriks mengandung NaN/Inf")
    if (a < 0).any() or (a > 1).any():
        raise GalatPengukuran("nilai di luar rentang [0, 1]")
    return a


class Penilai:
    """Skor P(hoaks) = rerata seed dari backend.seed_probs_each. Tanpa fallback."""

    def __init__(self, backend, n_seed):
        fn = getattr(backend, "seed_probs_each", None)
        if not callable(fn):
            raise RuntimeError("backend tidak memiliki seed_probs_each(texts); benchmark dihentikan "
                               "agar cara penghitungan tidak berubah diam-diam.")
        self.fn, self.n_seed = fn, n_seed
        self.jalur = "backend.seed_probs_each -> mean(axis=1)"
        self.cache, self.per_seed, self.galat = {}, {}, {}

    def skor(self, texts):
        baru = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if baru:
            try:
                a = validasi_matriks(self.fn(list(baru)), len(baru), self.n_seed)
                for t, baris in zip(baru, a):
                    self.cache[t] = float(baris.mean())
                    self.per_seed[t] = [float(x) for x in baris]
            except Exception as e:  # kegagalan pengukuran: dicatat, tidak dialihkan
                for t in baru:
                    self.cache[t] = None
                    self.galat[t] = f"{type(e).__name__}: {e}"
        return [self.cache[t] for t in texts]


# ----------------------------------------------------------------------------------
# Statistik
# ----------------------------------------------------------------------------------
def _valid(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def delta_pt(p, p0):
    return (p - p0) * 100.0 if _valid(p) and _valid(p0) else None


def statistik(nilai):
    v = [x for x in nilai if _valid(x)]
    return {
        "n_valid": len(v), "n_gagal": len(nilai) - len(v),
        "mean": float(np.mean(v)) if v else None,
        "std": float(np.std(v, ddof=1)) if len(v) > 1 else None,
        "min": float(np.min(v)) if v else None,
        "max": float(np.max(v)) if v else None,
    }


def proporsi_setara(delta_ablasi, deltas_kontrol, arah):
    """Proporsi kontrol acak dengan efek (pada arah yang diharapkan) setara/lebih kuat daripada
    ablasi. arah=-1: harapan delta negatif (kata merah); +1: delta positif (kata hijau).
    Deskriptif: 0 dari 10 berarti tidak teramati pada 10 kontrol, bukan bukti signifikansi."""
    v = [x for x in deltas_kontrol if _valid(x)]
    if not _valid(delta_ablasi) or not v:
        return {"n_setara_atau_lebih_kuat": None, "n_kontrol_valid": len(v), "proporsi": None}
    n = sum(1 for x in v if (x * arah) >= (delta_ablasi * arah))
    return {"n_setara_atau_lebih_kuat": n, "n_kontrol_valid": len(v), "proporsi": n / len(v)}


# ----------------------------------------------------------------------------------
# Status kasus
# ----------------------------------------------------------------------------------
def tentukan_status(n_total, n_valid, baseline_konsisten):
    """Prioritas: pengukuran_gagal > baseline_tidak_konsisten > hasil_parsial > ok.
    Daftar `masalah` memuat semua alasan yang berlaku."""
    masalah = []
    if n_total == 0 or n_valid == 0:
        masalah.append("seluruh variasi gagal diukur")
    if not baseline_konsisten:
        masalah.append("baseline berbeda dari engine")
    if 0 < n_valid < n_total:
        masalah.append(f"{n_total - n_valid} dari {n_total} variasi gagal diukur")

    if n_total == 0 or n_valid == 0:
        status = "pengukuran_gagal"
    elif not baseline_konsisten:
        status = "baseline_tidak_konsisten"
    elif n_valid < n_total:
        status = "hasil_parsial"
    else:
        status = "ok"
    return status, masalah


# ----------------------------------------------------------------------------------
# Konfigurasi aktual untuk metadata
# ----------------------------------------------------------------------------------
KATA_KONFIG = ("vote", "sample", "seed", "random_state", "thresh", "num_feat", "kernel", "lime")


def _skalar(v):
    if isinstance(v, (int, float, str, bool)) or v is None:
        return True
    return isinstance(v, (list, tuple)) and len(v) <= 50 and all(isinstance(i, (int, float, str)) for i in v)


def _bisa_json(v):
    return v if (_skalar(v) or isinstance(v, dict)) else repr(v)


def _atribut(o):
    """Atribut instance + atribut level kelas (non-callable, non-dunder)."""
    d = {}
    try:
        d.update({k: v for k, v in vars(type(o)).items()
                  if not k.startswith("_") and not callable(v) and not isinstance(v, (property, staticmethod, classmethod))})
    except TypeError:
        pass
    try:
        d.update(vars(o))
    except TypeError:
        pass
    return d


def deteksi_konfigurasi(pen, modul):
    backend = getattr(pen, "backend", None)
    kandidat = [("pen", pen), ("backend", backend),
                ("explainer", getattr(pen, "explainer", None)),
                ("_explainer", getattr(pen, "_explainer", None)),
                ("backend.explainer", getattr(backend, "explainer", None)),
                ("backend._explainer", getattr(backend, "_explainer", None))]
    out = {}
    for nama, o in kandidat:
        if o is None:
            continue
        for k, v in _atribut(o).items():
            if any(w in k.lower() for w in KATA_KONFIG) and _skalar(v):
                out[f"{nama}.{k}"] = list(v) if isinstance(v, tuple) else v
    for k, v in vars(modul).items():
        if k.isupper() and any(w in k.lower() for w in KATA_KONFIG) and _skalar(v):
            out[f"modul.{k}"] = list(v) if isinstance(v, tuple) else v
    return out


def _datar(diag):
    """Ratakan diagnostik satu tingkat: {a: {b: 1}} -> {a.b: 1}."""
    out = {}
    for k, v in (diag or {}).items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out[f"{k}.{k2}"] = v2
        else:
            out[k] = v
    return out


PREFIKS_EXPLAINER = ("explainer.", "_explainer.", "backend.explainer.", "backend._explainer.")


def _sumber_kunci(k):
    if k.startswith(PREFIKS_EXPLAINER):
        return "atribut explainer"
    if k.startswith("modul."):
        return "konstanta modul"
    if k.startswith(("pen.", "backend.")):
        return "atribut pen/backend"
    return "lainnya"


def _dari_explainer(konfig, kata):
    # Hanya atribut explainer atau yang bernama mengandung "lime".
    # Seed model (pen./backend./modul.SEEDS) sengaja tidak ikut.
    return {k: v for k, v in konfig.items()
            if (k.startswith(PREFIKS_EXPLAINER) or "lime" in k.lower())
            and any(w in k.lower() for w in kata)}


def _dari_diag(diag, kata):
    return {k: v for k, v in _datar(diag).items()
            if any(w in k.lower() for w in kata) and _skalar(v)}


def turunkan_metadata(pen, konfig, seeds, diag):
    def pilih(nama, kata):
        auto = None
        h = _dari_explainer(konfig, kata)
        if h:
            per_kunci = {k: _sumber_kunci(k) for k in h}
            auto = {"nilai": h, "sumber": "; ".join(sorted(set(per_kunci.values()))),
                    "sumber_per_kunci": per_kunci}
        else:
            hd = _dari_diag(diag, kata)
            if hd:
                auto = {"nilai": hd, "sumber": "diagnostik LIME (payload)"}
        if nama in KONFIG_MANUAL:
            cocok = None if auto is None else KONFIG_MANUAL[nama] in list(auto["nilai"].values())
            return {"nilai": KONFIG_MANUAL[nama], "sumber": "KONFIG_MANUAL",
                    "terdeteksi_otomatis": auto, "cocok_dengan_deteksi": cocok}
        return auto or {"nilai": "TIDAK_TERDETEKSI", "sumber": None}

    rule = getattr(pen, "rule", None)
    return {
        "aturan_voting": {"nilai": _bisa_json(rule) if rule is not None else "TIDAK_TERDETEKSI",
                          "sumber": "pen.rule" if rule is not None else None},
        "seed_model": list(seeds),                                    # seed checkpoint IndoBERT
        "seed_lime": pilih("seed_lime", ("seed", "random_state")),    # inisialisasi LIME
        "jumlah_sampel_lime": pilih("jumlah_sampel_lime", ("sample",)),
    }


# ----------------------------------------------------------------------------------
# Satu kasus uji
# ----------------------------------------------------------------------------------
def uji_kasus(pen, penilai, item):
    res = pen.nilai(item["teks"], explain=True, debug=True)
    base = {"id": item["id"], "label_ground_truth": item["label_ground_truth"],
            "sumber_label": item.get("sumber_label"), "kategori": item["kategori"],
            "teks_asli": item["teks"], "status_engine": res.get("status")}

    if not res.get("success"):
        return {**base, "status": "ditolak",
                "alasan": res.get("reason") or res.get("message") or "tidak diketahui"}

    expl = res.get("explanation") or {}
    tokens = expl.get("tokens") or []
    if not expl.get("explanation_available") or not tokens:
        return {**base, "status": "lime_gagal", "label_prediksi": res.get("label"),
                "alasan": expl.get("reason") or expl.get("error") or "penjelasan LIME tidak tersedia"}

    t_dinilai = res["teks_dinilai"]
    p0_engine = float(res["debug"]["mean_prob_hoax"])
    p0 = penilai.skor([t_dinilai])[0]
    if p0 is None:
        return {**base, "status": "pengukuran_gagal", "teks_dinilai": t_dinilai,
                "alasan": f"baseline gagal diukur: {penilai.galat.get(t_dinilai)}"}
    selisih_baseline = abs(p0 - p0_engine)

    diag = expl.get("diagnostik") or expl.get("diagnostik_lime") or {}
    local_r2 = diag.get("local_r2", diag.get("local_r2_score"))

    merah = [t["word"] for t in sorted((t for t in tokens if t.get("weight", 0) > 0),
                                       key=lambda t: -t["weight"])][:2]
    hijau = [t["word"] for t in sorted((t for t in tokens if t.get("weight", 0) < 0),
                                       key=lambda t: t["weight"])][:2]

    rencana = [(f"hapus_single_{w}", "merah", [w]) for w in merah]
    if len(merah) >= 2:
        rencana.append(("hapus_pasangan", "merah", merah))
    rencana += [(f"hapus_single_{w}", "hijau", [w]) for w in hijau]
    if len(hijau) >= 2:
        rencana.append(("hapus_pasangan", "hijau", hijau))
    varian = {(kel, nama): hapus_daftar(t_dinilai, ws) for nama, kel, ws in rencana}

    kandidat = kata_unik(t_dinilai, set(merah + hijau))
    kontrol = {1: [], 2: []}
    for k in (1, 2):
        if len(kandidat) < k:
            continue
        rng = random.Random(f"{item['id']}_k{k}_salt")
        for it in range(N_KONTROL):
            pilih = rng.sample(kandidat, k)
            teks, n = hapus_daftar(t_dinilai, pilih)
            kontrol[k].append((it + 1, pilih, teks, n))

    # Tiga kelompok skor terpisah: kegagalan satu kelompok tidak menghapus kelompok lain.
    penilai.skor([v[0] for v in varian.values()])
    for k in (1, 2):
        penilai.skor([c[2] for c in kontrol[k]])
    P = lambda t: penilai.cache[t]

    kontrol_out, delta_kontrol = {}, {}
    for k, daftar in kontrol.items():
        iters = []
        for it, pilih, teks, n in daftar:
            iters.append({"iterasi": it, "kata_dihapus": pilih, "n_kemunculan_terhapus": n,
                          "p_setelah": P(teks), "p_setelah_per_seed": penilai.per_seed.get(teks),
                          "delta_pt": delta_pt(P(teks), p0), "galat": penilai.galat.get(teks)})
        delta_kontrol[k] = [i["delta_pt"] for i in iters]
        kontrol_out[f"k{k}"] = {"iterasi": iters, "statistik_delta_pt": statistik(delta_kontrol[k])}

    def hasil_ablasi(kel, arah):
        out = {}
        for (k_, nama), (teks, n) in varian.items():
            if k_ != kel:
                continue
            d = delta_pt(P(teks), p0)
            k_pembanding = 2 if nama == "hapus_pasangan" else 1
            out[nama] = {"p_setelah": P(teks), "p_setelah_per_seed": penilai.per_seed.get(teks),
                         "delta_pt": d, "n_kemunculan_terhapus": n,
                         "arah_sesuai": None if d is None else (d * arah) > 0,
                         "kontrol_pembanding": f"k{k_pembanding}",
                         "kontrol_setara": proporsi_setara(d, delta_kontrol.get(k_pembanding, []), arah),
                         "galat": penilai.galat.get(teks)}
        return out

    ab_m, ab_h = hasil_ablasi("merah", -1), hasil_ablasi("hijau", +1)
    nilai_variasi = ([a["p_setelah"] for ab in (ab_m, ab_h) for a in ab.values()]
                     + [i["p_setelah"] for kk in kontrol_out.values() for i in kk["iterasi"]])
    n_total = len(nilai_variasi)
    n_valid = sum(1 for x in nilai_variasi if _valid(x))
    baseline_ok = selisih_baseline <= TOLERANSI_BASELINE
    status, masalah = tentukan_status(n_total, n_valid, baseline_ok)

    return {**base, "status": status, "masalah": masalah,
            "n_variasi_total": n_total, "n_variasi_valid": n_valid,
            "n_variasi_gagal": n_total - n_valid,
            "teks_dinilai": t_dinilai, "p_awal_hoax": p0, "p_awal_engine": p0_engine,
            "p_awal_per_seed": penilai.per_seed.get(t_dinilai),
            "selisih_baseline": selisih_baseline, "baseline_konsisten": baseline_ok,
            "votes_hoax": res.get("votes_hoax"), "label_prediksi": res.get("label"),
            "pred_model": LABEL_MAP.get(res.get("label")),
            "tokens_lime": tokens, "local_r2": local_r2, "diagnostik_lime": diag,
            "num_samples_explanation": expl.get("num_samples", diag.get("num_samples")),
            "kata_merah": merah, "kata_hijau": hijau,
            "ablasi_merah": ab_m, "ablasi_hijau": ab_h,
            "kontrol_acak": kontrol_out, "n_kandidat_kontrol": len(kandidat)}


# ----------------------------------------------------------------------------------
# Probe terisolasi: adapter + status + metadata + alur sintetis (tanpa model)
# ----------------------------------------------------------------------------------
class _BackendTiruan:
    def __init__(self, matriks_fn):
        self.f = matriks_fn

    def seed_probs_each(self, texts):
        return self.f(texts)


def probe_adapter():
    hasil = {}

    p = Penilai(_BackendTiruan(lambda t: [[0.1, 0.5, 0.9]] * len(t)), 3)
    hasil["rerata_3_seed"] = abs(p.skor(["a"])[0] - 0.5) < 1e-12

    panggilan = []
    def f(t):
        panggilan.append(len(t))
        return [[0.2, 0.4, 0.6]] * len(t)
    p = Penilai(_BackendTiruan(f), 3)
    p.skor(["a", "a", "b"]); p.skor(["a", "b"])
    hasil["dedup_cache"] = panggilan == [2]

    kasus_buruk = {
        "nan": lambda t: [[0.1, float("nan"), 0.9]] * len(t),
        "di_luar_rentang": lambda t: [[0.1, 1.2, 0.9]] * len(t),
        "jumlah_seed_salah": lambda t: [[0.1, 0.9]] * len(t),
        "jumlah_baris_salah": lambda t: [[0.1, 0.5, 0.9]],
        "bukan_2d": lambda t: [0.1, 0.5, 0.9],
    }
    for nama, fn in kasus_buruk.items():
        p = Penilai(_BackendTiruan(fn), 3)
        v = p.skor(["a", "b"])
        hasil[f"tolak_{nama}"] = v == [None, None] and "a" in p.galat

    s = statistik([1.0, None, float("nan"), 3.0])
    hasil["statistik_tahan_none_nan"] = s["n_valid"] == 2 and s["n_gagal"] == 2 and s["mean"] == 2.0

    try:
        Penilai(object(), 3)
        hasil["tanpa_fallback"] = False
    except RuntimeError:
        hasil["tanpa_fallback"] = True

    pr = proporsi_setara(-10.0, [-12.0, -3.0, 0.5, -10.0], -1)
    hasil["proporsi_setara"] = pr["n_setara_atau_lebih_kuat"] == 2 and pr["n_kontrol_valid"] == 4

    hasil["status_ok"] = tentukan_status(5, 5, True)[0] == "ok"
    hasil["status_baseline"] = tentukan_status(5, 5, False)[0] == "baseline_tidak_konsisten"
    hasil["status_parsial"] = tentukan_status(5, 3, True)[0] == "hasil_parsial"
    hasil["status_gagal_total"] = tentukan_status(5, 0, True)[0] == "pengukuran_gagal"
    hasil["status_gagal_menang"] = tentukan_status(5, 0, False)[0] == "pengukuran_gagal"

    hasil.update(_probe_alur_sintetis())
    gagal = [k for k, ok in hasil.items() if not ok]
    for k, ok in hasil.items():
        print(f"  [{'LULUS' if ok else 'GAGAL'}] {k}")
    return not gagal


def _probe_alur_inti():
    """Engine & backend tiruan: memeriksa status end-to-end dan metadata."""
    TEKS = "viral curang resmi berita kabar data tersebar"
    TOKENS = [{"word": "viral", "weight": 0.3}, {"word": "curang", "weight": 0.2},
              {"word": "resmi", "weight": -0.2}, {"word": "berita", "weight": -0.1}]
    SEEDS_T = [0.00, 0.01, -0.01]

    def prob(t):
        p = 0.3 + 0.1 * ("viral" in t) + 0.1 * ("curang" in t) - 0.05 * ("resmi" in t)
        return [min(max(p + s, 0), 1) for s in SEEDS_T]

    class Backend:
        def __init__(self, mode):
            self.mode = mode
            self.audit = {}

        def seed_probs_each(self, texts):
            m = [prob(t) for t in texts]
            if self.mode == "k2_nan":      # kelompok kontrol k=2 gagal
                m = [[float("nan")] * 3 if sum(w not in t for w in ("kabar", "data", "tersebar")) >= 2
                     else r for t, r in zip(texts, m)]
                # NaN per baris -> seluruh matriks batch ditolak validasi
            if self.mode == "semua_variasi_nan":
                m = [[float("nan")] * 3 if t != TEKS else r for t, r in zip(texts, m)]
            return m

    class Explainer:
        random_state = 42
        num_samples = 500

    class Pen:
        rule = "2 dari 3 seed"
        def __init__(self, mode="normal", offset=0.0, tolak=False, lime_gagal=False):
            self.backend = Backend(mode)
            self._explainer = Explainer()  # privat, seperti aplikasi
            self.offset, self.tolak, self.lime_gagal = offset, tolak, lime_gagal

        def nilai(self, teks, explain=True, debug=True):
            if self.tolak:
                return {"success": False, "status": "ditolak_gerbang", "reason": "di luar domain"}
            p_engine = float(np.mean(prob(TEKS))) + self.offset
            return {"success": True, "status": "dinilai", "label": "BERPOLA HOAKS",
                    "teks_dinilai": TEKS, "votes_hoax": 2, "debug": {"mean_prob_hoax": p_engine},
                    "explanation": {"explanation_available": not self.lime_gagal,
                                    "tokens": [] if self.lime_gagal else TOKENS,
                                    "reason": "lime error" if self.lime_gagal else None,
                                    "num_samples": 500, "diagnostik": {"local_r2": 0.9}}}

    item = {"id": "S01", "label_ground_truth": 1, "kategori": "sintetis", "teks": TEKS}

    def jalankan(**kw):
        pen = Pen(**kw)
        return uji_kasus(pen, Penilai(pen.backend, 3), item)

    h = {}
    k = jalankan()
    h["alur_ok"] = (k["status"] == "ok" and k["baseline_konsisten"] and k["n_variasi_gagal"] == 0
                    and k["ablasi_merah"]["hapus_pasangan"]["arah_sesuai"] is True
                    and k["ablasi_hijau"]["hapus_pasangan"]["arah_sesuai"] is True)
    h["alur_baseline_tidak_konsisten"] = jalankan(offset=0.01)["status"] == "baseline_tidak_konsisten"
    kp = jalankan(mode="k2_nan")
    h["alur_hasil_parsial"] = kp["status"] == "hasil_parsial" and 0 < kp["n_variasi_gagal"] < kp["n_variasi_total"]
    h["alur_pengukuran_gagal"] = jalankan(mode="semua_variasi_nan")["status"] == "pengukuran_gagal"
    kt = jalankan(tolak=True)
    h["alur_ditolak"] = kt["status"] == "ditolak" and kt["alasan"] == "di luar domain" \
        and kt["status_engine"] == "ditolak_gerbang" and not punya_data(kt)
    h["alur_lime_gagal"] = jalankan(lime_gagal=True)["status"] == "lime_gagal"

    pen = Pen()
    md = turunkan_metadata(pen, deteksi_konfigurasi(pen, sys.modules[__name__]), [42, 123, 999], {})
    h["meta_aturan_dari_pen_rule"] = md["aturan_voting"]["nilai"] == "2 dari 3 seed" \
        and md["aturan_voting"]["sumber"] == "pen.rule"
    h["meta_seed_dipisah"] = md["seed_model"] == [42, 123, 999] \
        and list(md["seed_lime"]["nilai"].values()) == [42] and md["seed_lime"]["sumber"] == "atribut explainer"
    h["meta_jumlah_sampel"] = list(md["jumlah_sampel_lime"]["nilai"].values()) == [500]
    md2 = turunkan_metadata(pen, {}, [42, 123, 999], {"lime": {"num_samples": 300, "random_state": 42}})
    h["meta_dari_payload"] = md2["seed_lime"]["sumber"] == "diagnostik LIME (payload)" \
        and md2["jumlah_sampel_lime"]["sumber"] == "diagnostik LIME (payload)"
    md3 = turunkan_metadata(object(), {}, [1], {})
    h["meta_tak_terdeteksi_ditandai"] = md3["seed_lime"]["nilai"] == "TIDAK_TERDETEKSI" \
        and md3["aturan_voting"]["nilai"] == "TIDAK_TERDETEKSI"
    h["num_samples_per_kasus"] = k["num_samples_explanation"] == 500

    # pemindaian lazy: explainer belum dibuat -> sumber modul; setelah dibuat -> atribut explainer
    import types

    class PenLazy:
        rule = "x"
        backend = Backend("normal")
        _explainer = None

    pl = PenLazy()
    ns = types.SimpleNamespace(LIME_NUM_SAMPLES=200, SEEDS=[42, 123, 999])
    md_a = turunkan_metadata(pl, deteksi_konfigurasi(pl, ns), [42, 123, 999], {})
    h["meta_lazy_sebelum_dibuat"] = md_a["seed_lime"]["nilai"] == "TIDAK_TERDETEKSI"
    h["meta_sumber_konstanta_modul"] = (md_a["jumlah_sampel_lime"]["sumber"] == "konstanta modul"
                                        and list(md_a["jumlah_sampel_lime"]["nilai"].values()) == [200])
    pl._explainer = Explainer()
    md_b = turunkan_metadata(pl, deteksi_konfigurasi(pl, ns), [42, 123, 999], {})
    h["meta_setelah_dibuat"] = (list(md_b["seed_lime"]["nilai"].values()) == [42]
                                and md_b["seed_lime"]["sumber"] == "atribut explainer")
    KONFIG_MANUAL["seed_lime"] = 42
    md_c = turunkan_metadata(pl, deteksi_konfigurasi(pl, ns), [42, 123, 999], {})
    h["meta_manual_dibandingkan"] = (md_c["seed_lime"]["sumber"] == "KONFIG_MANUAL"
                                     and md_c["seed_lime"]["cocok_dengan_deteksi"] is True)
    return h


def _probe_alur_sintetis():
    simpan = dict(KONFIG_MANUAL)  # probe tidak boleh terpengaruh pengaturan manual pengguna
    KONFIG_MANUAL.clear()
    try:
        return _probe_alur_inti()
    finally:
        KONFIG_MANUAL.clear()
        KONFIG_MANUAL.update(simpan)


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
def main():
    print("PROBE (adapter, status, metadata, alur sintetis):")
    if not probe_adapter():
        print("Probe gagal; benchmark dibatalkan.")
        sys.exit(1)
    if "--probe" in sys.argv:
        return

    sys.path.insert(0, os.getcwd())
    import src.ml.inference as modul
    from src.ml.inference import get_predictor, MODEL_NAME, SEEDS

    t_mulai = time.time()
    pen = get_predictor()
    penilai = Penilai(pen.backend, len(SEEDS))
    audit = getattr(pen.backend, "audit", {}) or {}

    print("=" * 95)
    print(f"BENCHMARK KESETIAAN LIME v{SCRIPT_VERSION} | skor: {penilai.jalur} | n_seed={len(SEEDS)}")
    print("=" * 95)

    f = lambda x: "NA" if x is None else f"{x:+.2f}"
    kasus = []
    for item in KORPUS_UJI:
        print(f"\n--- {item['id']} ({item['kategori']}) ---")
        k = uji_kasus(pen, penilai, item)
        kasus.append(k)
        if not punya_data(k):
            print(f"  [{k['status']} | engine={k.get('status_engine')}] {k.get('alasan')}")
            continue
        if k["status"] != "ok":
            print(f"  [STATUS: {k['status']}] " + "; ".join(k.get("masalah", [])))
        print(f"  P(awal)={k['p_awal_hoax']*100:.2f}% | {k['label_prediksi']} "
              f"(pred={k['pred_model']}, label peneliti={k['label_ground_truth']}) | R2={k['local_r2']}")
        for nama, ab in (("Merah", k["ablasi_merah"]), ("Hijau", k["ablasi_hijau"])):
            for n, a in ab.items():
                c = a["kontrol_setara"]
                print(f"  {nama}:{n}: {f(a['delta_pt'])} pt | arah sesuai={a['arah_sesuai']} | "
                      f"kontrol {a['kontrol_pembanding']}: "
                      f"{c['n_setara_atau_lebih_kuat']}/{c['n_kontrol_valid']} setara/lebih kuat")

    durasi = time.time() - t_mulai
    konfig = deteksi_konfigurasi(pen, modul)  # setelah kasus berjalan: explainer lazy sudah dibuat
    diag_contoh = next((k["diagnostik_lime"] for k in kasus if k.get("diagnostik_lime")), {})
    meta_cfg = turunkan_metadata(pen, konfig, SEEDS, diag_contoh)
    for kunci, v in meta_cfg.items():
        if isinstance(v, dict) and v.get("nilai") == "TIDAK_TERDETEKSI":
            print(f"PERINGATAN: {kunci} tidak terdeteksi; isi KONFIG_MANUAL['{kunci}'].")

    metadata = {
        "script_version": SCRIPT_VERSION, "waktu_eksekusi": datetime.now().isoformat(timespec="seconds"),
        "durasi_detik": round(durasi, 2), "python": platform.python_version(),
        "model_name": MODEL_NAME, "n_seed": len(SEEDS),
        "audit_backend": audit, "jalur_skor": penilai.jalur,
        "n_kontrol_per_k": N_KONTROL, "toleransi_baseline": TOLERANSI_BASELINE,
        **meta_cfg, "konfigurasi_terdeteksi": konfig,
        "n_teks_unik_dinilai": len(penilai.cache), "n_pengukuran_gagal": len(penilai.galat),
        "ringkasan_status": {s: sum(1 for k in kasus if k["status"] == s)
                             for s in sorted({k["status"] for k in kasus})},
        "num_samples_teramati": sorted({k["num_samples_explanation"] for k in kasus
                                        if k.get("num_samples_explanation") is not None}),
        "catatan_label": "label_ground_truth = skenario berlabel peneliti; belum acuan independen "
                         "kecuali sumber_label terisi.",
        "catatan_statistik": "kontrol_setara = hitungan deskriptif dari N_KONTROL kontrol acak, "
                             "bukan p-value atau uji signifikansi.",
        "catatan_pelaporan": "Hanya kasus berstatus 'ok' untuk tabel utama; status lain dilaporkan terpisah.",
    }

    cap = datetime.now().strftime("%Y%m%d_%H%M%S")
    path_json, path_csv = f"hasil_kesetiaan_lime_v5_{cap}.json", f"hasil_kesetiaan_lime_v5_{cap}.csv"
    with open(path_json, "w", encoding="utf-8") as fh:
        json.dump({"metadata": metadata, "kasus_uji": kasus}, fh, indent=2, ensure_ascii=False, default=str)

    baris = []
    for k in kasus:
        b = {"id": k["id"], "status": k["status"], "status_engine": k.get("status_engine"),
             "label_peneliti": k["label_ground_truth"]}
        if punya_data(k):
            pm = k["ablasi_merah"].get("hapus_pasangan") or {}
            ph = k["ablasi_hijau"].get("hapus_pasangan") or {}
            k1, k2 = (k["kontrol_acak"].get(x, {}).get("statistik_delta_pt", {}) for x in ("k1", "k2"))
            b.update({
                "masalah": "; ".join(k.get("masalah", [])), "n_variasi_gagal": k["n_variasi_gagal"],
                "pred_model": k["pred_model"], "label_prediksi": k["label_prediksi"],
                "p_awal_hoax": k["p_awal_hoax"], "baseline_konsisten": k["baseline_konsisten"],
                "kata_merah": "|".join(k["kata_merah"]), "delta_pasang_merah_pt": pm.get("delta_pt"),
                "merah_setara_n": (pm.get("kontrol_setara") or {}).get("n_setara_atau_lebih_kuat"),
                "merah_kontrol_n": (pm.get("kontrol_setara") or {}).get("n_kontrol_valid"),
                "kata_hijau": "|".join(k["kata_hijau"]), "delta_pasang_hijau_pt": ph.get("delta_pt"),
                "hijau_setara_n": (ph.get("kontrol_setara") or {}).get("n_setara_atau_lebih_kuat"),
                "hijau_kontrol_n": (ph.get("kontrol_setara") or {}).get("n_kontrol_valid"),
                "kontrol_k1_mean_pt": k1.get("mean"), "kontrol_k2_mean_pt": k2.get("mean"),
                "kontrol_k2_std_pt": k2.get("std"), "local_r2": k["local_r2"],
                "num_samples": k.get("num_samples_explanation"),
            })
        else:
            b["alasan"] = k.get("alasan")
        baris.append(b)
    df = pd.DataFrame(baris)
    df.to_csv(path_csv, index=False)

    print("\n" + "=" * 95)
    print(f"Tersimpan: {path_csv} & {path_json} | {durasi:.1f} dtk | "
          f"{len(penilai.cache)} teks unik | {len(penilai.galat)} pengukuran gagal")
    print(f"Ringkasan status: {metadata['ringkasan_status']}")
    cols = [c for c in ("id", "status", "label_peneliti", "pred_model", "p_awal_hoax",
                        "delta_pasang_merah_pt", "merah_setara_n", "delta_pasang_hijau_pt",
                        "hijau_setara_n", "kontrol_k2_mean_pt") if c in df.columns]
    print(df[cols].round(4).to_string(index=False))
    print("=" * 95)


if __name__ == "__main__":
    main()