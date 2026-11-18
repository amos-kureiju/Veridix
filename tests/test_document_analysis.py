import math
import re
import threading
import unittest
from unittest.mock import Mock, patch

import numpy as np

from src.ml import document_analysis
from src.ml.inference import BackendIndoBERT, MAX_LEN, Penilai


class StubBackend:
    seeds = [42, 123, 999]

    def __init__(self):
        self.received = []

    def count_tokens(self, text):
        # Each word normally consumes one token. The cost suffix models subwords.
        return 2 + sum(
            int(word.removeprefix("subword")) if word.startswith("subword") else 1
            for word in text.split()
        )

    def seed_probs_each_untruncated(self, texts, token_counts):
        actual_counts = [self.count_tokens(text) for text in texts]
        if actual_counts != token_counts or any(count > MAX_LEN for count in actual_counts):
            raise ValueError("Unexpected tokenization")
        self.received.extend(texts)
        return np.full((len(texts), len(self.seeds)), 0.1)


def block(text, start_char=0, pages=None):
    return {"text": text, "start_char": start_char, "pages": pages or []}


class DocumentAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.backend = StubBackend()
        self.predictor = Penilai(self.backend, decision_rule="unanimous")

    def analyze(self, *blocks):
        return document_analysis.analyze_document(blocks, self.predictor)

    def test_500_words_preserve_exact_source_including_negation_and_unicode(self):
        paragraphs = [" ".join(f"kata{i}" for i in range(215))]
        paragraphs.append("🙂 Klarifikasi: pejabat tidak pernah menyatakan hal tersebut.")
        paragraphs.append(" ".join(f"nomor{i}" for i in range(330)))
        text = " \t" + "\r\n\r\n".join(paragraphs) + "\n"
        segments = self.analyze(block(text))
        expected_words = list(re.finditer(r"\S+", text))

        self.assertEqual(segments[-1]["end_word"], len(expected_words))
        self.assertEqual([s["text"] for s in segments], self.backend.received)
        next_word = 1
        for segment in segments:
            start_word, end_word = segment["start_word"], segment["end_word"]
            self.assertEqual(start_word, next_word)
            self.assertLessEqual(end_word - start_word + 1, 60)
            self.assertEqual(segment["start_char"], expected_words[start_word - 1].start())
            self.assertEqual(segment["end_char"], expected_words[end_word - 1].end())
            self.assertEqual(segment["text"], text[segment["start_char"]:segment["end_char"]])
            self.assertEqual(segment["status"], "dinilai")
            next_word = end_word + 1
        self.assertIn(paragraphs[1], self.backend.received)

    def test_prefers_sentence_boundary_before_word_cap(self):
        sentence = " ".join(["kata"] * 39 + ["selesai."])
        second = " ".join(["lanjutan"] * 28)
        segments = self.analyze(block(f"{sentence} {second}"))
        self.assertEqual([s["text"] for s in segments], [sentence, second])

    def test_exact_token_limit_and_long_single_word(self):
        text = "subword60 subword66 subword127 kata berikut"
        first, rejected, last = self.analyze(block(text))
        self.assertEqual((first["text"], first["token_count"]), ("subword60 subword66", 128))
        self.assertEqual((rejected["text"], rejected["token_count"]), ("subword127", 129))
        self.assertEqual(rejected["status"], "ditolak")
        self.assertIsNone(rejected["label"])
        self.assertIsNone(rejected["votes_hoax"])
        self.assertEqual(last["text"], "kata berikut")
        self.assertNotIn(rejected["text"], self.backend.received)

    def test_limit_reports_every_unprocessed_word_in_each_remaining_block(self):
        a, b, c = (" ".join([word] * 70) for word in ("pertama", "kedua", "ketiga"))
        with patch.object(document_analysis, "MAX_DOCUMENT_SEGMENTS", 2):
            segments = self.analyze(
                block(a), block(b, start_char=len(a) + 3),
                block(c, start_char=len(a) + len(b) + 6),
            )
        self.assertEqual([(s["start_word"], s["end_word"]) for s in segments], [
            (1, 60), (61, 70), (71, 140), (141, 210),
        ])
        self.assertEqual([s["status"] for s in segments], [
            "dinilai", "dinilai", "belum_dinilai", "belum_dinilai",
        ])
        self.assertEqual([s["text"] for s in segments[2:]], [b, c])
        self.assertEqual(len(self.backend.received), 2)

    def test_page_offsets_and_words_continue_across_different_blocks(self):
        first = "satu dua"
        second = "tiga"
        last = "empat lima"
        segments = self.analyze(
            block(f"{first} {second}", pages=[(1, 0, len(first)), (2, len(first) + 1, 13)]),
            block(last, start_char=19, pages=[(4, 19, 19 + len(last))]),
        )
        self.assertEqual([s["page_numbers"] for s in segments], [[1, 2], [4]])
        self.assertEqual([s["text"] for s in segments], [f"{first} {second}", last])
        self.assertEqual([s["start_word"] for s in segments], [1, 4])
        self.assertEqual([s["start_char"] for s in segments], [0, 19])

    def test_empty_document_and_control_only_words_are_not_scored(self):
        self.assertEqual(self.analyze(block(" \t\n\r")), [])
        first, invisible, last = self.analyze(block("awal \u200b akhir"))
        self.assertEqual([first["status"], invisible["status"], last["status"]], [
            "dinilai", "ditolak", "dinilai",
        ])
        self.assertEqual(self.backend.received, ["awal", "akhir"])

    def test_empty_content_tokens_are_explicitly_rejected(self):
        self.backend.count_tokens = Mock(return_value=2)
        segment, = self.analyze(block("acak yang tidak ditokenisasi"))
        self.assertEqual(segment["status"], "ditolak")
        self.assertEqual(segment["token_count"], 2)
        self.assertFalse(self.backend.received)

    def test_tokenizer_failure_keeps_range_and_does_not_fabricate_result(self):
        self.backend.count_tokens = lambda text: {
            "": 2, "teks bermasalah": None, "berikutnya": 3,
        }[text]
        failed, okay = self.analyze(block("teks bermasalah\n\nberikutnya"))
        self.assertEqual(failed["status"], "gagal")
        self.assertEqual(failed["text"], "teks bermasalah")
        self.assertIsNone(failed["token_count"])
        self.assertIsNone(failed["label"])
        self.assertEqual(okay["status"], "dinilai")
        self.assertEqual(self.backend.received, ["berikutnya"])

    def test_votes_and_invalid_scores(self):
        self.backend.seed_probs_each_untruncated = Mock(return_value=[
            [0.5, 0.49, 0.5], [0.5, 0.6, 1], [math.nan, 0.1, 0.1], [0.2, 1.1, 0.3],
        ])
        ambiguous, hoax, nan, out_of_range = self.analyze(block("a\n\nb\n\nc\n\nd"))
        self.assertEqual((ambiguous["status"], ambiguous["votes_hoax"]), ("ambigu", "2/3"))
        self.assertEqual((hoax["status"], hoax["label"], hoax["votes_hoax"]),
                         ("dinilai", "BERPOLA HOAKS", "3/3"))
        for segment in (nan, out_of_range):
            self.assertEqual(segment["status"], "gagal")
            self.assertIsNone(segment["label"])
            self.assertIsNone(segment["votes_hoax"])

    def test_failed_batch_preserves_subsequent_batches(self):
        self.backend.seed_probs_each_untruncated = Mock(side_effect=[ValueError(), [[0, 0, 0]]])
        with patch.object(document_analysis, "BATCH", 1):
            failed, okay = self.analyze(block("pertama\n\nkedua"))
        self.assertEqual(failed["status"], "gagal")
        self.assertEqual((okay["status"], okay["votes_hoax"]), ("dinilai", "0/3"))

    def test_non_numeric_model_matrix_is_not_interpreted_as_votes(self):
        for scores in ([["0", "0", "0"]], [[False, False, False]]):
            with self.subTest(scores=scores):
                self.backend.seed_probs_each_untruncated = Mock(return_value=scores)
                segment, = self.analyze(block("teks contoh"))
                self.assertEqual(segment["status"], "gagal")
                self.assertIsNone(segment["votes_hoax"])

    def test_backend_checks_token_count_before_model_forward(self):
        backend = BackendIndoBERT.__new__(BackendIndoBERT)
        backend._lock = threading.Lock()
        backend.torch = Mock()
        backend.seeds = [42, 123, 999]
        mask = Mock(shape=(1, MAX_LEN))
        mask.sum.return_value.tolist.return_value = [4]
        backend.tokenizer = Mock(return_value={
            "input_ids": Mock(shape=(1, MAX_LEN)),
            "attention_mask": mask,
        })
        with self.assertRaisesRegex(ValueError, "Tokenisasi batch tidak sesuai"):
            backend.seed_probs_each_untruncated(["teks contoh"], [5])
        backend.tokenizer.assert_called_once_with(
            ["teks contoh"], max_length=MAX_LEN, padding="max_length",
            truncation=False, return_tensors="pt",
        )
        backend.torch.no_grad.assert_not_called()


if __name__ == "__main__":
    unittest.main()
