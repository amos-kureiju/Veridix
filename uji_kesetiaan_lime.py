"""
uji_kesetiaan_lime.py (v5.4) — Pengujian Kesetiaan LIME (Faithfulness Benchmark).

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
  * Ablasi sah hanya bila seluruh jenis kata target ditemukan dan skor terukur.
    Delta nol setelah penghapusan yang sah tetap merupakan hasil pengukuran.
  * Kontrol memakai kombinasi unik; target menyesuaikan jumlah kombinasi tersedia.
  * Hash skrip/korpus dan versi paket mencatat identitas eksperimen. Timer tahap
    membungkus panggilan yang sama, tanpa mengubah skor maupun konfigurasi model.

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
import hashlib
from importlib import metadata as impmeta
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_VERSION = "5.4"
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
    _k["status_label"] = "bersumber" if _k["sumber_label"] else "skenario_peneliti"


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


def _angka(x):
    """Satu angka finite dari skalar / list / array 1 elemen; selain itu None."""
    try:
        a = np.ravel(np.asarray(x, dtype=float))
    except (ValueError, TypeError):
        return None
    return float(a[0]) if a.size == 1 and math.isfinite(a[0]) else None


KUNCI_LOCAL_PRED = ("local_pred", "local_prediction", "local_pred_hoax")


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
def tentukan_status(n_total, n_valid, baseline_konsisten, n_ablasi_efektif=None, n_kontrol_lengkap=None):
    """Prioritas: pengukuran_gagal > baseline_tidak_konsisten > hasil_parsial > ok.
    Daftar `masalah` memuat semua alasan yang berlaku."""
    masalah = []
    if n_total == 0 or n_valid == 0:
        masalah.append("seluruh variasi gagal diukur")
    if not baseline_konsisten:
        masalah.append("baseline berbeda dari engine")
    if 0 < n_valid < n_total:
        masalah.append(f"{n_total - n_valid} dari {n_total} variasi gagal diukur")
    if n_ablasi_efektif is not None and n_ablasi_efektif == 0:
        masalah.append("tidak ada ablasi sah dengan skor terukur")
    if n_kontrol_lengkap is False:
        masalah.append("kontrol pembanding tidak lengkap atau tidak tersedia")

    if n_total == 0 or n_valid == 0:
        status = "pengukuran_gagal"
    elif not baseline_konsisten:
        status = "baseline_tidak_konsisten"
    elif (n_valid < n_total
          or n_ablasi_efektif == 0
          or n_kontrol_lengkap is False):
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
    t_nilai = time.perf_counter()
    res = pen.nilai(item["teks"], explain=True, debug=True)
    waktu_nilai = time.perf_counter() - t_nilai
    base = {"id": item["id"], "label_ground_truth": item["label_ground_truth"],
            "sumber_label": item.get("sumber_label"), "status_label": item.get("status_label"),
            "kategori": item["kategori"],
            "teks_asli": item["teks"], "status_engine": res.get("status"),
            "waktu_nilai_dtk": round(waktu_nilai, 6),
            "waktu_baseline_dtk": None, "waktu_variasi_dtk": None}

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
    t_baseline = time.perf_counter()
    p0 = penilai.skor([t_dinilai])[0]
    base["waktu_baseline_dtk"] = round(time.perf_counter() - t_baseline, 6)
    if p0 is None:
        return {**base, "status": "pengukuran_gagal", "teks_dinilai": t_dinilai,
                "alasan": f"baseline gagal diukur: {penilai.galat.get(t_dinilai)}"}
    selisih_baseline = abs(p0 - p0_engine)

    diag = expl.get("diagnostik") or expl.get("diagnostik_lime") or {}
    local_r2 = diag.get("local_r2", diag.get("local_r2_score"))
    # Kecocokan model linear lokal pada TEKS ASLI: |prediksi lokal - skor asli (rerata 3 seed)|.
    # Hanya bermakna jika kelas yang dijelaskan LIME = kelas hoaks (verifikasi di inference.py).
    local_pred = next((v for v in (_angka(diag.get(k_)) for k_ in KUNCI_LOCAL_PRED) if v is not None), None)
    abs_local_error = None if local_pred is None else abs(local_pred - p0)

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
    kata_target = {(kel, nama): ws for nama, kel, ws in rencana}
    varian = {(kel, nama): hapus_daftar(t_dinilai, ws) for nama, kel, ws in rencana}

    kandidat = kata_unik(t_dinilai, set(merah + hijau))
    kontrol = {1: [], 2: []}
    for k in (1, 2):
        if len(kandidat) < k:
            continue
        rng = random.Random(f"{item['id']}_k{k}_salt")
        semua = list(combinations(kandidat, k))
        rng.shuffle(semua)
        for it, pilih in enumerate(semua[:N_KONTROL]):   # tanpa pengulangan kombinasi
            teks, n = hapus_daftar(t_dinilai, list(pilih))
            kontrol[k].append((it + 1, list(pilih), teks, n))

    # Tiga kelompok skor terpisah: kegagalan satu kelompok tidak menghapus kelompok lain.
    t_variasi = time.perf_counter()
    penilai.skor([v[0] for v in varian.values()])
    for k in (1, 2):
        penilai.skor([c[2] for c in kontrol[k]])
    base["waktu_variasi_dtk"] = round(time.perf_counter() - t_variasi, 6)
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
            ws = kata_target[(kel, nama)]
            tidak_ditemukan = [w for w in ws if hapus_kata(t_dinilai, w)[1] == 0]
            alasan = []
            if tidak_ditemukan:
                alasan.append("kata target tidak ditemukan: " + ", ".join(tidak_ditemukan))
            if len(set(ws)) != len(ws):
                alasan.append("jenis kata target berulang")
            if n == 0:
                alasan.append("tidak ada kemunculan kata yang terhapus")
            if d is None:
                alasan.append("skor ablasi tidak berhasil diukur")
            sah = not alasan
            k_pembanding = 2 if nama == "hapus_pasangan" else 1
            out[nama] = {"p_setelah": P(teks), "p_setelah_per_seed": penilai.per_seed.get(teks),
                         "kata_target": ws, "kata_tidak_ditemukan": tidak_ditemukan,
                         "ablasi_valid": sah, "alasan_tidak_sah": "; ".join(alasan) or None,
                         "delta_pt": d if sah else None, "n_kemunculan_terhapus": n,
                         "arah_sesuai": (d * arah) > 0 if sah else None,
                         "kontrol_pembanding": f"k{k_pembanding}",
                         "kontrol_setara": proporsi_setara(d if sah else None, delta_kontrol.get(k_pembanding, []), arah),
                         "galat": penilai.galat.get(teks)}
        return out

    ab_m, ab_h = hasil_ablasi("merah", -1), hasil_ablasi("hijau", +1)
    nilai_variasi = ([a["p_setelah"] for ab in (ab_m, ab_h) for a in ab.values()]
                     + [i["p_setelah"] for kk in kontrol_out.values() for i in kk["iterasi"]])
    n_total = len(nilai_variasi)
    n_valid = sum(1 for x in nilai_variasi if _valid(x))
    baseline_ok = selisih_baseline <= TOLERANSI_BASELINE
    semua_ablasi = [a for ab in (ab_m, ab_h) for a in ab.values()]
    ablasi_tidak_sah = [{"kelompok": kel, "nama": nama, "alasan": a["alasan_tidak_sah"]}
                       for kel, ab in (("merah", ab_m), ("hijau", ab_h))
                       for nama, a in ab.items() if not a["ablasi_valid"]]
    ablasi_efektif = [a for a in semua_ablasi if a["ablasi_valid"]]
    kontrol_rencana = {}
    for k in (1, 2):
        diperlukan = bool((k == 1 and (merah or hijau)) or (k == 2 and (len(merah) >= 2 or len(hijau) >= 2)))
        tersedia = math.comb(len(kandidat), k)
        target = min(N_KONTROL, tersedia) if diperlukan else 0
        r = {
            "diperlukan": diperlukan, "diminta": N_KONTROL if diperlukan else 0,
            "kombinasi_tersedia": tersedia, "target": target,
            "dihasilkan": len(kontrol[k]),
            "n_mask_unik": len({tuple(sorted(c[1])) for c in kontrol[k]}),
            "terukur": kontrol_out.get(f"k{k}", {}).get("statistik_delta_pt", {}).get("n_valid", 0),
            "terbatas": diperlukan and tersedia < N_KONTROL,
        }
        r["lengkap"] = (not diperlukan or
                        (target > 0 and r["dihasilkan"] == r["n_mask_unik"] == r["terukur"] == target))
        kontrol_rencana[f"k{k}"] = r
    kontrol_lengkap = all(
        r["lengkap"] for r in kontrol_rencana.values()
    )
    status, masalah = tentukan_status(n_total, n_valid, baseline_ok,
                                      n_ablasi_efektif=len(ablasi_efektif),
                                      n_kontrol_lengkap=kontrol_lengkap)
    if ablasi_tidak_sah:
        masalah.append(f"{len(ablasi_tidak_sah)} ablasi tidak sah; lihat rincian per ablasi")
        if status == "ok":
            status = "hasil_parsial"

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
            "local_pred": local_pred, "abs_local_error": abs_local_error,
            "kata_merah": merah, "kata_hijau": hijau,
            "ablasi_merah": ab_m, "ablasi_hijau": ab_h,
            "n_ablasi_total": len(semua_ablasi), "n_ablasi_valid": len(ablasi_efektif),
            "n_ablasi_tidak_sah": len(ablasi_tidak_sah), "ablasi_tidak_sah": ablasi_tidak_sah,
            "rencana_kontrol": kontrol_rencana, "kontrol_lengkap": kontrol_lengkap,
            "kontrol_terbatas": any(r["terbatas"] for r in kontrol_rencana.values()),
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
    hasil["status_kontrol_lengkap_ok"] = tentukan_status(5, 5, True, n_ablasi_efektif=2, n_kontrol_lengkap=True)[0] == "ok"
    hasil["status_tanpa_kontrol_info_ok"] = tentukan_status(5, 5, True)[0] == "ok"
    hasil["kapitalisasi_hapus_persis"] = hapus_kata("Viral viral VIRAL viral", "viral") == ("Viral VIRAL", 2)
    hasil["kapitalisasi_tak_cocok"] = hapus_kata("viral", "Viral") == ("viral", 0)
    hasil["kapitalisasi_kontrol_terpisah"] = kata_unik("Viral viral VIRAL", set()) == ["Viral", "viral", "VIRAL"]
    hasil["status_tanpa_ablasi_efektif"] = tentukan_status(5, 5, True, n_ablasi_efektif=0)[0] == "hasil_parsial"
    hasil["status_kontrol_tak_lengkap"] = tentukan_status(5, 5, True, n_kontrol_lengkap=False)[0] == "hasil_parsial"

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
        def __init__(self, mode="normal", offset=0.0, tolak=False, lime_gagal=False, tanpa_local_pred=False,
                     teks=TEKS, tokens=None):
            self.backend = Backend(mode)
            self._explainer = Explainer()  # privat, seperti aplikasi
            self.offset, self.tolak, self.lime_gagal = offset, tolak, lime_gagal
            self.tanpa_lp = tanpa_local_pred
            self.teks, self.tokens = teks, TOKENS if tokens is None else tokens

        def nilai(self, teks, explain=True, debug=True):
            if self.tolak:
                return {"success": False, "status": "ditolak_gerbang", "reason": "di luar domain"}
            p_engine = float(np.mean(prob(self.teks))) + self.offset
            return {"success": True, "status": "dinilai", "label": "BERPOLA HOAKS",
                    "teks_dinilai": self.teks, "votes_hoax": 2, "debug": {"mean_prob_hoax": p_engine},
                    "explanation": {"explanation_available": not self.lime_gagal,
                                    "tokens": [] if self.lime_gagal else self.tokens,
                                    "reason": "lime error" if self.lime_gagal else None,
                                    "num_samples": 500,
                                    "diagnostik": ({"local_r2": 0.9} if self.tanpa_lp
                                                   else {"local_r2": 0.9, "local_pred": 0.50})}}

    item = {"id": "S01", "label_ground_truth": 1, "kategori": "sintetis", "teks": TEKS}

    def jalankan(**kw):
        pen = Pen(**kw)
        return uji_kasus(pen, Penilai(pen.backend, 3), {**item, "teks": pen.teks})

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
    h["waktu_tahap_terukur"] = all(_valid(k[n]) and k[n] >= 0 for n in
        ("waktu_nilai_dtk", "waktu_baseline_dtk", "waktu_variasi_dtk"))
    h["waktu_tahap_penolakan_tidak_dibuat_nol"] = (_valid(kt["waktu_nilai_dtk"])
        and kt["waktu_baseline_dtk"] is None and kt["waktu_variasi_dtk"] is None)
    gagal_lime = jalankan(lime_gagal=True)
    h["waktu_tahap_lime_gagal_tersimpan"] = (_valid(gagal_lime["waktu_nilai_dtk"])
        and gagal_lime["waktu_baseline_dtk"] is None and gagal_lime["waktu_variasi_dtk"] is None)

    kosong = jalankan(tokens=[{"word": "viral", "weight": 0.0}])
    h["alur_tanpa_ablasi_parsial"] = kosong["status"] == "hasil_parsial" and kosong["n_ablasi_valid"] == 0
    hilang = jalankan(tokens=[{"word": "tidak_ada", "weight": 0.3}])
    a = hilang["ablasi_merah"]["hapus_single_tidak_ada"]
    h["ablasi_kata_hilang_tidak_dinilai"] = (hilang["status"] == "hasil_parsial"
        and not a["ablasi_valid"] and a["delta_pt"] is None and a["arah_sesuai"] is None
        and a["kontrol_setara"]["proporsi"] is None)
    sebagian = jalankan(tokens=[{"word": "viral", "weight": 0.3}, {"word": "tidak_ada", "weight": 0.2}])
    pasangan = sebagian["ablasi_merah"]["hapus_pasangan"]
    h["pasangan_target_tidak_lengkap"] = (sebagian["status"] == "hasil_parsial"
        and pasangan["n_kemunculan_terhapus"] == 1 and not pasangan["ablasi_valid"]
        and pasangan["kata_tidak_ditemukan"] == ["tidak_ada"] and pasangan["delta_pt"] is None
        and pasangan["kontrol_setara"]["proporsi"] is None and sebagian["n_ablasi_tidak_sah"] == 2)
    nol = jalankan(tokens=[{"word": "berita", "weight": 0.1}])
    a = nol["ablasi_merah"]["hapus_single_berita"]
    h["delta_nol_tetap_sah"] = (nol["status"] == "ok" and a["ablasi_valid"]
        and a["delta_pt"] == 0.0 and a["arah_sesuai"] is False and not nol["masalah"])
    kecil = jalankan(teks="viral kabar", tokens=[{"word": "viral", "weight": 0.3}])
    r = kecil["rencana_kontrol"]["k1"]
    h["kontrol_target_sesuai_ketersediaan"] = (kecil["status"] == "ok" and kecil["kontrol_terbatas"]
        and r["diminta"] == 10 and r["target"] == r["dihasilkan"] == r["terukur"] == r["n_mask_unik"] == 1)
    kurang = jalankan(teks="viral curang kabar", tokens=TOKENS[:2])
    h["kontrol_pasangan_tidak_tersedia"] = (kurang["status"] == "hasil_parsial"
        and not kurang["kontrol_lengkap"] and kurang["rencana_kontrol"]["k2"]["target"] == 0
        and kurang["n_ablasi_valid"] == 3)
    h["kontrol_kombinasi_unik"] = all(r["dihasilkan"] == r["n_mask_unik"] for r in k["rencana_kontrol"].values())
    h["ringkasan_ablasi_dan_kontrol_tersimpan"] = (k["n_ablasi_total"] == k["n_ablasi_valid"] == 6
        and k["n_ablasi_tidak_sah"] == 0 and k["kontrol_lengkap"] and not k["masalah"])
    h["hasil_json_tanpa_nan"] = bool(json.dumps([k, hilang, sebagian, nol, kecil, kurang], allow_nan=False))

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
    h["abs_local_error_dihitung"] = (k["abs_local_error"] is not None
                                     and abs(k["abs_local_error"] - 0.05) < 1e-9)
    h["abs_local_error_tanpa_payload"] = jalankan(tanpa_local_pred=True)["abs_local_error"] is None
    h["angka_unwrap"] = (_angka([0.4]) == 0.4 and _angka(None) is None
                         and _angka(float("nan")) is None and _angka({"a": 1}) is None)

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


def versi_paket(nama):
    try:
        return impmeta.version(nama)
    except impmeta.PackageNotFoundError:
        return None


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


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

    t_mulai = time.perf_counter()
    # Snapshot identitas sebelum pekerjaan panjang, agar edit berikutnya tidak
    # mengubah identitas sumber yang dicatat pada akhir benchmark.
    sha_skrip = sha256_bytes(Path(__file__).read_bytes())
    sha_korpus = sha256_bytes(json.dumps(KORPUS_UJI, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    t_awal_muat = time.perf_counter()
    pen = get_predictor()
    t_muat = time.perf_counter() - t_awal_muat
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
        ale = k["abs_local_error"]
        ale_s = "NA" if ale is None else f"{ale:.4f}"
        print(f"  P(awal)={k['p_awal_hoax']*100:.2f}% | {k['label_prediksi']} "
              f"(pred={k['pred_model']}, label peneliti={k['label_ground_truth']}, "
              f"status label={k['status_label']}) | R2={k['local_r2']} | |lokal-asli|={ale_s}")
        for nama, ab in (("Merah", k["ablasi_merah"]), ("Hijau", k["ablasi_hijau"])):
            for n, a in ab.items():
                c = a["kontrol_setara"]
                print(f"  {nama}:{n}: {f(a['delta_pt'])} pt | arah sesuai={a['arah_sesuai']} | "
                      f"kontrol {a['kontrol_pembanding']}: "
                      f"{c['n_setara_atau_lebih_kuat']}/{c['n_kontrol_valid']} setara/lebih kuat")

    durasi = time.perf_counter() - t_mulai
    konfig = deteksi_konfigurasi(pen, modul)  # setelah kasus berjalan: explainer lazy sudah dibuat
    diag_contoh = next((k["diagnostik_lime"] for k in kasus if k.get("diagnostik_lime")), {})
    meta_cfg = turunkan_metadata(pen, konfig, SEEDS, diag_contoh)
    for kunci, v in meta_cfg.items():
        if isinstance(v, dict) and v.get("nilai") == "TIDAK_TERDETEKSI":
            print(f"PERINGATAN: {kunci} tidak terdeteksi; isi KONFIG_MANUAL['{kunci}'].")

    if not all(it.get("sumber_label") for it in KORPUS_UJI):
        print("PERINGATAN: sumber_label belum lengkap; label = skenario peneliti, bukan acuan independen.")
    if not any(k.get("local_pred") is not None for k in kasus):
        print("PERINGATAN: payload LIME tidak memuat local_pred; abs_local_error tidak dapat dihitung.")

    metadata = {
        "sha256_skrip": sha_skrip,
        "sha256_korpus": sha_korpus,
        "versi_paket": {n: versi_paket(n) for n in
                        ("numpy", "pandas", "lime", "scikit-learn", "torch", "transformers")},
        "perangkat": str(getattr(pen.backend, "device", "tidak diketahui")),
        "waktu_muat_model_dtk": round(t_muat, 6),
        "urutan_kasus": [it["id"] for it in KORPUS_UJI],
        "script_version": SCRIPT_VERSION, "waktu_eksekusi": datetime.now().isoformat(timespec="seconds"),
        "durasi_detik": round(durasi, 2), "python": platform.python_version(),
        "model_name": MODEL_NAME, "n_seed": len(SEEDS),
        "audit_backend": audit, "jalur_skor": penilai.jalur,
        "n_kontrol_per_k": N_KONTROL, "toleransi_baseline": TOLERANSI_BASELINE,
        "metode_kontrol": "kombinasi unik tanpa pengembalian; target=min(N_KONTROL, kombinasi tersedia)",
        **meta_cfg, "konfigurasi_terdeteksi": konfig,
        "n_teks_unik_dinilai": len(penilai.cache), "n_pengukuran_gagal": len(penilai.galat),
        "ringkasan_status": {s: sum(1 for k in kasus if k["status"] == s)
                             for s in sorted({k["status"] for k in kasus})},
        "num_samples_teramati": sorted({k["num_samples_explanation"] for k in kasus
                                        if k.get("num_samples_explanation") is not None}),
        "n_local_pred_tersedia": sum(1 for k in kasus if k.get("local_pred") is not None),
        "n_kasus_uji": len(KORPUS_UJI),
        "n_label_bersumber": sum(1 for it in KORPUS_UJI if it.get("sumber_label")),
        "catatan_label": "label_ground_truth = skenario berlabel peneliti; belum acuan independen "
                         "kecuali sumber_label terisi.",
        "catatan_statistik": "kontrol_setara = hitungan deskriptif dari kontrol yang berhasil diukur "
                             "(maksimal N_KONTROL per k), bukan p-value atau uji signifikansi.",
        "catatan_ablasi": "Ablasi sah bila seluruh jenis kata target terhapus dan skor terukur. "
                          "Delta nol yang sah tetap dilaporkan; ablasi tidak sah memiliki delta null.",
        "catatan_waktu": "waktu_nilai_dtk mencakup validasi, klasifikasi, dan LIME; bukan LIME murni. "
                         "waktu_baseline_dtk mengukur verifikasi skor asli, waktu_variasi_dtk "
                         "mengukur pemberian skor ablasi/kontrol termasuk cache. Tahap yang belum "
                         "dijalankan bernilai null. durasi_detik mencakup persiapan dan benchmark, "
                         "tanpa probe dan ekspor hasil.",
        "catatan_pelaporan": "Hanya kasus berstatus 'ok' untuk tabel utama; status lain dilaporkan terpisah.",
    }

    cap = datetime.now().strftime("%Y%m%d_%H%M%S")
    path_json, path_csv = f"hasil_kesetiaan_lime_v5_{cap}.json", f"hasil_kesetiaan_lime_v5_{cap}.csv"
    with open(path_json, "w", encoding="utf-8") as fh:
        json.dump({"metadata": metadata, "kasus_uji": kasus}, fh, indent=2, ensure_ascii=False, default=str)

    baris = []
    for k in kasus:
        b = {"id": k["id"], "status": k["status"], "status_engine": k.get("status_engine"),
             "label_peneliti": k["label_ground_truth"], "status_label": k.get("status_label"),
             "waktu_nilai_dtk": k.get("waktu_nilai_dtk"),
             "waktu_baseline_dtk": k.get("waktu_baseline_dtk"),
             "waktu_variasi_dtk": k.get("waktu_variasi_dtk")}
        if punya_data(k):
            pm = k["ablasi_merah"].get("hapus_pasangan") or {}
            ph = k["ablasi_hijau"].get("hapus_pasangan") or {}
            k1, k2 = (k["kontrol_acak"].get(x, {}).get("statistik_delta_pt", {}) for x in ("k1", "k2"))
            b.update({
                "masalah": "; ".join(k.get("masalah", [])), "n_variasi_gagal": k["n_variasi_gagal"],
                "n_ablasi_total": k["n_ablasi_total"], "n_ablasi_valid": k["n_ablasi_valid"],
                "n_ablasi_tidak_sah": k["n_ablasi_tidak_sah"],
                "kontrol_lengkap": k["kontrol_lengkap"], "kontrol_terbatas": k["kontrol_terbatas"],
                "rincian_ablasi_tidak_sah": json.dumps(k["ablasi_tidak_sah"], ensure_ascii=False),
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
                "local_pred": k.get("local_pred"), "abs_local_error": k.get("abs_local_error"),
            })
            for nama, rencana in k["rencana_kontrol"].items():
                for kolom in ("diperlukan", "diminta", "kombinasi_tersedia", "target", "dihasilkan",
                              "n_mask_unik", "terukur", "terbatas", "lengkap"):
                    b[f"kontrol_{nama}_{kolom}"] = rencana[kolom]
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
