"""Pilot stabilitas dan kandidat percepatan LIME, terpisah dari aplikasi.

Default: 4 teks x 3 seed explainer x 200/500 sampel = 24 fit padding aktif.
--padding compare membandingkan fixed/dynamic (48 fit). Kandidat dynamic
mempertahankan tokenizer, truncation 128, batch, bobot, seed, dan lock model.
Probabilitas kandidat diperiksa terhadap backend aktif pada SELURUH teks
neighborhood setelah setiap fit, di luar timer LIME. Pemeriksaan ini menambah
durasi penelitian; waktu tersebut bukan biaya LIME aplikasi.

    python uji_stabilitas_lime.py --probe
    python uji_stabilitas_lime.py
    python uji_stabilitas_lime.py --padding compare --ids T01 T03 --samples 200
    python uji_stabilitas_lime.py --resume hasil_parsial.json --plan-only
    python uji_stabilitas_lime.py --resume hasil_parsial.json

Hasil disimpan setelah setiap fit. Skrip tidak melatih model atau membuka lockbox.
Resume mempertahankan hasil lama dan hanya menjalankan baseline fixed yang belum
tercatat. Kandidat gagal tidak diulang otomatis dan toleransi tetap 1e-6.
"""
import argparse
import copy
import hashlib
import itertools
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uji_kesetiaan_lime import KORPUS_UJI, GalatPengukuran, validasi_matriks, versi_paket

VERSION = "1.1"
METHOD_VERSION = "1.0"  # metode, ambang, dan backend eksperimen tetap
LEGACY_SCRIPT_SHA256 = "e626acce002a416b19d195a4b15995f8df759854c031030a261e849634f31d41"
TOP_K = 5
TOLERANSI = 1e-6


class ParitasGagal(RuntimeError):
    pass


def angka(x):
    if x is None:
        return None
    a = np.asarray(x, dtype=float).reshape(-1)
    return float(a[0]) if a.size == 1 and np.isfinite(a[0]) else None


def periksa_paritas(reference, candidate):
    a = validasi_matriks(reference, len(reference), 3)
    b = validasi_matriks(candidate, len(a), 3)
    delta = float(np.max(np.abs(a - b))) if a.size else 0.0
    flips = int(np.count_nonzero((a >= 0.5) != (b >= 0.5)))
    worst = None
    if a.size:
        row, seed = np.unravel_index(np.argmax(np.abs(a - b)), a.shape)
        worst = {"row_index": int(row), "seed_index": int(seed),
                 "reference_probability": float(a[row, seed]), "candidate_probability": float(b[row, seed])}
    return {"n_teks": len(a), "max_abs_error": delta, "n_keputusan_berubah": flips,
            "n_probabilitas_melebihi_toleransi": int(np.count_nonzero(np.abs(a - b) > TOLERANSI)),
            "worst_difference": worst,
            "toleransi": TOLERANSI, "lulus": delta <= TOLERANSI and flips == 0}


def kunci_fit(fit):
    return fit["id"], fit["padding"], fit["num_samples"], fit["seed_lime"]


def rencana_fits(config):
    plan = []
    for case_id in config["ids"]:
        for index, (samples, seed) in enumerate(itertools.product(config["samples"], config["seeds"])):
            modes = config["padding"] if index % 2 == 0 else list(reversed(config["padding"]))
            plan.extend((case_id, mode, samples, seed) for mode in modes)
    return plan


def sisa_resume(payload):
    """Lanjutkan baseline saja; semua catatan lama, termasuk kegagalan, dipertahankan."""
    plan = rencana_fits(payload["metadata"]["config"])
    seen = set()
    for fit in payload["fits"]:
        key = kunci_fit(fit)
        if key in seen or key not in plan:
            raise ValueError("checkpoint memiliki percobaan duplikat atau di luar rencana")
        seen.add(key)
    return [key for key in plan if key[1] == "fixed" and key not in seen]


