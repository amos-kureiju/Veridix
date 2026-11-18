"""Kontrak teks/LIME dan metadata pemotongan; backend tiruan tanpa checkpoint/DB."""

import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from src.ml import inference
from src.utils.input_validation import validate_input_text
from src.utils.praproses import praproses


TEXT = (
    "Presiden bersama jajaran menteri dan anggota DPR membahas kebijakan "
    "anggaran bantuan sosial untuk masyarakat di Indonesia."
)
MISSING = object()


def evaluator(token_count=40, *, sambung=False):
    backend = SimpleNamespace(
        seeds=[42, 123, 999],
        seed_probs_each=Mock(return_value=np.array([[0.2, 0.3, 0.1]])),
    )
    if token_count is not MISSING:
        backend.count_tokens = Mock(return_value=token_count)
    return inference.Penilai(backend, sambung_tanda_hubung=sambung), backend


class TestExplanationTextContract(unittest.TestCase):
    def test_rejected_input_never_reaches_lime_or_backend(self):
        # The former fallback admitted the three-word example and long raw text.
        for text in (None, "", "Presiden mengumumkan bansos", TEXT * 400):
            with self.subTest(text_type=type(text).__name__, length=len(text or "")):
                penilai, backend = evaluator()
                with patch.object(penilai, "_lime") as explain:
                    result = penilai.explain_text(text)
                self.assertFalse(result["explanation_available"])
                self.assertEqual(result["tokens"], [])
                self.assertIn("tidak layak", result["error"].lower())
                explain.assert_not_called()
                backend.seed_probs_each.assert_not_called()

    def test_input_that_becomes_short_after_cleaning_cannot_be_explained(self):
        text = " ".join(["<span>"] * 8) + " Presiden mengumumkan bansos"
        self.assertTrue(validate_input_text(text)["ok"])
        self.assertLess(len(praproses(text).split()), 10)
        penilai, backend = evaluator()
        with patch.object(penilai, "_lime") as explain:
            result = penilai.explain_text(text)
        self.assertFalse(result["explanation_available"])
        explain.assert_not_called()
        backend.seed_probs_each.assert_not_called()

    def test_classification_and_lime_receive_same_sanitized_preprocessed_text(self):
        text = TEXT.replace("Presiden", "Pr\u0435siden\u200b") + " " + "kebijakan nasional " * 30
        sanitized = validate_input_text(text)
        self.assertTrue(sanitized["ok"])
        prepared = praproses(sanitized["text"])
        self.assertNotIn("\u0435", prepared)
        self.assertNotIn("\u200b", prepared)
        penilai, backend = evaluator()
        explanation = {"explanation_available": True, "tokens": [], "teks_dijelaskan": prepared}
        with patch.object(penilai, "_lime", return_value=explanation) as explain:
            result = penilai.nilai(text, explain=True)
            standalone = penilai.explain_text(text)
        self.assertTrue(result["success"])
        self.assertEqual(result["teks_dinilai"], prepared)
        self.assertEqual(result["explanation"], standalone)
        self.assertEqual([call.args[0] for call in explain.call_args_list], [prepared, prepared])
        backend.seed_probs_each.assert_called_once_with([prepared])
        backend.count_tokens.assert_called_once_with(prepared)


