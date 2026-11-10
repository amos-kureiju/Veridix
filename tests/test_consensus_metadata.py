"""tests/test_consensus_metadata.py — Uji kalkulasi rasio konsensus agreement_ratio."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from src.ml.inference import Penilai


class MockBackend:
    def __init__(self, seeds, probs_map):
        self.seeds = seeds
        self.probs_map = probs_map

    def seed_probs_each(self, texts):
        # Kembalikan probabilitas tiruan sesuai konfigurasi kasus
        return np.array([self.probs_map])


class TestConsensusMetadata(unittest.TestCase):
    def setUp(self):
        self.seeds = [42, 123, 999]
        self.valid_political_text = (
            "Presiden Joko Widodo bersama jajaran menteri dan anggota DPR menggelar rapat "
            "evaluasi anggaran bantuan sosial pangan nasional di Jakarta."
        )

    def _eval(self, probs):
        backend = MockBackend(self.seeds, probs)
        penilai = Penilai(backend, decision_rule="unanimous")
        return penilai.nilai(self.valid_political_text)

    # 1. Suara bulat 3/3 (hoaks) -> rasio 1.0
    def test_unanimous_hoax_ratio_is_one(self):
        res = self._eval([0.85, 0.90, 0.95])
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "dinilai")
        self.assertEqual(res["label"], "BERPOLA HOAKS")
        self.assertEqual(res["votes_hoax"], "3/3")
        self.assertEqual(res["agreement_ratio"], 1.0)

    # 2. Suara bulat 0/3 (fakta) -> rasio 1.0
    def test_unanimous_fact_ratio_is_one(self):
        res = self._eval([0.10, 0.15, 0.20])
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "dinilai")
        self.assertEqual(res["label"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(res["votes_hoax"], "0/3")
        self.assertEqual(res["agreement_ratio"], 1.0)

    # 3. Suara ambigu 2/3 -> rasio 2/3 (0.6667)
    def test_ambiguous_two_of_three_ratio(self):
        res = self._eval([0.80, 0.85, 0.20])
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "ambigu")
        self.assertEqual(res["label"], "PERLU VERIFIKASI (SEED TIDAK SEPAKAT)")
        self.assertEqual(res["votes_hoax"], "2/3")
        self.assertAlmostEqual(res["agreement_ratio"], 2 / 3, places=5)

    # 4. Suara ambigu 1/3 -> rasio 2/3 (0.6667)
    def test_ambiguous_one_of_three_ratio(self):
        res = self._eval([0.80, 0.20, 0.25])
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "ambigu")
        self.assertEqual(res["label"], "PERLU VERIFIKASI (SEED TIDAK SEPAKAT)")
        self.assertEqual(res["votes_hoax"], "1/3")
        self.assertAlmostEqual(res["agreement_ratio"], 2 / 3, places=5)

    # 5. Model tidak dijalankan (di luar domain politik) -> agreement_ratio adalah None
    def test_out_of_domain_has_no_agreement_ratio(self):
        backend = MockBackend(self.seeds, [0.9, 0.9, 0.9])
        penilai = Penilai(backend)
        res = penilai.nilai("Resep cara memasak rendang daging sapi padang empuk dan lezat sekali.")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "di_luar_domain")
        self.assertIsNone(res.get("agreement_ratio"))

    # 6. Model tidak dijalankan (teks terlalu pendek) -> agreement_ratio adalah None
    def test_short_text_has_no_agreement_ratio(self):
        backend = MockBackend(self.seeds, [0.9, 0.9, 0.9])
        penilai = Penilai(backend)
        res = penilai.nilai("Teks pendek.")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "ditolak")
        self.assertIsNone(res.get("agreement_ratio"))

   # 7. Backend tidak boleh dipanggil sama sekali jika masukan ditolak sebelum model
    def test_backend_not_called_when_text_rejected(self):
        backend_mock = Mock()
        penilai = Penilai(backend_mock)
        res = penilai.nilai(
            "Resep memasak rendang daging sapi yang empuk "
            "dengan santan dan rempah khas Minang."
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "di_luar_domain")
        backend_mock.seed_probs_each.assert_not_called()
        self.assertIsNone(res.get("agreement_ratio"))

    # 8. Ambang batas tepat 0.5 dianggap bernilai 1 (ke arah hoaks) sesuai aturan biner
    def test_probability_exactly_point_five_threshold(self):
        res = self._eval([0.5, 0.5, 0.5])
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "dinilai")
        self.assertEqual(res["label"], "BERPOLA HOAKS")
        self.assertEqual(res["votes_hoax"], "3/3")
        self.assertEqual(res["agreement_ratio"], 1.0)

    # 9. Anomali numerik (keluaran kosong atau NaN) ditolak tanpa rasio konsensus
    def test_computation_anomalies_rejected_without_consensus(self):
        backend_mock = Mock()
        backend_mock.seeds = self.seeds
        penilai = Penilai(backend_mock)

        # Keluaran kosong
        backend_mock.seed_probs_each.return_value = []
        res_empty = penilai.nilai(self.valid_political_text)
        self.assertFalse(res_empty["success"])
        self.assertIsNone(res_empty.get("agreement_ratio"))

        # Keluaran memuat NaN
        backend_mock.seed_probs_each.return_value = np.array([[0.8, float("nan"), 0.9]])
        res_nan = penilai.nilai(self.valid_political_text)
        self.assertFalse(res_nan["success"])
        self.assertIsNone(res_nan.get("agreement_ratio"))


if __name__ == "__main__":
    unittest.main()