def periksa_sumber_resume(payload, corpus):
    """Resume hanya untuk implementasi/metode yang identitasnya dikenal."""
    metadata = payload["metadata"]
    if metadata.get("planned_fits") != len(rencana_fits(metadata["config"])):
        raise ValueError("jumlah rencana checkpoint tidak sesuai konfigurasi")
    if [p["id"] for p in payload["inputs"]] != metadata["config"]["ids"]:
        raise ValueError("daftar input checkpoint tidak sesuai konfigurasi")
    sha = lambda data: hashlib.sha256(data).hexdigest()
    script_hash = sha(Path(__file__).read_bytes())
    if metadata.get("sha256_script") not in (LEGACY_SCRIPT_SHA256, script_hash):
        raise ValueError("skrip sumber checkpoint tidak dikenal; tinjau sebelum melanjutkan")
    expected = {"sha256_inference": sha((ROOT / "src/ml/inference.py").read_bytes()),
                "sha256_ablation_script": sha((ROOT / "uji_kesetiaan_lime.py").read_bytes()),
                "sha256_corpus": sha(json.dumps(corpus, sort_keys=True, ensure_ascii=False).encode())}
    if any(metadata.get(k) != v for k, v in expected.items()):
        raise ValueError("kode inferensi/ablasi/korpus berbeda dari checkpoint")
    if metadata.get("method_version", METHOD_VERSION) != METHOD_VERSION:
        raise ValueError("metode eksperimen berbeda")
    if any(f.get("parity", {}).get("toleransi") != TOLERANSI
           for f in payload["fits"] if f.get("parity") is not None):
        raise ValueError("toleransi checkpoint berbeda")
    sisa_resume(payload)


def periksa_runtime_resume(previous, current):
    for key in ("audit_backend", "device", "model_seeds", "max_length", "batch_size", "torch_threads", "packages"):
        if previous.get(key) != current.get(key):
            raise ValueError(f"lingkungan resume berbeda: {key}")


class BackendPaddingDinamis:
    """Kandidat eksperimen: padding per minibatch; memakai objek model yang sama."""

    def __init__(self, backend, max_len, batch):
        self.backend, self.max_len, self.batch = backend, max_len, batch

    def seed_probs_each(self, texts):
        b = self.backend
        texts = [str(t) for t in texts]
        result = np.zeros((len(texts), len(b.seeds)), dtype=np.float64)
        if not texts:
            return result
        # Tokenisasi sekali per minibatch, lalu tensor CPU dipakai ulang semua seed.
        chunks = [(i, b.tokenizer(texts[i:i + self.batch], max_length=self.max_len,
                    padding=True, truncation=True, return_tensors="pt"))
                  for i in range(0, len(texts), self.batch)]
        with b._lock, b.torch.no_grad():
            for j, seed in enumerate(b.seeds):
                b.clf.load_state_dict(b.states[seed], strict=False)
                for i, enc in chunks:
                    ids = enc["input_ids"].to(b.device)
                    am = enc["attention_mask"].to(b.device)
                    p = b.torch.softmax(b.clf(ids, am), dim=1)[:, 1].cpu().numpy()
                    result[i:i + len(p), j] = p
        return result


class CallbackProbabilitas:
    """Validasi matriks; simpan keluaran aktual untuk pemeriksaan paritas sesudah fit."""

    def __init__(self, backend):
        self.backend = backend
        self.calls = []

    def __call__(self, texts):
        texts = list(texts)
        p = validasi_matriks(self.backend.seed_probs_each(texts), len(texts), 3)
        self.calls.append((texts, p.copy()))
        mean = p.mean(axis=1)
        return np.column_stack([1.0 - mean, mean])


def fitur_teratas(coefficients):
    # Nol tetap disimpan sebagai koefisien mentah, tetapi bukan fitur berpengaruh.
    ranked = sorted((c for c in coefficients if c["weight"] != 0),
                    key=lambda c: (-abs(c["weight"]), c["word"], c["feature_id"]))
    return [c["word"] for c in ranked[:TOP_K]]


