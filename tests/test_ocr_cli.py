"""Regresi CLI OCR memakai mesin/model tiruan dan berkas sementara saja."""

import builtins
import contextlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
TEXT = "Presiden dan pemerintah membahas kebijakan anggaran nasional bersama anggota DPR dalam rapat resmi di Jakarta hari ini."
PAYLOAD = b"fixture-image-bytes\x00"


def ocr_result(text=TEXT, clean_text=None, accepted=True, kode=None, pesan=None):
    cleaned = clean_text if clean_text is not None else text
    kategori = "OK" if accepted else "TOLAK_KUALITAS"
    kd = kode or ("OK" if accepted else "MUTU_CONF_RENDAH")
    msg = pesan or ("Teks berhasil dibaca." if accepted else "Kualitas kepercayaan OCR rendah.")
    return {
        "kategori": kategori,
        "kode": kd,
        "pesan": msg,
        "teks_mentah": text,
        "teks_bersih": cleaned,
        "lines": [text] if isinstance(text, str) else [],
        "scores": [0.95],
        "fitur": {"n_kata": len(cleaned.split()) if isinstance(cleaned, str) else 0, "conf_rata2": 0.95, "conf_min": 0.95},
        "dapat_dinilai": accepted,
        "alasan": [] if accepted else [{"kode": kd, "pesan": msg}],
        "berkas": {"format": "PNG", "lebar": 200, "tinggi": 100, "ukuran_byte": len(PAYLOAD), "sha256": "dummy-sha256"},
        "durasi_detik": {"total": 0.12, "ocr": 0.08, "kualitas": 0.02},
    }


def model_result(**updates):
    result = {
        "success": True, "status": "dinilai", "label": "BERPOLA HOAKS",
        "votes_hoax": "3/3", "teks_dinilai": TEXT, "terpotong": False,
        "debug": {"prob_hoax_per_seed": {42: 0.9, 123: 0.92, 999: 0.93}},
    }
    result.update(updates)
    return result


class TestOCRCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = importlib.import_module("uji_ujung_ke_ujung")

    def setUp(self):
        self.folder_context = tempfile.TemporaryDirectory()
        self.folder = Path(self.folder_context.name)
        self.image = self.folder / "clear.png"
        self.image.write_bytes(PAYLOAD)
        self.output = self.folder / "report.json"

    def tearDown(self):
        self.folder_context.cleanup()

    def invoke(self, *images, extra=(), output=None):
        args = ["--output", str(output or self.output), *extra, *map(str, images)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return self.cli.main(args)

    def report(self):
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_import_does_not_parse_arguments_load_engines_or_write_report(self):
        code = (
            "import sys; from pathlib import Path; "
            "sys.path.insert(0, sys.argv[1]); "
            "before = set(Path.cwd().iterdir()); "
            "import uji_ujung_ke_ujung as cli; "
            "assert callable(cli.main); "
            "assert 'paddleocr' not in sys.modules; "
            "assert 'src.ml.inference' not in sys.modules; "
            "assert sys.modules['src.utils.ocr_extractor']._OCR is None; "
            "assert cli._pred is None; "
            "assert set(Path.cwd().iterdir()) == before"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", code, str(ROOT), "--unknown-option"],
            cwd=self.folder, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_quality_refusal_keeps_record_without_loading_model(self):
        with patch.object(self.cli, "proses_gambar", return_value=ocr_result(accepted=False)), patch.object(self.cli, "model") as provider:
            exit_code = self.invoke(self.image)
        self.assertEqual(exit_code, 0)
        provider.assert_not_called()
        report = self.report()
        self.assertEqual(report["total"], 1)
        self.assertEqual(report["ringkasan"], {"gerbang_kualitas": 1})
        row = report["gambar"][0]
        self.assertEqual(row["teks_ocr_mentah"], TEXT)
        self.assertEqual(row["keputusan"], "TIDAK_LAYAK")
        self.assertIn("kepercayaan", row["alasan"])

    def test_accepted_ocr_uses_path_clean_text_and_requested_lime(self):
        raw = "| " + TEXT + " https://example.com/source ^"
        predictor = Mock()
        predictor.nilai.return_value = model_result(explanation={"explanation_available": True})
        with patch.object(self.cli, "proses_gambar", return_value=ocr_result(text=raw, clean_text=TEXT)) as extract, patch.object(self.cli, "model", return_value=predictor) as provider:
            exit_code = self.invoke(self.image, extra=("--lime",))
        self.assertEqual(exit_code, 0)
        extract.assert_called_once()
        provider.assert_called_once_with()
        predictor.nilai.assert_called_once_with(TEXT, explain=True, debug=True)

        rep = self.report()
        self.assertEqual(rep["versi_pipeline"], self.cli.VERSI_PIPELINE)
        self.assertEqual(rep["hash_kebijakan"], self.cli.hash_kebijakan())

        row = self.report()["gambar"][0]
        self.assertEqual(row["teks_ocr_mentah"], raw)
        self.assertEqual(row["teks_bersih"], TEXT)
        self.assertEqual(row["teks_dinilai"], TEXT)
        self.assertEqual(row["status"], "dinilai")
        self.assertTrue(row["explanation"]["explanation_available"])

        self.assertEqual(row["identitas_berkas"]["format"], "PNG")
        self.assertEqual(row["identitas_berkas"]["sha256"], "dummy-sha256")
        self.assertEqual(row["durasi_detik_pipeline"]["total"], 0.12)

    def test_raw_fifty_character_gate_matches_current_image_endpoint(self):
        text = "a b c d e f g h i j"
        res = ocr_result(text=text, accepted=False, kode="MUTU_TEKS_PENDEK", pesan="kurang dari 50 karakter")
        with patch.object(self.cli, "proses_gambar", return_value=res), patch.object(self.cli, "model") as provider:
            exit_code = self.invoke(self.image)
        self.assertEqual(exit_code, 0)
        provider.assert_not_called()
        self.assertEqual(self.report()["gambar"][0]["tahap_akhir"], "gerbang_kualitas")
        self.assertEqual(self.report()["gambar"][0]["keputusan"], "TIDAK_LAYAK")

    def test_model_refusal_is_preserved_as_normal_result(self):
        predictor = Mock()
        predictor.nilai.return_value = model_result(
            success=False, status="di_luar_domain", label="DI LUAR CAKUPAN",
            reason="Teks di luar topik politik.",
        )
        with patch.object(self.cli, "proses_gambar", return_value=ocr_result()), patch.object(self.cli, "model", return_value=predictor):
            exit_code = self.invoke(self.image)
        self.assertEqual(exit_code, 0)
        row = self.report()["gambar"][0]
        self.assertEqual(row["tahap_akhir"], "model")
        self.assertEqual(row["status"], "di_luar_domain")
        self.assertEqual(row["alasan"], "Teks di luar topik politik.")

    def test_missing_read_and_model_load_errors_preserve_all_rows_and_continue(self):
        missing = self.folder / "missing.png"
        unreadable = self.folder / "unreadable.png"
        bad_model = self.folder / "bad_model.png"
        final_image = self.folder / "final.png"
        for path in (unreadable, bad_model, final_image):
            path.write_bytes(PAYLOAD)

        # Mock proses_gambar: gagal baca pada unreadable, sukses pada yang lain
        def mock_proses(target_path):
            if Path(target_path) == unreadable:
                return {
                    "kategori": "TOLAK_INPUT",
                    "kode": "INPUT_TIDAK_TERBACA",
                    "pesan": "Berkas tidak dapat dibaca.",
                    "teks_mentah": "",
                    "teks_bersih": "",
                    "dapat_dinilai": False,
                }
            return ocr_result()

        predictor = Mock()
        predictor.nilai.return_value = model_result()
        with patch.object(self.cli, "proses_gambar", side_effect=mock_proses) as extract, patch.object(self.cli, "model", side_effect=[RuntimeError("fixture checkpoint failure"), predictor]):
            exit_code = self.invoke(missing, unreadable, bad_model, final_image)

        self.assertEqual(exit_code, 1)
        # missing dicek lewat is_file() sehingga proses_gambar hanya dipanggil untuk 3 berkas yang ada
        self.assertEqual(extract.call_count, 3)
        report = self.report()
        self.assertEqual(report["total"], 4)
        self.assertEqual(sum(report["ringkasan"].values()), 4)
        self.assertEqual(
            [row["tahap_akhir"] for row in report["gambar"]],
            ["berkas_tidak_ada", "input_ditolak", "model_galat", "model"]
        )
        self.assertIn("checkpoint", report["gambar"][2]["galat"])
        self.assertEqual(report["gambar"][3]["status"], "dinilai")

    def test_model_inference_exception_is_recorded_before_next_image(self):
        second = self.folder / "second.png"
        second.write_bytes(PAYLOAD)
        predictor = Mock()
        predictor.nilai.side_effect = [ValueError("fixture backend failure"), model_result()]
        with patch.object(self.cli, "proses_gambar", return_value=ocr_result()), patch.object(self.cli, "model", return_value=predictor):
            exit_code = self.invoke(self.image, second)
        self.assertEqual(exit_code, 1)
        self.assertEqual([r["tahap_akhir"] for r in self.report()["gambar"]], ["model_galat", "model"])

    def test_ocr_engine_returned_and_raised_errors_are_failures_and_continue(self):
        second = self.folder / "second.png"
        third = self.folder / "third.png"
        second.write_bytes(PAYLOAD)
        third.write_bytes(PAYLOAD)
        outputs = [
            {"kategori": "GALAT_MESIN", "kode": "MESIN_GAGAL", "pesan": "fixture DLL failure"},
            RuntimeError("fixture OCR exception"),
            ocr_result(accepted=False)
        ]
        with patch.object(self.cli, "proses_gambar", side_effect=outputs), patch.object(self.cli, "model") as provider:
            exit_code = self.invoke(self.image, second, third)
        self.assertEqual(exit_code, 1)
        provider.assert_not_called()
        rows = self.report()["gambar"]
        self.assertEqual([r["tahap_akhir"] for r in rows], ["ocr_galat", "ocr_galat", "gerbang_kualitas"])
        self.assertEqual([r["keputusan"] for r in rows[:2]], ["GAGAL", "GAGAL"])
        self.assertTrue(all("waktu_ocr_dtk" in r for r in rows))

    def test_report_write_failure_returns_failure(self):
        blocked = self.folder / "regular-file"
        blocked.write_bytes(b"keep")
        with patch.object(self.cli, "proses_gambar", return_value=ocr_result(accepted=False)), patch.object(self.cli, "model") as provider:
            exit_code = self.invoke(self.image, output=blocked / "report.json")
        self.assertEqual(exit_code, 1)
        self.assertEqual(blocked.read_bytes(), b"keep")
        provider.assert_not_called()

    def test_malformed_engine_contracts_are_recorded_as_failures(self):
        # 1. OCR mengembalikan keluaran rusak, teks kosong, salah tipe, atau penanda hilang
        ocr_invalids = [
            None,
            [],
            {"kategori": "OK", "kode": "OK", "teks_bersih": "", "dapat_dinilai": True},
            {"kategori": "OK", "kode": "OK", "teks_bersih": 12345, "dapat_dinilai": True},
            {"kategori": "OK", "kode": "OK", "teks_bersih": TEXT, "dapat_dinilai": None},
        ]
        for invalid in ocr_invalids:
            with self.subTest(engine="OCR", value=invalid), patch.object(self.cli, "proses_gambar", return_value=invalid), patch.object(self.cli, "model") as provider:
                self.assertEqual(self.invoke(self.image), 1)
                self.assertEqual(self.report()["gambar"][0]["tahap_akhir"], "ocr_galat")
                provider.assert_not_called()

        # 2. Model mengembalikan keluaran rusak, dict kosong, atau tanpa status/label
        model_invalids = [
            None,
            [],
            {},
            {"success": True},
        ]
        for invalid in model_invalids:
            predictor = Mock()
            predictor.nilai.return_value = invalid
            with self.subTest(engine="model", value=invalid), patch.object(self.cli, "proses_gambar", return_value=ocr_result()), patch.object(self.cli, "model", return_value=predictor):
                self.assertEqual(self.invoke(self.image), 1)
                self.assertEqual(self.report()["gambar"][0]["tahap_akhir"], "model_galat")  

    def test_atomic_report_replacement_failure_preserves_old_report_and_cleans_temp(self):
        previous = b"previous complete report\n"
        self.output.write_bytes(previous)
        with patch.object(self.cli, "proses_gambar", return_value=ocr_result(accepted=False)), patch.object(self.cli, "model") as provider, patch.object(self.cli.os, "replace", side_effect=PermissionError("fixture replace failure")):
            exit_code = self.invoke(self.image)
        self.assertEqual(exit_code, 1)
        self.assertEqual(self.output.read_bytes(), previous)
        self.assertEqual(list(self.folder.glob("report.json.*.tmp")), [])
        provider.assert_not_called()

    def test_report_cannot_overwrite_input_image(self):
        with patch.object(self.cli, "proses_gambar") as extract, patch.object(self.cli, "model") as provider:
            try:
                exit_code = self.invoke(self.image, output=self.image)
            except SystemExit as exc:
                exit_code = exc.code
        self.assertNotEqual(exit_code, 0)
        self.assertEqual(self.image.read_bytes(), PAYLOAD)
        extract.assert_not_called()
        provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
