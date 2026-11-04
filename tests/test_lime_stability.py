"""Regresi eksperimen LIME; backend tiruan, tanpa checkpoint, database, atau jaringan."""
import copy
import hashlib
import json
import unittest
from types import SimpleNamespace

import numpy as np

import uji_stabilitas_lime as experiment


class Tensor:
    def __init__(self, values):
        self.values = np.asarray(values)

    def to(self, device):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.values

    def __getitem__(self, index):
        return Tensor(self.values[index])


class Context:
    def __init__(self):
        self.active = False

    def __enter__(self):
        if self.active:
            raise AssertionError("context masuk dua kali")
        self.active = True
        return self

    def __exit__(self, *args):
        self.active = False


class TestDynamicPadding(unittest.TestCase):
    def backend(self, fail=False):
        lock, grad = Context(), Context()
        token_calls, swaps, forwards = [], [], []
        owner = self

        class Model:
            def load_state_dict(self, state, strict):
                owner.assertTrue(lock.active and grad.active)
                owner.assertIs(strict, False)
                self.seed = state["seed"]
                swaps.append(self.seed)

            def __call__(self, ids, mask):
                owner.assertTrue(lock.active and grad.active)
                forwards.append((self.seed, len(ids.values)))
                if fail:
                    raise RuntimeError("galat forward tiruan")
                logits = ids.values[:, 0] * 0.001 + (self.seed % 10) * 0.01
                return Tensor(np.column_stack([np.zeros_like(logits), logits]))

        def tokenize(texts, **kwargs):
            self.assertFalse(lock.active)
            self.assertEqual(kwargs, dict(max_length=128, padding=True, truncation=True, return_tensors="pt"))
            token_calls.append(list(texts))
            ids = np.array([[int(t) + 1] for t in texts])
            return {"input_ids": Tensor(ids), "attention_mask": Tensor(np.ones_like(ids))}

        def softmax(tensor, dim):
            self.assertEqual(dim, 1)
            values = np.exp(tensor.values - tensor.values.max(axis=1, keepdims=True))
            return Tensor(values / values.sum(axis=1, keepdims=True))

        backend = SimpleNamespace(seeds=[42, 123, 999], states={s: {"seed": s} for s in (42, 123, 999)},
            _lock=lock, torch=SimpleNamespace(no_grad=lambda: grad, softmax=softmax),
            tokenizer=tokenize, clf=Model(), device="cpu")
        return backend, grad, token_calls, swaps, forwards

    def test_chunks_reused_and_seed_row_order_preserved(self):
        backend, grad, tokens, swaps, forwards = self.backend()
        output = experiment.BackendPaddingDinamis(backend, 128, 32).seed_probs_each(map(str, range(70)))
        expected = np.array([[1 / (1 + np.exp(-((i + 1) * 0.001 + (s % 10) * 0.01)))
                              for s in backend.seeds] for i in range(70)])
        np.testing.assert_allclose(output, expected, rtol=0, atol=1e-15)
        self.assertEqual(output.dtype, np.float64)
        self.assertEqual([len(batch) for batch in tokens], [32, 32, 6])
        self.assertEqual(swaps, backend.seeds)
        self.assertEqual(forwards, [(s, n) for s in backend.seeds for n in (32, 32, 6)])
        self.assertFalse(backend._lock.active or grad.active)
        output = experiment.BackendPaddingDinamis(backend, 128, 32).seed_probs_each([])
        self.assertEqual(output.shape, (0, 3))
        self.assertEqual([len(batch) for batch in tokens], [32, 32, 6])
        self.assertEqual(swaps, backend.seeds)
        self.assertEqual(len(forwards), 9)

    def test_forward_failure_releases_lock_and_no_grad(self):
        backend, grad, _, _, _ = self.backend(fail=True)
        with self.assertRaisesRegex(RuntimeError, "galat forward"):
            experiment.BackendPaddingDinamis(backend, 128, 32).seed_probs_each(["1"])
        self.assertFalse(backend._lock.active or grad.active)