def metrik_pasangan(a, b):
    sa, sb = set(a["top_words"]), set(b["top_words"])
    union = sa | sb
    wa = {c["word"]: c["weight"] for c in a["coefficients"]}
    wb = {c["word"]: c["weight"] for c in b["coefficients"]}
    shared = [w for w in wa.keys() & wb.keys() if wa[w] != 0 and wb[w] != 0]
    same = sum((wa[w] > 0) == (wb[w] > 0) for w in shared)
    return {"jaccard_top5": len(sa & sb) / len(union) if union else None,
            "n_top_a": len(sa), "n_top_b": len(sb), "n_shared_nonzero": len(shared),
            "n_same_sign": same, "sign_agreement": same / len(shared) if shared else None}


def statistik(values):
    vals = [float(v) for v in values if v is not None and math.isfinite(v)]
    return {"n": len(vals), "mean": float(np.mean(vals)) if vals else None,
            "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else None,
            "median": float(np.median(vals)) if vals else None}


def ringkasan(fits, config):
    rows = []
    for case_id, padding, samples in itertools.product(config["ids"], config["padding"], config["samples"]):
        group = [f for f in fits if (f["id"], f["padding"], f["num_samples"]) == (case_id, padding, samples)]
        ok = [f for f in group if f["status"] == "ok"]
        pairs = [{"seed_a": a["seed_lime"], "seed_b": b["seed_lime"], **metrik_pasangan(a, b)}
                 for a, b in itertools.combinations(ok, 2)]
        jac = statistik([p["jaccard_top5"] for p in pairs])
        complete = (len(ok) == len(config["seeds"]) and
                    jac["n"] == math.comb(len(config["seeds"]), 2) and jac["n"] > 0)
        rows.append({"id": case_id, "padding": padding, "num_samples": samples,
                     "n_direncanakan": len(config["seeds"]), "n_tercatat": len(group), "n_ok": len(ok),
                     "n_gagal_atau_ditolak": len(group) - len(ok), "lengkap": complete,
                     "pairs": pairs, "jaccard_top5": jac,
                     "sign_agreement": statistik([p["sign_agreement"] for p in pairs]),
                     "local_r2": statistik([f["local_r2"] for f in ok]),
                     "abs_local_error": statistik([f["abs_local_error"] for f in ok]),
                     "fit_seconds": statistik([f["fit_seconds"] for f in ok]),
                     "memenuhi_kriteria_jaccard": (jac["mean"] >= config["jaccard_threshold"])
                         if complete else None})
    return rows


def perbandingan_padding(fits):
    rows = []
    fixed = {(f["id"], f["num_samples"], f["seed_lime"]): f
             for f in fits if f["padding"] == "fixed" and f["status"] == "ok"}
    for dynamic in (f for f in fits if f["padding"] == "dynamic" and f["status"] == "ok"):
        key = dynamic["id"], dynamic["num_samples"], dynamic["seed_lime"]
        if key in fixed:
            baseline = fixed[key]
            # Sesi berbeda dapat mempunyai beban mesin berbeda: jangan buat rasio silang.
            if baseline.get("session_id") != dynamic.get("session_id"):
                continue
            rows.append({"id": key[0], "num_samples": key[1], "seed_lime": key[2],
                         "fixed_seconds": baseline["fit_seconds"], "dynamic_seconds": dynamic["fit_seconds"],
                         "speed_ratio_fixed_over_dynamic": baseline["fit_seconds"] / dynamic["fit_seconds"]
                             if dynamic["fit_seconds"] > 0 else None,
                         **metrik_pasangan(baseline, dynamic)})
    return rows


