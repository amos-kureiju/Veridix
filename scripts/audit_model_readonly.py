"""Audit the frozen development data and saved predictions; never evaluate lockbox.

Run from the repository root with the project Python environment. Only the audit
JSON in reports/ is written; datasets, checkpoints, and old results are preserved.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, ks_2samp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import text_pipeline as tp
from src.ml.inference import Penilai
from src.utils.input_validation import stopword_ratio, validate_input_text
from src.utils.political_guardrail import check_political_domain
from src.utils.praproses import praproses


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def key(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def canonical_title(text):
    return key(tp.clean(tp.norm_title(str(text))))


def metrics(y, pred):
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "confusion_matrix_labels_0_1": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
    }


def main():
    folder = ROOT / "data/processed_v2"
    splits = {s: pd.read_csv(folder / f"{s}.csv") for s in ("train", "val", "dev_test")}
    corp = pd.concat([d.assign(split=s) for s, d in splits.items()], ignore_index=True)
    log = json.loads((ROOT / "log_training.json").read_text(encoding="utf-8"))
    saved = pd.read_csv(ROOT / "prediksi_val_dev.csv")
    report = {"scope": "train/val/dev_test only; no lockbox rows read or evaluated"}

    report["splits"] = {}
    for name, d in splits.items():
        lengths = d.text.str.split().str.len()
        report["splits"][name] = {
            "n": len(d), "labels": d.label.value_counts().sort_index().to_dict(),
            "nulls": d.isna().sum().to_dict(),
            "words_min_median_max": [int(lengths.min()), float(lengths.median()), int(lengths.max())],
            "duplicate_ids": int(d.id.duplicated().sum()),
        }
    report["source_by_label"] = pd.crosstab(corp.source, corp.label).to_dict(orient="index")
    report["year_by_label"] = pd.crosstab(pd.to_datetime(corp.date).dt.year, corp.label).to_dict(orient="index")
    report["group_cross_split"] = int(corp.groupby("group_id").split.nunique().gt(1).sum())
    report["text_cross_split"] = int(corp.groupby("text").split.nunique().gt(1).sum())
    report["canonical_title_cross_split"] = int(corp.assign(k=corp.title.map(canonical_title)).groupby("k").split.nunique().gt(1).sum())
    report["word_length_ks"] = float(ks_2samp(corp[corp.label == 0].text.str.split().str.len(), corp[corp.label == 1].text.str.split().str.len()).statistic)

    # Hash only public development artifacts and raw files here. The existing
    # verifikasi_manifest.py separately verifies the lockbox bytes without parsing.
    manifest = pd.read_csv(folder / "MANIFEST_sha256.csv")
    integrity = []
    for row in manifest.itertuples():
        name = str(row.berkas).replace("\\", "/")
        if name.startswith("LOCKBOX/"):
            continue
        if name.startswith("RAW/"):
            path = ROOT / "data/raw" / name[4:]
        elif name in ("text_pipeline.py", "01b_rebuild_dataset_final.py"):
            path = ROOT / name
        else:
            path = folder / name
        integrity.append({"file": name, "exists": path.exists(), "matches": path.exists() and sha(path) == row.sha256.lower()})
    report["manifest_development_and_raw"] = integrity
    report["training_data_hash_matches"] = {
        f: sha(ROOT / f if f == "text_pipeline.py" else folder / f) == h
        for f, h in log["data_hash"].items()
    }

    report["saved_prediction_alignment"] = {}
    report["saved_metrics"] = []
    for name in ("val", "dev_test"):
        d = splits[name]
        ref = saved[saved.split == name]
        report["saved_prediction_alignment"][name] = {
            "unique_ids": not bool(ref.id.duplicated().any()),
            "id_set_equal": set(ref.id) == set(d.id),
            "labels_equal": bool((ref.set_index("id").loc[d.id, "label"].to_numpy() == d.label.to_numpy()).all()),
        }
        ref = ref.set_index("id").loc[d.id]
        for run in log["runs"]:
            run_key = f'{run["loss"]}_{run["seed"]}'
            p = ref[f"pred_{run_key}"].to_numpy()
            prob = ref[f"prob_{run_key}"].to_numpy()
            m = metrics(d.label, p)
            m.update(split=name, run=run_key, matches_log_acc=bool(np.isclose(m["accuracy"], run["val_acc" if name == "val" else "dev_acc"])),
                     matches_log_f1=bool(np.isclose(m["macro_f1"], run["val_f1" if name == "val" else "dev_f1"])),
                     pred_probability_mismatches=int((p != (prob >= 0.5)).sum()))
            report["saved_metrics"].append(m)

    runs = pd.DataFrame(log["runs"])
    report["training_summary"] = {
        loss: {name: {"mean": float(g[name].mean()), "sample_std": float(g[name].std())}
               for name in ("val_acc", "val_f1", "dev_acc", "dev_f1", "eval_benar_share_hoaks", "eval_kompas_share_hoaks")}
        for loss, g in runs.groupby("loss")
    }
    means = runs.groupby("loss").val_f1.mean()
    chosen = "ce" if abs(means.ce - means.focal) < 0.01 else means.idxmax()
    report["selection_rule_matches"] = chosen == log["terpilih"]

    tr = splits["train"]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    baseline = LogisticRegression(max_iter=2000, random_state=0).fit(vectorizer.fit_transform(tr.text), tr.label)
    report["baseline_and_paired_tests"] = {}
    for name in ("val", "dev_test"):
        d = splits[name]
        pred = baseline.predict(vectorizer.transform(d.text))
        ref = saved[saved.split == name].set_index("id").loc[d.id]
        result = metrics(d.label, pred)
        result["paired_ce_vs_baseline"] = []
        for seed in (42, 123, 999):
            a, b = ref[f"pred_ce_{seed}"].to_numpy() == d.label.to_numpy(), pred == d.label.to_numpy()
            n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
            pvalue = float(binomtest(min(n10, n01), n10 + n01, 0.5).pvalue) if n10 + n01 else 1.0
            result["paired_ce_vs_baseline"].append({"seed": seed, "bert_only_correct": n10, "baseline_only_correct": n01, "p": pvalue, "accuracy_difference": float(a.mean() - b.mean())})
        report["baseline_and_paired_tests"][name] = result

    # Exploratory source holdouts reuse dev_test and are not final test results.
    report["baseline_source_holdout_diagnostic"] = []
    for source, held in splits["dev_test"].groupby("source"):
        train_other = tr[tr.source != source]
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        clf = LogisticRegression(max_iter=2000, random_state=0).fit(vec.fit_transform(train_other.text), train_other.label)
        p = clf.predict(vec.transform(held.text))
        regular = baseline.predict(vectorizer.transform(held.text))
        report["baseline_source_holdout_diagnostic"].append({
            "source": source, "n": len(held), "label": int(held.label.iloc[0]),
            "held_source_accuracy": float(accuracy_score(held.label, p)),
            "regular_baseline_accuracy": float(accuracy_score(held.label, regular)),
        })

    # Refit similarities on the smaller development corpus. These are diagnostic
    # candidates, not proof of a violation of the original full-corpus graph.
    sim_vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.5, sublinear_tf=True).fit(corp.text)
    xtrain = sim_vec.transform(tr.text)
    report["refit_similarity_candidates"] = {}
    for name in ("val", "dev_test"):
        d = splits[name]
        sim = (sim_vec.transform(d.text) @ xtrain.T).tocoo()
        selected = sim.data > 0.7
        report["refit_similarity_candidates"][name] = [
            {"eval_id": d.id.iloc[i], "train_id": tr.id.iloc[j], "cosine": float(value),
             "same_label": bool(d.label.iloc[i] == tr.label.iloc[j])}
            for i, j, value in zip(sim.row[selected], sim.col[selected], sim.data[selected])
        ]

    def features(d):
        t = d.text
        return np.c_[t.str.split().str.len(), t.str.len(), t.str.count(r"[.!?]"), t.str.count(",")]

    te = splits["dev_test"]
    tree = DecisionTreeClassifier(max_depth=4, random_state=0).fit(features(tr), tr.label)
    report["c4_surface_feature_accuracy_recomputed"] = float(accuracy_score(te.label, tree.predict(features(te))))
    report["c4_single_feature_accuracy"] = {}
    for i, feature in enumerate(("words", "characters", "sentence_punctuation", "commas")):
        tree = DecisionTreeClassifier(max_depth=3, random_state=0).fit(features(tr)[:, [i]], tr.label)
        report["c4_single_feature_accuracy"][feature] = float(accuracy_score(te.label, tree.predict(features(te)[:, [i]])))

    validation = [validate_input_text(t) for t in corp.text]
    checked = corp.assign(
        valid=[r["ok"] for r in validation],
        stopword_ratio=corp.text.map(stopword_ratio),
        domain_short=[check_political_domain(t)[0] for t in corp.text],
        domain_full=[check_political_domain(t)[0] for t in corp.title.fillna("") + ". " + corp.body.fillna("")],
    )
    report["gates_by_label"] = {}
    for label, d in checked.groupby("label"):
        rejected = d[~d.valid]
        report["gates_by_label"][str(label)] = {
            "n": len(d), "input_rejected": len(rejected),
            "rejected_with_exact_zero_stopword_ratio": int((rejected.stopword_ratio == 0).sum()),
            "rejected_positive_stopword_ratios": rejected.loc[rejected.stopword_ratio > 0, "stopword_ratio"].tolist(),
            "domain_short_pass": int(d.domain_short.sum()), "domain_full_pass": int(d.domain_full.sum()),
            "combined_short_pass": int((d.valid & d.domain_short).sum()),
        }

    report["application_on_saved_predictions"] = {}
    for name in ("val", "dev_test"):
        d = checked[checked.split == name].copy()
        ref = saved[saved.split == name].set_index("id").loc[d.id]
        votes = ref[[f"pred_ce_{s}" for s in (42, 123, 999)]].to_numpy().sum(axis=1)
        gate = (d.valid & d.domain_short).to_numpy()
        decided = gate & np.isin(votes, [0, 3])
        correct = (votes >= 2).astype(int) == d.label.to_numpy()
        report["application_on_saved_predictions"][name] = {
            "note": "Uses saved per-seed outputs; gates re-run on frozen short texts. Not an independent full API evaluation.",
            "n": len(d), "gate_pass": int(gate.sum()), "decided": int(decided.sum()),
            "ambigu_after_gates": int((gate & ~np.isin(votes, [0, 3])).sum()),
            "decided_accuracy": float(correct[decided].mean()),
            "correct_and_decided_over_all": float((correct & decided).mean()),
        }

    # Reproduce the notebook's OOD title filtering, then check canonical keys.
    seen_raw = set(corp.title.map(key))
    seen_canonical = set(corp.title.map(canonical_title))
    report["external_title_dedup"] = {}
    for filename in ("eval_benar.csv", "eval_kompas_cekfakta.csv"):
        ext = pd.read_csv(folder / filename)
        if filename.startswith("eval_kompas"):
            tagged = ext.title.str.match(r"(?i)^\s*\[(?:hoaks|hoax|salah|disinformasi)\]")
            if tagged.any():
                ext = ext[tagged]
        ext = ext.assign(k=ext.title.map(key)).drop_duplicates("k")
        ext = ext[~ext.k.isin(seen_raw)]
        overlaps = ext.title.map(canonical_title).isin(seen_canonical)
        report["external_title_dedup"][filename] = {
            "notebook_n": len(ext), "canonical_title_overlap_with_development": int(overlaps.sum()),
            "overlap_examples": ext.loc[overlaps, "title"].head(3).tolist(),
            "raw_label_counts_not_ground_truth_for_this_diagnostic": ext.label.value_counts().to_dict(),
            "titles_passing_application_input_and_domain": sum(
                validate_input_text(t)["ok"] and check_political_domain(t)[0]
                for t in ext.title.map(lambda t: tp.ensure_end(tp.norm_title(str(t))))
            ),
        }

    class FakeBackend:
        def seed_probs_each(self, texts):
            return np.tile([0.1, 0.1, 0.1], (len(texts), 1))

    raw = "KPU dan " + " ".join(["https://example.com/berita"] * 8)
    report["minimum_words_after_cleanup_probe"] = {
        "input_words": len(raw.split()), "validation_ok": validate_input_text(raw)["ok"],
        "prepared_text": praproses(raw), "prepared_words": len(praproses(raw).split()),
        "result": Penilai(FakeBackend()).nilai(raw),
        "backend": "fake; probes orchestration only, not classification ability",
    }

    out = ROOT / "reports/audit_model_2026-10-24_summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=lambda x: x.item() if isinstance(x, np.generic) else str(x)), encoding="utf-8")
    print(out)
    for field in ("splits", "source_by_label", "group_cross_split", "text_cross_split", "canonical_title_cross_split", "word_length_ks", "selection_rule_matches", "baseline_and_paired_tests", "baseline_source_holdout_diagnostic", "refit_similarity_candidates", "c4_surface_feature_accuracy_recomputed", "c4_single_feature_accuracy", "gates_by_label", "application_on_saved_predictions", "external_title_dedup", "minimum_words_after_cleanup_probe"):
        print(field, json.dumps(report[field], ensure_ascii=False, default=str))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
