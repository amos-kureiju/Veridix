"""Kontrak teks/LIME dan metadata pemotongan; backend tiruan tanpa checkpoint/DB."""

import unittest
from types import SimpleNamespace
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


if __name__ == "__main__":
    unittest.main()