class ToyBackend:
    text = "Viral viral berita resmi politik pemerintah daerah nasional data kabar"
    seeds = [42, 123, 999]

    def __init__(self, alter_neighbors=False):
        self.alter_neighbors = alter_neighbors
        self.calls = []

    def seed_probs_each(self, texts):
        self.calls.append(list(texts))
        rows = []
        for text in texts:
            words = set(text.split())
            p = 0.4 + 0.2 * ("viral" in words) - 0.1 * ("Viral" in words) - 0.15 * ("resmi" in words)
            if self.alter_neighbors and text != self.text:
                p += 0.01
            rows.append([p - 0.02, p, p + 0.02])
        return np.asarray(rows)


class TestStabilityFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lime.lime_text import LimeTextExplainer
        cls.explainer = LimeTextExplainer

    def setUp(self):
        self.reference = ToyBackend()
        self.prepared = {"id": "TOY", "status": "ok", "teks_dinilai": ToyBackend.text,
                         "p_asli_hoax": float(self.reference.seed_probs_each([ToyBackend.text]).mean())}
        self.reference.calls.clear()

    def fit(self, mode="fixed", backend=None):
        return experiment.run_fit(self.prepared, mode, 40, 7,
            backend or self.reference, self.reference, self.explainer)

    def test_actual_lime_fixed_dynamic_pair_matches_raw_coefficients(self):
        fixed, dynamic = self.fit(), self.fit("dynamic", ToyBackend())
        self.assertEqual((fixed["status"], dynamic["status"]), ("ok", "ok"))
        self.assertEqual(fixed["coefficients"], dynamic["coefficients"])
        self.assertTrue(any(c["weight"] != round(c["weight"], 4) for c in fixed["coefficients"]))
        self.assertTrue(dynamic["parity"]["lulus"])
        self.assertEqual(dynamic["parity"]["n_teks"], 40)
        self.assertEqual(len(self.reference.calls[-1]), 40)
        self.assertEqual(experiment.metrik_pasangan(fixed, dynamic)["jaccard_top5"], 1.0)

    def test_changed_neighbors_rejected_even_when_original_score_matches(self):
        result = self.fit("dynamic", ToyBackend(alter_neighbors=True))
        self.assertEqual(result["status"], "paritas_gagal")
        self.assertEqual(result["parity"]["n_teks"], 40)
        self.assertGreater(result["parity"]["max_abs_error"], experiment.TOLERANSI)
        self.assertIsNotNone(result["fit_seconds"])
        self.assertIsNotNone(result["parity_seconds"])
        self.assertTrue(result["coefficients"])
        self.assertTrue(result["top_words"])
        self.assertIsNotNone(result["local_r2"])
        self.assertIsNotNone(result["abs_local_error"])
        worst = result["parity"]["worst_difference"]
        self.assertNotEqual(worst["text"], ToyBackend.text)
        self.assertEqual(worst["model_seed"], ToyBackend.seeds[worst["seed_index"]])
        self.assertAlmostEqual(abs(worst["reference_probability"] - worst["candidate_probability"]),
                               result["parity"]["max_abs_error"])


