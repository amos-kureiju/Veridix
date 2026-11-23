# Regresi unit untuk modul evaluasi berpasangan uji_ocr_berpasangan.py

import contextlib
import io
import json
import sys
import tempfile
import unittest
from copy import deepcopy
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


TEXT = "Presiden dan pemerintah membahas kebijakan anggaran bantuan sosial bersama DPR untuk seluruh warga Indonesia."


def model_result(votes=0, **updates):
    result = {
        "success": True,
        "status": "ambigu" if votes in (1, 2) else "dinilai",
        "label": "PERLU VERIFIKASI (SEED TIDAK SEPAKAT)" if votes in (1, 2) else
            "BERPOLA HOAKS" if votes == 3 else "TIDAK BERPOLA HOAKS",
        "votes_hoax": f"{votes}/3",
        "decision_rule": "unanimous",
        "seed_decisions": {seed: int(index < votes) for index, seed in enumerate((42, 123, 999))},
        "agreement_ratio": max(votes, 3 - votes) / 3,
        "latency_seconds": 0.01,
        "teks_dinilai": TEXT,
        "terpotong": False,
    }
    result.update(updates)
    return result


def ocr_result(text=TEXT, category="OK"):
    return {
        "kategori": category,
        "kode": "fixture-" + category,
        "pesan": "Hasil OCR tiruan.",
        "teks_mentah": text,
        "teks_bersih": text,
        "dapat_dinilai": category == "OK",
        "alasan": [],
        "fitur": {"conf_rata2": 0.95},
    }