def simpan(payload, prefix):
    """Checkpoint atomik per fit; angka tidak tersedia tetap null/kosong."""
    payload["summary"] = ringkasan(payload["fits"], payload["metadata"]["config"])
    payload["padding_comparisons"] = perbandingan_padding(payload["fits"])
    path = prefix.with_suffix(".json")
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)
    rows = []
    for fit in payload["fits"]:
        row = {k: v for k, v in fit.items() if k not in ("coefficients", "top_words", "parity")}
        for k in ("coefficients", "top_words", "parity"):
            row[k] = json.dumps(fit.get(k), ensure_ascii=False, allow_nan=False)
        rows.append(row)
    path_csv = prefix.with_suffix(".csv")
    temp_csv = path_csv.with_suffix(".csv.tmp")
    pd.DataFrame(rows).to_csv(temp_csv, index=False)
    temp_csv.replace(path_csv)


def rss_bytes():
    try:
        import psutil
        return int(psutil.Process().memory_info().rss)
    except ImportError:
        return None


def run_fit(prepared, mode, samples, seed, backend, reference, explainer_class):
    result = {"id": prepared["id"], "padding": mode, "num_samples": samples, "seed_lime": seed,
              "status": "gagal", "error": None, "coefficients": [], "top_words": [],
              "local_r2": None, "local_prediction": None, "abs_local_error": None,
              "p_asli_hoax": prepared.get("p_asli_hoax"), "fit_seconds": None,
              "parity_seconds": None, "parity": None, "rss_before_bytes": None, "rss_after_bytes": None}
    if prepared["status"] != "ok":
        return {**result, "status": "ditolak", "error": prepared.get("reason")}
    try:
        text = prepared["teks_dinilai"]
        explainer = explainer_class(class_names=["TIDAK_HOAKS", "HOAKS"],
                                   split_expression=r"\W+", bow=True, random_state=seed,
                                   kernel_width=25, feature_selection="auto")
        callback = CallbackProbabilitas(backend)
        n_features = max(1, min(8, len(set(text.lower().split()))))  # kebijakan aplikasi
        result["rss_before_bytes"] = rss_bytes()
        start = time.perf_counter()
        try:
            exp = explainer.explain_instance(text, callback, labels=(1,), num_features=n_features,
                                            num_samples=samples, distance_metric="cosine")
        finally:
            result["fit_seconds"] = time.perf_counter() - start
            result["rss_after_bytes"] = rss_bytes()
        p_original = validasi_matriks([exp.predict_proba], 1, 2)[0, 1]
        if abs(float(p_original) - prepared["p_asli_hoax"]) > TOLERANSI:
            raise ParitasGagal("skor asli explainer berbeda dari baseline")
        if mode == "dynamic":
            start_parity = time.perf_counter()
            texts = [t for batch, _ in callback.calls for t in batch]
            measured = np.concatenate([p for _, p in callback.calls], axis=0)
            parity = periksa_paritas(reference.seed_probs_each(texts), measured)
            result["parity_seconds"] = time.perf_counter() - start_parity
            result["parity"] = parity
            worst = parity["worst_difference"]
            if worst is not None:
                worst["text"] = texts[worst["row_index"]]
                seeds = getattr(reference, "seeds", [])
                worst["model_seed"] = seeds[worst["seed_index"]] if len(seeds) == 3 else None
        words = exp.domain_mapper.indexed_string
        for feature_id, coefficient in exp.local_exp[1]:
            weight = angka(coefficient)
            if weight is None:
                raise ValueError("koefisien LIME tidak finite")
            result["coefficients"].append({"feature_id": int(feature_id),
                                           "word": str(words.word(feature_id)), "weight": weight})
        result["top_words"] = fitur_teratas(result["coefficients"])
        score = exp.score.get(1) if isinstance(exp.score, dict) else exp.score
        result["local_r2"] = angka(score)
        result["local_prediction"] = angka(getattr(exp, "local_pred", None))
        if result["local_prediction"] is not None:
            result["abs_local_error"] = abs(result["local_prediction"] - float(p_original))
        if result["parity"] is not None and not result["parity"]["lulus"]:
            raise ParitasGagal("probabilitas/keputusan kandidat berbeda pada neighborhood aktual")
        result["status"] = "ok"
    except Exception as exc:
        result["status"] = "paritas_gagal" if isinstance(exc, ParitasGagal) else "gagal"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def probe():
    tests = {}
    p = np.array([[0.1, 0.2, 0.3], [0.8, 0.9, 0.7]])
    tests["paritas_identik"] = periksa_paritas(p, p)["lulus"]
    tests["paritas_menolak_perubahan_skor"] = not periksa_paritas(p, p + 0.001)["lulus"]
    tests["paritas_menolak_flip_dekat_ambang"] = not periksa_paritas([[0.4999999] * 3], [[0.5000001] * 3])["lulus"]
    class Stub:
        def seed_probs_each(self, texts):
            return np.tile([0.2, 0.4, 0.6], (len(texts), 1))
    cb = CallbackProbabilitas(Stub())
    tests["callback_mean_tiga_seed"] = np.allclose(cb(["teks"]), [[0.6, 0.4]])
    tests["callback_mencatat_neighborhood"] = cb.calls[0][0] == ["teks"]
    bad = type("Bad", (), {"seed_probs_each": lambda self, texts: [[float("nan")] * 3]})()
    try:
        CallbackProbabilitas(bad)(["teks"])
        tests["callback_menolak_nan"] = False
    except GalatPengukuran:
        tests["callback_menolak_nan"] = True
    coefficients = [{"feature_id": i, "word": w, "weight": v} for i, (w, v) in
                    enumerate((("Viral", 0.2), ("viral", -0.3), ("nol", 0.0)))]
    a = {"coefficients": coefficients, "top_words": fitur_teratas(coefficients)}
    b = {"coefficients": [{**c, "weight": -c["weight"]} for c in coefficients], "top_words": a["top_words"]}
    pair = metrik_pasangan(a, b)
    tests["fitur_kapitalisasi_terpisah"] = a["top_words"] == ["viral", "Viral"]
    tests["tanda_dengan_denominator"] = pair["sign_agreement"] == 0 and pair["n_shared_nonzero"] == 2
    tests["himpunan_kosong_bukan_stabil_sempurna"] = metrik_pasangan(
        {"coefficients": [], "top_words": []}, {"coefficients": [], "top_words": []})["jaccard_top5"] is None
    tests["prediksi_regresi_negatif_dipertahankan"] = angka([-0.11]) == -0.11
    tests["r2_tidak_tersedia_tetap_null"] = angka(float("nan")) is None
    config = {"ids": ["T"], "padding": ["fixed"], "samples": [200], "seeds": [1, 2, 3], "jaccard_threshold": 0.6}
    fits = [{**a, "id": "T", "padding": "fixed", "num_samples": 200, "seed_lime": s, "status": "ok",
             "local_r2": 0.5, "abs_local_error": 0.01, "fit_seconds": 1.0} for s in (1, 2, 3)]
    summary = ringkasan(fits, config)[0]
    tests["tiga_seed_tiga_pasangan"] = len(summary["pairs"]) == 3 and summary["lengkap"]
    tests["fit_gagal_tidak_dihilangkan"] = ringkasan(fits[:2], config)[0]["memenuhi_kriteria_jaccard"] is None
    for name, ok in tests.items():
        print(f"[{'LULUS' if ok else 'GAGAL'}] {name}")
    return all(tests.values())


def parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--probe", action="store_true", help="probe tanpa model dan tanpa berkas hasil")
    p.add_argument("--ids", nargs="+")
    p.add_argument("--seeds", nargs="+", type=int, help="seed explainer, bukan checkpoint")
    p.add_argument("--samples", nargs="+", type=int)
    p.add_argument("--padding", choices=("fixed", "dynamic", "compare"))
    p.add_argument("--jaccard-threshold", type=float)
    p.add_argument("--resume", type=Path, help="lanjutkan fit fixed yang hilang; sumber tetap utuh")
    p.add_argument("--plan-only", action="store_true", help="tampilkan rencana tanpa memuat model")
    return p


def main():
    arg_parser = parser()
    args = arg_parser.parse_args()
    known = {c["id"]: c for c in KORPUS_UJI}
    source = None
    source_bytes = None
    if args.resume:
        if any(v is not None for v in (args.ids, args.seeds, args.samples, args.padding, args.jaccard_threshold)):
            arg_parser.error("--resume memakai konfigurasi sumber; jangan gabungkan dengan opsi konfigurasi")
        source_bytes = args.resume.read_bytes()
        source = json.loads(source_bytes)
        cfg = source["metadata"]["config"]
        args.ids, args.seeds, args.samples = cfg["ids"], cfg["seeds"], cfg["samples"]
        args.jaccard_threshold = cfg["jaccard_threshold"]
        modes = list(cfg["padding"])
    else:
        args.ids = args.ids or [c["id"] for c in KORPUS_UJI]
        args.seeds = args.seeds or [1, 2, 3]
        args.samples = args.samples or [200, 500]
        args.padding = args.padding or "fixed"
        args.jaccard_threshold = 0.6 if args.jaccard_threshold is None else args.jaccard_threshold
        modes = ["fixed", "dynamic"] if args.padding == "compare" else [args.padding]
    for name, values in (("ids", args.ids), ("seeds", args.seeds), ("samples", args.samples)):
        if len(set(values)) != len(values):
            arg_parser.error(f"{name} tidak boleh berulang")
    if any(i not in known for i in args.ids):
        arg_parser.error("ID tidak dikenal; pilih " + ", ".join(known))
    if any(s < 0 or s >= 2 ** 32 for s in args.seeds) or any(n < 2 for n in args.samples):
        arg_parser.error("seed harus uint32 dan num_samples minimal 2")
    if not math.isfinite(args.jaccard_threshold) or not 0 <= args.jaccard_threshold <= 1:
        arg_parser.error("ambang Jaccard harus finite di [0, 1]")
    if args.probe:
        return 0 if probe() else 1
    sha = lambda data: hashlib.sha256(data).hexdigest()
    corpus = [known[i] for i in args.ids]
    config = {"ids": args.ids, "seeds": args.seeds, "samples": args.samples, "padding": modes,
              "jaccard_threshold": args.jaccard_threshold}
    if source is not None:
        periksa_sumber_resume(source, corpus)
    pending = sisa_resume(source) if source is not None else rencana_fits(config)
    if args.plan_only:
        print(f"{len(pending)} percobaan belum dijalankan" + (" (baseline fixed saja)" if source is not None else ""))
        for case_id, mode, samples, seed in pending:
            print(f"{case_id} {mode} n={samples} seed={seed}")
        return 0
    if source is not None and not pending:
        print("Tidak ada percobaan fixed yang hilang; sumber tidak diubah.")
        return 0
    identities = {"sha256_script": sha(Path(__file__).read_bytes()),
                  "sha256_inference": sha((ROOT / "src/ml/inference.py").read_bytes()),
                  "sha256_ablation_script": sha((ROOT / "uji_kesetiaan_lime.py").read_bytes()),
                  "sha256_corpus": sha(json.dumps(corpus, sort_keys=True, ensure_ascii=False).encode())}
    started_at = datetime.now().astimezone().isoformat()
    from lime.lime_text import LimeTextExplainer
    from src.ml.inference import (get_predictor, MAX_LEN, BATCH, SEEDS, EXPECTED_SHA256,
                                  EXPECTED_PIPELINE_SHA256, EXPECTED_BASE_REVISION)
    start = time.perf_counter()
    predictor = get_predictor()
    backend = predictor.backend
    audit = backend.audit
    expected = {"text_pipeline_sha256": EXPECTED_PIPELINE_SHA256, "base_revision": EXPECTED_BASE_REVISION,
                **{f"sha256_seed_{s}": h for s, h in EXPECTED_SHA256.items()}}
    if list(backend.seeds) != SEEDS or any(audit.get(k) != v for k, v in expected.items()):
        raise RuntimeError("Identitas tiga checkpoint/pipeline/revisi tidak sesuai baseline beku")
    prefix = ROOT / ("hasil_stabilitas_lime_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    payload = {"metadata": {"script_version": VERSION, "method_version": METHOD_VERSION, "started_at": started_at,
               "config": config, "planned_fits": len(corpus) * len(args.seeds) * len(args.samples) * len(modes),
               **identities,
               "audit_backend": audit, "device": str(backend.device), "model_seeds": list(backend.seeds),
               "max_length": MAX_LEN, "batch_size": BATCH, "torch_threads": backend.torch.get_num_threads(),
               "model_init_seconds": time.perf_counter() - start,
               "packages": {n: versi_paket(n) for n in ("numpy", "pandas", "lime", "scikit-learn", "torch", "transformers", "psutil")},
               "notes": ["Pilot empat skenario peneliti; bukan akurasi atau evaluasi lockbox.",
                         "LIME menjelaskan rerata P(hoaks) tiga seed, bukan aturan voting.",
                         "Galat lokal hanya pada teks asli; bukan kesetiaan heldout.",
                         "Jaccard 0.6 adalah kriteria eksploratif, bukan standar keandalan.",
                         "Kurang dari dua seed explainer tidak menghasilkan pengukuran stabilitas.",
                         "RSS sebelum/sesudah fit bukan puncak memori.",
                         "Paritas kandidat setelah fit di luar timer LIME; menambah durasi studi."],
               "complete": False}, "inputs": [], "fits": []}
    if source is not None:
        periksa_runtime_resume(source["metadata"], payload["metadata"])
        payload["fits"] = copy.deepcopy(source["fits"])
        for fit in payload["fits"]:
            fit.setdefault("session_id", args.resume.stem)
        payload["resume_history"] = copy.deepcopy(source.get("resume_history", []))
        payload["resume_history"].append({"source_path": str(args.resume.resolve()),
            "source_sha256": sha(source_bytes), "source_script_sha256": source["metadata"]["sha256_script"],
            "source_version": source["metadata"]["script_version"], "n_existing_fits": len(source["fits"])})
        payload["metadata"].update({"resume_target_fits": len(pending), "resume_complete": False,
                                    "resume_policy": "missing_fixed_only; recorded failures never retried"})
    dynamic = BackendPaddingDinamis(backend, MAX_LEN, BATCH)
    implementations = {"fixed": backend, "dynamic": dynamic}
    for item in corpus:
        result = predictor.nilai(item["teks"], explain=False, debug=True)
        prepared = {"id": item["id"], "label_peneliti": item["label_ground_truth"],
                    "sumber_label": item.get("sumber_label"), "status_engine": result.get("status"),
                    "status": "ok" if result.get("success") else "ditolak", "reason": result.get("reason")}
        if prepared["status"] == "ok":
            prepared["teks_dinilai"] = result["teks_dinilai"]
            prob = validasi_matriks(backend.seed_probs_each([result["teks_dinilai"]]), 1, 3)
            prepared["p_asli_per_seed"] = prob[0].tolist()
            prepared["p_asli_hoax"] = float(prob.mean())
        payload["inputs"].append(prepared)
    if source is not None:
        if len(source["inputs"]) != len(payload["inputs"]):
            raise ValueError("jumlah input berubah saat resume")
        for previous, current in zip(source["inputs"], payload["inputs"]):
            if (previous["id"], previous["status"], previous.get("teks_dinilai")) != (
                    current["id"], current["status"], current.get("teks_dinilai")):
                raise ValueError("masukan yang dipraproses berubah saat resume")
            if current["status"] == "ok" and not periksa_paritas(
                    [previous["p_asli_per_seed"]], [current["p_asli_per_seed"]])["lulus"]:
                raise ValueError("probabilitas baseline berubah saat resume")
    simpan(payload, prefix)
    # Warm-up dan preflight; bukan bagian dari timer fit.
    short_probes = [p["teks_dinilai"] for p in payload["inputs"] if p["status"] == "ok"] + [""]
    probe_groups = [short_probes,
                    ["Pemerintah menyatakan bahwa anggaran daerah ditinjau secara terbuka. " * 140]]
    # Pisahkan kelompok panjang agar probe pendek benar-benar memakai padding pendek.
    try:
        baseline = np.concatenate([backend.seed_probs_each(group) for group in probe_groups], axis=0)
        validasi_matriks(baseline, sum(map(len, probe_groups)), 3)
        if source is None and "dynamic" in modes:
            candidate = np.concatenate([dynamic.seed_probs_each(group) for group in probe_groups], axis=0)
            payload["parity_preflight"] = periksa_paritas(baseline, candidate)
            if not payload["parity_preflight"]["lulus"]:
                raise ParitasGagal("paritas kandidat gagal pada probe pendek/panjang/kosong")
        payload["preflight_status"] = "ok"
    except Exception as exc:
        payload["preflight_status"] = "gagal"
        payload["preflight_error"] = f"{type(exc).__name__}: {exc}"
        payload["metadata"]["elapsed_seconds"] = time.perf_counter() - start
        simpan(payload, prefix)
        print("Pemeriksaan awal gagal; lihat", prefix.with_suffix(".json"))
        return 1
    prepared_by_id = {case["id"]: case for case in payload["inputs"]}
    full_plan = rencana_fits(config)
    for step, (case_id, mode, samples, seed) in enumerate(pending, 1):
        fit = run_fit(prepared_by_id[case_id], mode, samples, seed, implementations[mode], backend, LimeTextExplainer)
        fit["order"] = len(payload["fits"]) + 1
        fit["planned_order"] = full_plan.index((case_id, mode, samples, seed)) + 1
        fit["session_id"] = prefix.name
        payload["fits"].append(fit)
        payload["metadata"]["elapsed_seconds"] = time.perf_counter() - start
        simpan(payload, prefix)
        print(f"{'Resume ' if source is not None else ''}{step}/{len(pending)} {case_id} {mode} "
              f"n={samples} seed={seed}: {fit['status']} | {fit['fit_seconds']} detik", flush=True)
        if fit["status"] == "paritas_gagal":
            print("Kandidat dihentikan karena paritas gagal; hasil parsial tersimpan.")
            return 1
    payload["metadata"]["complete"] = len(payload["fits"]) == len(full_plan)
    if source is not None:
        payload["metadata"]["resume_complete"] = True
    fixed_results = {kunci_fit(f): f for f in payload["fits"] if f["padding"] == "fixed"}
    payload["metadata"]["baseline_fixed_complete"] = all(
        key in fixed_results and fixed_results[key]["status"] == "ok" for key in full_plan if key[1] == "fixed")
    payload["metadata"]["elapsed_seconds"] = time.perf_counter() - start
    simpan(payload, prefix)
    rows = [{"id": r["id"], "padding": r["padding"], "samples": r["num_samples"], "n_ok": r["n_ok"],
             "jaccard": r["jaccard_top5"]["mean"], "local_gap": r["abs_local_error"]["mean"],
             "fit_seconds": r["fit_seconds"]["median"]} for r in payload["summary"]]
    print(pd.DataFrame(rows).to_string(index=False))
    print("Tersimpan:", prefix.with_suffix(".json"), "dan", prefix.with_suffix(".csv"))
    if source is not None:
        print("Kelanjutan baseline selesai. Kegagalan kandidat lama tetap tercatat; compare belum disetujui.")
    return 0 if all(f["status"] == "ok" for f in payload["fits"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