class TestResume(unittest.TestCase):
    def fixture(self):
        config = {"ids": ["T01", "T02", "T03", "T04"], "padding": ["fixed", "dynamic"],
                  "samples": [200, 500], "seeds": [1, 2, 3], "jaccard_threshold": 0.6}
        sha = lambda value: hashlib.sha256(value).hexdigest()
        metadata = {"config": config, "script_version": "1.0", "planned_fits": 48, "complete": False,
            "sha256_script": experiment.LEGACY_SCRIPT_SHA256,
            "sha256_inference": sha((experiment.ROOT / "src/ml/inference.py").read_bytes()),
            "sha256_ablation_script": sha((experiment.ROOT / "uji_kesetiaan_lime.py").read_bytes()),
            "sha256_corpus": sha(json.dumps(experiment.KORPUS_UJI, sort_keys=True, ensure_ascii=False).encode())}
        fits = [{"id": case_id, "padding": mode, "num_samples": samples, "seed_lime": seed,
                 "status": "ok", "parity": None, "order": n + 1}
                for n, (case_id, mode, samples, seed) in enumerate(experiment.rencana_fits(config)[:34])]
        fits[-1].update(status="paritas_gagal", parity={"toleransi": 1e-6,
            "max_abs_error": 1.0728836059570312e-6, "n_keputusan_berubah": 0, "lulus": False})
        return {"metadata": metadata, "inputs": [{"id": i} for i in config["ids"]], "fits": fits}

    def test_partial_34_plans_only_seven_missing_fixed_without_changing_history(self):
        payload = self.fixture()
        original = copy.deepcopy(payload)
        experiment.periksa_sumber_resume(payload, experiment.KORPUS_UJI)
        pending = experiment.sisa_resume(payload)
        expected = [("T03", "fixed", 500, 3)] + [
            ("T04", "fixed", samples, seed) for samples in (200, 500) for seed in (1, 2, 3)]
        self.assertEqual(pending, expected)
        self.assertEqual(payload, original)
        self.assertEqual(sum(f["status"] == "ok" for f in payload["fits"]), 33)
        self.assertNotIn(experiment.kunci_fit(payload["fits"][-1]), pending)
        self.assertEqual(len(payload["fits"]) + len(pending), 41)

    def test_duplicate_and_out_of_plan_records_are_rejected(self):
        for change in ("duplicate", "outside"):
            payload = self.fixture()
            extra = copy.deepcopy(payload["fits"][0])
            if change == "outside":
                extra["seed_lime"] = 999
            payload["fits"].append(extra)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "duplikat|luar rencana"):
                experiment.sisa_resume(payload)

    def test_changed_source_identity_method_or_tolerance_is_rejected(self):
        for key in ("sha256_script", "sha256_inference", "sha256_ablation_script", "sha256_corpus", "method_version"):
            payload = self.fixture()
            payload["metadata"][key] = "changed"
            with self.subTest(key=key), self.assertRaises(ValueError):
                experiment.periksa_sumber_resume(payload, experiment.KORPUS_UJI)
        payload = self.fixture()
        payload["fits"][-1]["parity"]["toleransi"] = 1e-5
        with self.assertRaisesRegex(ValueError, "toleransi"):
            experiment.periksa_sumber_resume(payload, experiment.KORPUS_UJI)
        for key in ("planned_fits", "inputs"):
            payload = self.fixture()
            if key == "planned_fits":
                payload["metadata"][key] = 1
            else:
                payload[key].pop()
            with self.subTest(key=key), self.assertRaises(ValueError):
                experiment.periksa_sumber_resume(payload, experiment.KORPUS_UJI)

    def test_runtime_identity_requires_same_environment(self):
        previous = {"audit_backend": {"seed": "abc"}, "device": "cpu", "model_seeds": [42, 123, 999],
                    "max_length": 128, "batch_size": 32, "torch_threads": 8,
                    "packages": {"torch": "example", "lime": "example"}}
        experiment.periksa_runtime_resume(previous, copy.deepcopy(previous))
        for key in previous:
            current = copy.deepcopy(previous)
            current[key] = "changed"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                experiment.periksa_runtime_resume(previous, current)

    def test_speed_ratios_do_not_pair_different_sessions(self):
        base = {"id": "T", "num_samples": 200, "seed_lime": 1, "status": "ok", "fit_seconds": 2.0,
                "coefficients": [{"feature_id": 0, "word": "viral", "weight": .2}], "top_words": ["viral"]}
        fixed = {**base, "padding": "fixed", "session_id": "old"}
        dynamic = {**base, "padding": "dynamic", "session_id": "new", "fit_seconds": 1.0}
        self.assertEqual(experiment.perbandingan_padding([fixed, dynamic]), [])
        dynamic["session_id"] = "old"
        result = experiment.perbandingan_padding([fixed, dynamic])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["speed_ratio_fixed_over_dynamic"], 2.0)

if __name__ == "__main__":
    unittest.main()