class TestOCREvaluationMain(unittest.TestCase):
    """Actual runner aggregation/publication using only temporary files and fake engines."""

    def setUp(self):
        self.context = tempfile.TemporaryDirectory()
        self.folder = Path(self.context.name)
        self.manifest = self.folder / "manifest.json"
        self.output = self.folder / "report.json"
        self.evaluator = Mock(rule="unanimous")
        self.evaluator.nilai.side_effect = lambda _text, **_kwargs: model_result()

    def tearDown(self):
        self.context.cleanup()

    def case(self, identifier, ref=TEXT, exists=True):
        image = self.folder / f"{identifier}.png"
        if exists:
            image.write_bytes(b"isolated-fake-image")
        return {"id": identifier, "gambar": str(image), "transkripsi_manual": ref}

    def save_manifest(self, value):
        self.manifest.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def invoke(self, dataset=None, output=None):
        args = ["uji_ocr_berpasangan.py", "--dataset", str(dataset or self.manifest), "--output", str(output or self.output)]
        with patch.object(sys, "argv", args), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return eval_module.main()

    def report(self):
        return json.loads(self.output.read_text(encoding="utf-8"))

    @contextlib.contextmanager
    def engines(self, responses=None):
        responses = responses or {}

        def extract(path):
            response = responses.get(Path(path).stem, ocr_result())
            if isinstance(response, Exception):
                raise response
            return deepcopy(response)

        with patch.object(eval_module, "get_predictor", return_value=self.evaluator) as provider, \
                patch.object(eval_module, "proses_gambar", side_effect=extract) as extract_mock, \
                patch.object(eval_module, "hash_kebijakan", return_value="fixture-policy-hash"):
            yield provider, extract_mock

    def test_main_aggregates_quality_rejections_and_retains_all_denominators(self):
        self.save_manifest([
            self.case("accepted"), self.case("quality"), self.case("input"),
            self.case("engine"), self.case("missing", exists=False),
        ])
        with self.engines({
            "quality": ocr_result("", "TOLAK_KUALITAS"),
            "input": ocr_result("", "TOLAK_INPUT"),
            "engine": ocr_result("", "GALAT_MESIN"),
        }):
            self.assertEqual(self.invoke(), 1)
        report = self.report()
        summary = report["ringkasan"]
        self.assertEqual(summary["total_kasus"], 5)
        for key in ("diterima_ocr", "ditolak_kualitas", "ditolak_input", "galat_mesin", "berkas_tidak_ada"):
            self.assertEqual(summary[key], 1, key)
        self.assertEqual(summary["galat_model"], 0)
        self.assertEqual(summary["galat_eksekusi"], 0)
        self.assertEqual(summary["pasangan_dibandingkan"], 1)
        self.assertEqual(summary["cer_terukur"], 2)
        self.assertEqual(summary["wer_terukur"], 2)
        self.assertEqual(summary["rata2_cer_diterima"], 0.0)
        self.assertEqual(summary["rata2_wer_diterima"], 0.0)
        self.assertEqual(summary["rata2_cer_semua_terukur"], 50.0)
        self.assertEqual(summary["rata2_wer_semua_terukur"], 50.0)
        self.assertEqual(len(report["hasil_evaluasi"]), 5)

    def test_main_without_measurable_pairs_reports_null_means(self):
        self.save_manifest([self.case("missing", exists=False)])
        with self.engines():
            self.assertEqual(self.invoke(), 1)
        summary = self.report()["ringkasan"]
        for key in ("cer_terukur", "wer_terukur", "pasangan_dibandingkan"):
            self.assertEqual(summary[key], 0)
        for key in ("rata2_cer_diterima", "rata2_wer_diterima", "rata2_cer_semua_terukur", "rata2_wer_semua_terukur"):
            self.assertIsNone(summary[key])

    def test_empty_reference_is_valid_but_has_no_ratio_or_model_pair(self):
        self.save_manifest([self.case("empty", ref="")])
        with self.engines():
            self.assertEqual(self.invoke(), 0)
        report = self.report()
        row = report["hasil_evaluasi"][0]
        self.assertEqual(row["transkripsi_manual"], "")
        self.assertIsNone(row["metrik_transkripsi"]["cer_persen"])
        self.assertIsNone(row["metrik_transkripsi"]["wer_persen"])
        self.assertEqual(row["metrik_transkripsi"]["char_errors"], len(TEXT))
        self.assertIsNone(row["konsistensi"]["label_sama"])
        self.assertEqual(report["ringkasan"]["pasangan_dibandingkan"], 0)

    def test_equal_ambiguous_labels_do_not_hide_different_seed_votes(self):
        hyp = TEXT.replace("Presiden", "residen")
        self.save_manifest([self.case("ambiguous")])
        self.evaluator.nilai.side_effect = lambda text, **_kwargs: model_result(1 if text == TEXT else 2)
        with self.engines({"ambiguous": ocr_result(hyp)}):
            self.assertEqual(self.invoke(), 0)
        report = self.report()
        row = report["hasil_evaluasi"][0]
        self.assertEqual(row["keputusan_akhir"], "SELESAI_DIEVALUASI")
        self.assertTrue(row["konsistensi"]["label_sama"])
        self.assertFalse(row["konsistensi"]["votes_sama"])
        self.assertEqual(report["ringkasan"]["pasangan_dibandingkan"], 1)

    def test_normal_model_rejection_does_not_form_a_compared_pair(self):
        hyp = TEXT.replace("Presiden", "residen")
        self.save_manifest([self.case("unscored")])
        rejected = {"success": False, "status": "ditolak", "label": "TIDAK DAPAT DINILAI", "reason": "Teks tidak layak.", "latency_seconds": 0.01}
        self.evaluator.nilai.side_effect = lambda text, **_kwargs: deepcopy(rejected) if text == TEXT else model_result()
        with self.engines({"unscored": ocr_result(hyp)}):
            self.assertEqual(self.invoke(), 0)
        report = self.report()
        self.assertIsNone(report["hasil_evaluasi"][0]["konsistensi"]["label_sama"])
        self.assertEqual(report["ringkasan"]["galat_model"], 0)
        self.assertEqual(report["ringkasan"]["pasangan_dibandingkan"], 0)

    def test_model_failures_and_malformed_outputs_never_look_consistent(self):
        hyp = TEXT.replace("Presiden", "residen")
        self.save_manifest([self.case("model_failure")])
        broken = (RuntimeError("fixture-model-failure"), None, [], {},
                  {"success": False, "status": "gagal", "label": "TIDAK DAPAT DINILAI", "reason": "Galat numerik.", "latency_seconds": 0.01},
                  model_result(label=None), model_result(votes_hoax="3/3"))
        for side in ("manual", "ocr"):
            for result in broken:
                with self.subTest(side=side, result=result):
                    if self.output.exists():
                        self.output.unlink()

                    def classify(text, **_kwargs):
                        failed_side = (text == TEXT) == (side == "manual")
                        if failed_side:
                            if isinstance(result, Exception):
                                raise result
                            return deepcopy(result)
                        return model_result()

                    self.evaluator.nilai.side_effect = classify
                    with self.engines({"model_failure": ocr_result(hyp)}):
                        self.assertEqual(self.invoke(), 1)
                    report = self.report()
                    row = report["hasil_evaluasi"][0]
                    self.assertEqual(row["keputusan_akhir"], "GALAT_MODEL")
                    self.assertIsNone(row["konsistensi"]["label_sama"])
                    self.assertEqual(report["ringkasan"]["galat_model"], 1)
                    self.assertEqual(report["ringkasan"]["galat_eksekusi"], 0)
                    self.assertEqual(report["ringkasan"]["pasangan_dibandingkan"], 0)
                    self.assertEqual(report["ringkasan"]["cer_terukur"], 1)

    def test_ocr_exception_is_counted_and_batch_continues(self):
        self.save_manifest([self.case("first"), self.case("broken"), self.case("last")])
        with self.engines({"broken": RuntimeError("fixture-OCR-failure")}):
            self.assertEqual(self.invoke(), 1)
        report = self.report()
        self.assertEqual(report["ringkasan"]["total_kasus"], 3)
        self.assertEqual(report["ringkasan"]["galat_eksekusi"], 1)
        self.assertEqual(report["ringkasan"]["galat_model"], 0)
        self.assertEqual(report["ringkasan"]["pasangan_dibandingkan"], 2)
        self.assertEqual(report["hasil_evaluasi"][1]["keputusan_akhir"], "GALAT_EKSEKUSI")
        self.assertEqual(report["hasil_evaluasi"][2]["keputusan_akhir"], "SELESAI_DIEVALUASI")

    def test_invalid_manifest_is_rejected_before_any_engine_load(self):
        valid = self.case("valid")
        malformed = (None, {}, [], ["not-an-object"], [{}],
                     [{**valid, "id": ""}], [{**valid, "id": "   "}], [{**valid, "id": 1}],
                     [valid, {**valid}], [{**valid, "gambar": ""}], [{**valid, "gambar": "   "}], [{**valid, "gambar": 1}],
                     [{**valid, "transkripsi_manual": None}],
                     [{key: value for key, value in valid.items() if key != "transkripsi_manual"}])
        for manifest in malformed:
            with self.subTest(manifest=manifest):
                self.save_manifest(manifest)
                with self.engines() as (provider, extract):
                    with self.assertRaises(SystemExit) as caught:
                        self.invoke()
                    self.assertEqual(caught.exception.code, 2)
                    provider.assert_not_called()
                    extract.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_missing_or_invalid_json_manifest_never_uses_default_cases(self):
        for contents in (None, "{not-json"):
            with self.subTest(contents=contents):
                if contents is not None:
                    self.manifest.write_text(contents, encoding="utf-8")
                with self.engines() as (provider, extract):
                    with self.assertRaises(SystemExit) as caught:
                        self.invoke()
                    self.assertEqual(caught.exception.code, 2)
                    provider.assert_not_called()
                    extract.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_existing_report_and_input_paths_are_preserved_before_loading(self):
        case = self.case("protected")
        self.save_manifest([case])
        self.output.write_bytes(b"previous-report-kept-verbatim")
        for output in (self.output, self.manifest, Path(case["gambar"])):
            with self.subTest(output=output):
                previous = output.read_bytes()
                with self.engines() as (provider, extract):
                    with self.assertRaises(SystemExit) as caught:
                        self.invoke(output=output)
                    self.assertEqual(caught.exception.code, 2)
                    provider.assert_not_called()
                    extract.assert_not_called()
                self.assertEqual(output.read_bytes(), previous)

    def test_atomic_publication_failure_leaves_no_partial_report_or_temp_file(self):
        self.save_manifest([self.case("publish")])
        before = set(self.folder.iterdir())
        with self.engines(), patch.object(eval_module.os, "link", side_effect=PermissionError("fixture-publication-failure")):
            self.assertEqual(self.invoke(), 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(set(self.folder.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
