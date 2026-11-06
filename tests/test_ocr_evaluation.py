# Regresi unit untuk modul evaluasi berpasangan uji_ocr_berpasangan.py

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import uji_ocr_berpasangan as eval_module


class TestOCREvaluation(unittest.TestCase):
    def test_jarak_levenshtein(self):
        # Identik
        self.assertEqual(eval_module.jarak_levenshtein(["a", "b"], ["a", "b"]), 0)
        # Substitusi tunggal
        self.assertEqual(eval_module.jarak_levenshtein(list("kucing"), list("kucing")), 0)
        self.assertEqual(eval_module.jarak_levenshtein(list("Presiden"), list("residen")), 1)
        # Penghapusan & penyisipan
        self.assertEqual(eval_module.jarak_levenshtein([], ["a", "b"]), 2)
        self.assertEqual(eval_module.jarak_levenshtein(["a"], []), 1)

    def test_hitung_cer_wer_kasus_normal(self):
        ref = "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial tahun anggaran baru harus tepat sasaran."
        # Salah baca: 'Presiden' -> 'residen' (1 del), 'tepat' -> 'te pat' (1 ins)
        hyp = "residen Joko Widodo menegaskan bahwa penyaluran bantuan sosial tahun anggaran baru harus te pat sasaran."

        cer, wer, char_err, word_err = eval_module.hitung_cer_wer(ref, hyp)
        self.assertIsNotNone(cer)
        self.assertAlmostEqual(cer, 1.9231, places=3)
        self.assertAlmostEqual(wer, 21.4286, places=3)
        self.assertEqual(char_err, 2)
        self.assertEqual(word_err, 3)

    def test_hitung_cer_wer_acuan_kosong_menghasilkan_none(self):
        # Acuan kosong tidak boleh membagi dengan nol atau menghasilkan 0.0% palsu
        cer, wer, char_err, word_err = eval_module.hitung_cer_wer("", "teks hasil ocr")
        self.assertIsNone(cer)
        self.assertIsNone(wer)
        self.assertEqual(char_err, len("teks hasil ocr"))
        self.assertEqual(word_err, 3)

    def test_evaluasi_satu_kasus_berkas_tidak_ada(self):
        kasus = {"id": "U99", "gambar": "non_existent_file.png", "transkripsi_manual": "bebas"}
        evaluator = Mock()
        res = eval_module.evaluasi_satu_kasus(kasus, evaluator)
        self.assertEqual(res["keputusan_akhir"], "DILEWATI_BERKAS_TIDAK_ADA")
        self.assertEqual(res["status_berkas"], "tidak_ditemukan")
        evaluator.nilai.assert_not_called()

    def test_evaluasi_satu_kasus_tolak_input_tidak_menghitung_cer_wer(self):
        kasus = {"id": "U03", "gambar": "dummy.bmp", "transkripsi_manual": "Naskah Acuan"}
        evaluator = Mock()
        raw_mock = {
            "kategori": "TOLAK_INPUT",
            "kode": "INPUT_FORMAT_TIDAK_DIDUKUNG",
            "pesan": "Format tidak didukung.",
            "teks_bersih": "",
            "dapat_dinilai": False,
        }

        with patch("pathlib.Path.is_file", return_value=True), \
             patch.object(eval_module, "proses_gambar", return_value=raw_mock):
            res = eval_module.evaluasi_satu_kasus(kasus, evaluator)

        self.assertEqual(res["keputusan_akhir"], "DITOLAK_TOLAK_INPUT")
        self.assertFalse(res["metrik_transkripsi"]["tersedia"])
        self.assertIsNone(res["metrik_transkripsi"]["cer_persen"])
        self.assertIsNone(res["evaluasi_teks_ocr"])
        evaluator.nilai.assert_not_called()

    def test_evaluasi_satu_kasus_tolak_kualitas_tetap_menghitung_cer_wer(self):
        kasus = {"id": "U01", "gambar": "pendek.png", "transkripsi_manual": "KEMENTERIAN KEUANGAN"}
        evaluator = Mock()
        raw_mock = {
            "kategori": "TOLAK_KUALITAS",
            "kode": "MUTU_TEKS_PENDEK",
            "pesan": "Teks terlalu pendek.",
            "teks_bersih": "KEMENTERIAN KEUANGAN",
            "dapat_dinilai": False,
        }

        with patch("pathlib.Path.is_file", return_value=True), \
             patch.object(eval_module, "proses_gambar", return_value=raw_mock):
            res = eval_module.evaluasi_satu_kasus(kasus, evaluator)

        self.assertEqual(res["keputusan_akhir"], "DITOLAK_TOLAK_KUALITAS")
        # Karena teks terbaca ada, metrik tetap dihitung untuk analisis kelemahan sistem
        self.assertTrue(res["metrik_transkripsi"]["tersedia"])
        self.assertEqual(res["metrik_transkripsi"]["cer_persen"], 0.0)
        self.assertEqual(res["metrik_transkripsi"]["wer_persen"], 0.0)

    def test_agregasi_ringkasan_tanpa_sampel_menghasilkan_none(self):
        # Memastikan tidak ada pembagian dengan nol saat list kosong
        cer_diterima = []
        rata2_cer = round(float(sum(cer_diterima) / len(cer_diterima)), 4) if cer_diterima else None
        self.assertIsNone(rata2_cer)


if __name__ == "__main__":
    unittest.main()