class TestTruncationMetadata(unittest.TestCase):
    def test_known_token_counts_distinguish_boundary_from_truncation(self):
        for count, expected in ((0, False), (128, False), (129, True), (np.int64(129), True)):
            with self.subTest(count=count):
                penilai, backend = evaluator(count)
                result = penilai.nilai(TEXT, debug=True)
                self.assertTrue(result["success"])
                self.assertIs(result["terpotong"], expected)
                self.assertIs(result["debug"]["pemotongan"]["terpotong_token"], expected)
                backend.seed_probs_each.assert_called_once_with([praproses(TEXT)])

    def test_missing_or_invalid_token_count_is_unknown_without_changing_decision(self):
        for count in (MISSING, None, True, np.bool_(False), -1, 12.0, "12", float("nan")):
            with self.subTest(count=repr(count)):
                penilai, backend = evaluator(count)
                result = penilai.nilai(TEXT, debug=True)
                self.assertTrue(result["success"])
                self.assertEqual(result["status"], "dinilai")
                self.assertEqual(result["label"], "TIDAK BERPOLA HOAKS")
                self.assertEqual(result["votes_hoax"], "0/3")
                self.assertEqual(result["agreement_ratio"], 1.0)
                self.assertIsNone(result["terpotong"])
                self.assertIsNone(result["debug"]["pemotongan"]["terpotong_token"])
                backend.seed_probs_each.assert_called_once_with([praproses(TEXT)])

    def test_token_count_exception_does_not_invalidate_valid_classification(self):
        penilai, backend = evaluator()
        backend.count_tokens.side_effect = RuntimeError("Pengukuran token tiruan gagal")
        result = penilai.nilai(TEXT, debug=True)
        self.assertTrue(result["success"])
        self.assertIsNone(result["terpotong"])
        self.assertIsNone(result["debug"]["pemotongan"]["terpotong_token"])

    def test_word_limit_is_measured_after_cleaning_instead_of_raw_tags(self):
        text = " ".join(["<span>"] * 55) + " " + TEXT
        self.assertGreater(len(text.split()), inference.MAX_WORDS)
        self.assertLessEqual(len(praproses(text).split()), inference.MAX_WORDS)
        penilai, backend = evaluator(40)
        result = penilai.nilai(text, debug=True)
        self.assertTrue(result["success"])
        self.assertIs(result["terpotong"], False)
        self.assertIs(result["debug"]["pemotongan"]["terpotong_kata"], False)
        self.assertEqual(result["teks_dinilai"], praproses(text))
        backend.seed_probs_each.assert_called_once_with([praproses(text)])

    def test_known_word_truncation_remains_true_when_token_measurement_is_unknown(self):
        text = TEXT + " " + "kebijakan nasional " * 30
        penilai, backend = evaluator(None)
        result = penilai.nilai(text, debug=True)
        self.assertTrue(result["success"])
        self.assertIs(result["terpotong"], True)
        self.assertIs(result["debug"]["pemotongan"]["terpotong_kata"], True)
        self.assertIsNone(result["debug"]["pemotongan"]["terpotong_token"])
        backend.seed_probs_each.assert_called_once_with([praproses(text)])

    def test_trailing_punctuation_removed_before_word_boundary_is_measured(self):
        words = TEXT.rstrip(".").split()
        text = " ".join(words + ["nasional"] * (inference.MAX_WORDS - len(words))) + " :"
        self.assertEqual(len(text.split()), inference.MAX_WORDS + 1)
        prepared = praproses(text)
        self.assertEqual(len(prepared.split()), inference.MAX_WORDS)
        penilai, backend = evaluator(40)
        result = penilai.nilai(text, debug=True)
        self.assertTrue(result["success"])
        self.assertIs(result["terpotong"], False)
        self.assertIs(result["debug"]["pemotongan"]["terpotong_kata"], False)
        self.assertEqual(result["teks_dinilai"], prepared)
        backend.seed_probs_each.assert_called_once_with([prepared])

    def test_optional_hyphen_joining_uses_same_word_count_order_as_preprocessing(self):
        text = " ".join(["kata"] * 59) + " me- netapkan"
        self.assertTrue(inference._pemotongan_kata(text, False))
        self.assertFalse(inference._pemotongan_kata(text, True))

    def test_word_measurement_failure_is_unknown_unless_token_truncation_is_known(self):
        for token_count, expected in ((40, None), (129, True)):
            with self.subTest(token_count=token_count):
                penilai, backend = evaluator(token_count)
                broken_metadata_pipeline = SimpleNamespace(clean=Mock(side_effect=RuntimeError("diagnostik gagal")))
                with patch.object(inference, "tp", broken_metadata_pipeline):
                    result = penilai.nilai(TEXT, debug=True)
                self.assertTrue(result["success"])
                self.assertIs(result["terpotong"], expected)
                self.assertIsNone(result["debug"]["pemotongan"]["terpotong_kata"])
                backend.seed_probs_each.assert_called_once_with([praproses(TEXT)])


