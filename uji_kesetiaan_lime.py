"""
uji_kesetiaan_lime.py (v4) — Pengujian Kesetiaan LIME (Faithfulness Benchmark).

Perubahan dari v3:
  * Adapter hanya memakai kontrak backend aplikasi: seed_probs_each(texts) ->
    matriks (n_teks, n_seed), lalu mean(axis=1). TANPA fallback ke pen.nilai().
  * Validasi ketat: bentuk matriks, jumlah seed, nilai finite, rentang [0, 1].
    Kegagalan dicatat sebagai kegagalan pengukuran (skor None + alasan).
  * Baseline P(awal) dihitung lewat jalur yang sama dengan variasi, lalu
    dicocokkan dengan debug.mean_prob_hoax dari engine (cek integritas).
  * Flag LIME dibaca dari explanation.explanation_available; alasan penolakan
    dari res["reason"]; status engine asli dipertahankan.
  * Proporsi kontrol setara/lebih kuat dilaporkan per ablasi terhadap kontrol
    berukuran sama (tunggal -> k=1, pasangan -> k=2), disertai n; bukan p-value.
  * Metadata konfigurasi diambil dari objek/modul aktual (bukan placeholder);
    yang tak terdeteksi ditandai eksplisit dan bisa diisi lewat KONFIG_MANUAL.
  * Probe adapter terisolasi: `python uji_kesetiaan_lime.py --probe`
    (juga dijalankan otomatis sebelum benchmark).
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

SCRIPT_VERSION = "4.0"
N_KONTROL = 10
PANJANG_MIN_KATA = 3
LABEL_MAP = {"BERPOLA HOAKS": 1, "TIDAK BERPOLA HOAKS": 0}  # selain ini -> None
TOLERANSI_BASELINE = 1e-6

# Isi jika konfigurasi tidak terdeteksi otomatis, mis.
# {"aturan_voting": "...", "jumlah_sampel_lime": 500, "seed_explainer": 42}
KONFIG_MANUAL = {}

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
# Status label: semua kasus di atas adalah skenario berlabel peneliti. Isi "sumber_label"
# per kasus (rujukan/prosedur verifikasi) sebelum label dipakai sebagai acuan akurasi.
for _k in KORPUS_UJI:
    _k.setdefault("sumber_label", None)

def punya_data(k):
    """True jika kasus punya hasil ablasi (status ok/parsial/baseline_tidak_konsisten/
    pengukuran_gagal setelah variasi dihitung). False untuk ditolak/lime_gagal/baseline gagal."""
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
# Adapter skor: kontrak seed_probs_each -> (n_teks, n_seed) -> mean(axis=1)
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
            raise RuntimeError("backend tidak memiliki seed_probs_each(texts); "
                               "benchmark dihentikan agar cara penghitungan tidak berubah diam-diam.")
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
# Deteksi konfigurasi aktual untuk metadata
# ----------------------------------------------------------------------------------
KATA_KONFIG = ("vote", "sample", "seed", "thresh", "num_feat", "kernel")


def _skalar(v):
    if isinstance(v, (int, float, str, bool)) or v is None:
        return True
    return isinstance(v, (list, tuple)) and len(v) <= 50 and all(isinstance(i, (int, float, str)) for i in v)


def deteksi_konfigurasi(pen, modul):
    kandidat = [("pen", pen), ("backend", getattr(pen, "backend", None)),
                ("explainer", getattr(pen, "explainer", None)),
                ("backend.explainer", getattr(getattr(pen, "backend", None), "explainer", None))]
    out = {}
    for nama, o in kandidat:
        if o is None:
            continue
        try:
            d = vars(o)
        except TypeError:
            continue
        for k, v in d.items():
            if any(w in k.lower() for w in KATA_KONFIG) and _skalar(v):
                out[f"{nama}.{k}"] = list(v) if isinstance(v, tuple) else v
    for k, v in vars(modul).items():
        if k.isupper() and any(w in k.lower() for w in KATA_KONFIG) and _skalar(v):
            out[f"modul.{k}"] = list(v) if isinstance(v, tuple) else v
    return out


def turunkan_metadata(konfig):
    def cari(kata):
        return {k: v for k, v in konfig.items() if kata in k.lower()} or "TIDAK_TERDETEKSI"
    meta = {"aturan_voting": cari("vote"), "jumlah_sampel_lime": cari("sample"),
            "seed_explainer": cari("seed")}
    meta.update({k: v for k, v in KONFIG_MANUAL.items()})  # manual menimpa deteksi
    return meta


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

    penilai.skor([v[0] for v in varian.values()] + [c[2] for k in kontrol for c in kontrol[k]])
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

    return {**base, "status": "ok",
            "teks_dinilai": t_dinilai, "p_awal_hoax": p0, "p_awal_engine": p0_engine,
            "p_awal_per_seed": penilai.per_seed.get(t_dinilai),
            "selisih_baseline": selisih_baseline,
            "baseline_konsisten": selisih_baseline <= TOLERANSI_BASELINE,
            "votes_hoax": res.get("votes_hoax"), "label_prediksi": res.get("label"),
            "pred_model": LABEL_MAP.get(res.get("label")),
            "tokens_lime": tokens, "local_r2": local_r2, "diagnostik_lime": diag,
            "kata_merah": merah, "kata_hijau": hijau,
            "ablasi_merah": hasil_ablasi("merah", -1), "ablasi_hijau": hasil_ablasi("hijau", +1),
            "kontrol_acak": kontrol_out, "n_kandidat_kontrol": len(kandidat)}


# ----------------------------------------------------------------------------------
# Probe adapter terisolasi (backend tiruan, tanpa model)
# ----------------------------------------------------------------------------------
class _BackendTiruan:
    def __init__(self, matriks_fn):
        self.f = matriks_fn

    def seed_probs_each(self, texts):
        return self.f(texts)


def probe_adapter():
    hasil = {}

    # 1. Rerata 3 seed, bukan seed terakhir
    p = Penilai(_BackendTiruan(lambda t: [[0.1, 0.5, 0.9]] * len(t)), 3)
    v = p.skor(["a"])[0]
    hasil["rerata_3_seed"] = abs(v - 0.5) < 1e-12

    # 2. Cache/dedup: backend dipanggil sekali untuk teks identik
    panggilan = []
    def f(t):
        panggilan.append(len(t))
        return [[0.2, 0.4, 0.6]] * len(t)
    p = Penilai(_BackendTiruan(f), 3)
    p.skor(["a", "a", "b"]); p.skor(["a", "b"])
    hasil["dedup_cache"] = panggilan == [2]

    # 3-6. Validasi harus menolak (skor None + galat tercatat)
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

    # 7. Statistik mengabaikan None/NaN
    s = statistik([1.0, None, float("nan"), 3.0])
    hasil["statistik_tahan_none_nan"] = s["n_valid"] == 2 and s["n_gagal"] == 2 and s["mean"] == 2.0

    # 8. Backend tanpa seed_probs_each -> berhenti, tidak fallback
    try:
        Penilai(object(), 3)
        hasil["tanpa_fallback"] = False
    except RuntimeError:
        hasil["tanpa_fallback"] = True

    # 9. Proporsi setara
    pr = proporsi_setara(-10.0, [-12.0, -3.0, 0.5, -10.0], -1)
    hasil["proporsi_setara"] = pr["n_setara_atau_lebih_kuat"] == 2 and pr["n_kontrol_valid"] == 4

    gagal = [k for k, ok in hasil.items() if not ok]
    for k, ok in hasil.items():
        print(f"  [{'LULUS' if ok else 'GAGAL'}] {k}")
    return not gagal


# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------
def main():
    print("PROBE ADAPTER (backend tiruan):")
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
    konfig = deteksi_konfigurasi(pen, modul)
    meta_cfg = turunkan_metadata(konfig)
    for k, v in meta_cfg.items():
        if v == "TIDAK_TERDETEKSI":
            print(f"PERINGATAN: {k} tidak terdeteksi; isi KONFIG_MANUAL['{k}'].")

    print("=" * 95)
    print(f"BENCHMARK KESETIAAN LIME v{SCRIPT_VERSION} | skor: {penilai.jalur} | n_seed={len(SEEDS)}")
    print("=" * 95)

    f = lambda x: "NA" if x is None else f"{x:+.2f}"
    kasus = []
    for item in KORPUS_UJI:
        print(f"\n--- {item['id']} ({item['kategori']}) ---")
        k = uji_kasus(pen, penilai, item)
        kasus.append(k)
        if k["status"] != "ok":
            print(f"  [{k['status']} | engine={k.get('status_engine')}] {k.get('alasan')}")
            continue
        if not k["baseline_konsisten"]:
            print(f"  PERINGATAN: baseline berbeda dari engine (selisih {k['selisih_baseline']:.2e})")
        pm, ph = k["ablasi_merah"].get("hapus_pasangan"), k["ablasi_hijau"].get("hapus_pasangan")
        print(f"  P(awal)={k['p_awal_hoax']*100:.2f}% | {k['label_prediksi']} "
              f"(pred={k['pred_model']}, label peneliti={k['label_ground_truth']}) | R2={k['local_r2']}")
        for nama, ab in (("Merah", k["ablasi_merah"]), ("Hijau", k["ablasi_hijau"])):
            for n, a in ab.items():
                c = a["kontrol_setara"]
                print(f"  {nama}:{n}: {f(a['delta_pt'])} pt | arah sesuai={a['arah_sesuai']} | "
                      f"kontrol {a['kontrol_pembanding']}: {c['n_setara_atau_lebih_kuat']}/{c['n_kontrol_valid']} setara/lebih kuat")

    durasi = time.time() - t_mulai
    metadata = {
        "script_version": SCRIPT_VERSION, "waktu_eksekusi": datetime.now().isoformat(timespec="seconds"),
        "durasi_detik": round(durasi, 2), "python": platform.python_version(),
        "model_name": MODEL_NAME, "seeds": list(SEEDS), "n_seed": len(SEEDS),
        "audit_backend": audit, "jalur_skor": penilai.jalur,
        "n_kontrol_per_k": N_KONTROL, "toleransi_baseline": TOLERANSI_BASELINE,
        **meta_cfg, "konfigurasi_terdeteksi": konfig,
        "n_teks_unik_dinilai": len(penilai.cache), "n_pengukuran_gagal": len(penilai.galat),
        "catatan_label": "label_ground_truth = skenario berlabel peneliti; belum acuan independen "
                         "kecuali sumber_label terisi.",
        "catatan_statistik": "kontrol_setara = hitungan deskriptif dari N_KONTROL kontrol acak, "
                             "bukan p-value atau uji signifikansi.",
    }

    cap = datetime.now().strftime("%Y%m%d_%H%M%S")
    path_json, path_csv = f"hasil_kesetiaan_lime_v4_{cap}.json", f"hasil_kesetiaan_lime_v4_{cap}.csv"
    with open(path_json, "w", encoding="utf-8") as fh:
        json.dump({"metadata": metadata, "kasus_uji": kasus}, fh, indent=2, ensure_ascii=False, default=str)

    baris = []
    for k in kasus:
        b = {"id": k["id"], "status": k["status"], "status_engine": k.get("status_engine"),
             "label_peneliti": k["label_ground_truth"]}
        if k["status"] == "ok":
            pm = k["ablasi_merah"].get("hapus_pasangan") or {}
            ph = k["ablasi_hijau"].get("hapus_pasangan") or {}
            k1, k2 = (k["kontrol_acak"].get(x, {}).get("statistik_delta_pt", {}) for x in ("k1", "k2"))
            b.update({
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
            })
        else:
            b["alasan"] = k.get("alasan")
        baris.append(b)
    df = pd.DataFrame(baris)
    df.to_csv(path_csv, index=False)

    print("\n" + "=" * 95)
    print(f"Tersimpan: {path_csv} & {path_json} | {durasi:.1f} dtk | "
          f"{len(penilai.cache)} teks unik | {len(penilai.galat)} pengukuran gagal")
    cols = [c for c in ("id", "status", "label_peneliti", "pred_model", "p_awal_hoax",
                        "delta_pasang_merah_pt", "merah_setara_n", "delta_pasang_hijau_pt",
                        "hijau_setara_n", "kontrol_k2_mean_pt") if c in df.columns]
    print(df[cols].round(4).to_string(index=False))
    print("=" * 95)


if __name__ == "__main__":
    main()