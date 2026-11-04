"""Regresi eksperimen LIME; backend tiruan, tanpa checkpoint, database, atau jaringan."""
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

if __name__ == "__main__":
    unittest.main()