class TestDocumentExplanation(unittest.TestCase):
    def setUp(self):
        self.backend = SimpleNamespace(
            seeds=list(inference.SEEDS),
            count_tokens=Mock(side_effect=lambda text: 2 + len(text.split())),
            seed_probs_each=Mock(),
            seed_probs_each_untruncated=Mock(),
            allow_unverified=False,
            audit={
                "base_revision": inference.EXPECTED_BASE_REVISION,
                "text_pipeline_sha256": inference.EXPECTED_PIPELINE_SHA256,
                **{f"sha256_seed_{seed}": digest for seed, digest in inference.EXPECTED_SHA256.items()},
            },
        )
        self.penilai = inference.Penilai(self.backend)

    def test_original_source_and_variants_use_strict_model_path(self):
        original = "Klarifikasi: DPR tidak pernah mengumumkan."
        variants = [original, "Klarifikasi: DPR pernah mengumumkan.", ""]
        self.backend.seed_probs_each_untruncated.return_value = [
            [0.2, 0.4, 0.6], [0.5, 0.75, 1], [0, 0, 0],
        ]
        explanation = SimpleNamespace(
            as_list=Mock(return_value=[("DPR", 0.125), ("tidak", -0.375)]),
            score=0.8, intercept={1: 0.2}, local_pred=[0.41],
        )

        def explain(text, classifier, **kwargs):
            self.assertEqual(text, original)
            self.assertEqual(kwargs["labels"], (1,))
            self.assertEqual(kwargs["num_samples"], inference.LIME_NUM_SAMPLES)
            np.testing.assert_allclose(classifier(variants), [[0.6, 0.4], [0.25, 0.75], [1.0, 0.0]])
            return explanation

        lime_module = ModuleType("lime.lime_text")
        lime_module.LimeTextExplainer = Mock(return_value=SimpleNamespace(explain_instance=explain))
        prior_explainer = Mock()
        self.penilai._explainer = prior_explainer
        with patch.dict(sys.modules, {"lime": ModuleType("lime"), "lime.lime_text": lime_module}), \
                patch.object(self.penilai, "siapkan_teks", side_effect=AssertionError("unexpected preprocessing")):
            result = self.penilai.explain_document_segment(original, token_count=7)

        self.assertTrue(result["explanation_available"])
        self.assertEqual(result["teks_dijelaskan"], original)
        self.assertEqual(result["tokens"], [
            {"word": "DPR", "weight": 0.125, "influence": "KE_HOAKS"},
            {"word": "tidak", "weight": -0.375, "influence": "KE_TIDAK_HOAKS"},
        ])
        self.assertEqual(result["diagnostik"]["local_r2"], 0.8)
        self.backend.seed_probs_each_untruncated.assert_called_once_with(variants, [7, 6, 2])
        self.backend.seed_probs_each.assert_not_called()
        self.assertIs(self.penilai._explainer, prior_explainer)
        prior_explainer.explain_instance.assert_not_called()

    def test_invalid_original_is_not_explained(self):
        cases = [
            ("", 2), (" ".join(["teks"] * 61), 63), ("teks", 2), ("teks", True), ("teks", 3.0),
        ]
        with patch.object(self.penilai, "_lime") as explain:
            for text, count in cases:
                with self.subTest(count=count):
                    result = self.penilai.explain_document_segment(text, count)
                    self.assertFalse(result["explanation_available"])
                    self.assertEqual(result["tokens"], [])
            explain.assert_not_called()

    def test_overlong_variant_fails_before_forward(self):
        self.backend.count_tokens.side_effect = None
        self.backend.count_tokens.return_value = inference.MAX_LEN + 1
        with self.assertRaisesRegex(ValueError, "Jumlah token"):
            self.penilai._mean_document_probs(["varian terlalu panjang"])
        self.backend.seed_probs_each_untruncated.assert_not_called()

    def test_invalid_scores_cannot_produce_document_weights(self):
        for scores in ([[0.1, 0.2]], [[True, True, True]], [[0.1, np.nan, 0.2]], [[0, 0, 1.01]]):
            with self.subTest(scores=scores):
                self.backend.seed_probs_each_untruncated.return_value = scores
                with self.assertRaisesRegex(ValueError, "Skor model"):
                    self.penilai._mean_document_probs(["teks segmen"])

    def test_identity_depends_on_config_and_verified_backend(self):
        identity = self.penilai.document_model_identity()
        self.assertRegex(identity, r"^[0-9a-f]{64}$")
        with patch.object(inference, "LIME_NUM_SAMPLES", inference.LIME_NUM_SAMPLES + 1):
            self.assertNotEqual(self.penilai.document_model_identity(), identity)
        self.backend.allow_unverified = True
        self.assertIsNone(self.penilai.document_model_identity())
        self.backend.allow_unverified = False
        self.backend.audit["sha256_seed_42"] = "changed-checkpoint"
        self.assertIsNone(self.penilai.document_model_identity())


if __name__ == "__main__":
    unittest.main()
