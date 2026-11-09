"""Kontrak HTTP OCR dengan pipeline/model tiruan; tanpa OCR atau database asli."""

import asyncio
import io
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Fixture ini mengimpor aplikasi dengan model dan OCR tiruan tanpa lifespan.
from tests import test_database_errors as fixture


routes = fixture.api_main.detection_routes
TEXT = "DPR dan pemerintah membahas kebijakan nasional bersama warga José di Jakarta untuk menjelaskan rencana anggaran."
RAW_MARKER = "private-raw-ocr-marker"


def accepted(**updates):
    result = {
        "kategori": routes.KATEGORI_OK, "kode": "OK", "pesan": "Periksa teks sebelum dianalisis.",
        "dapat_dinilai": True, "teks_bersih": TEXT,
        "teks_mentah": RAW_MARKER, "fitur": {"conf_rata2": 0.91},
        "detail_teknis": None,
    }
    result.update(updates)
    return result


class TestOCRRoutes(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(routes.router, prefix="/api/v1")
        self.app.dependency_overrides[routes.get_current_user] = lambda: SimpleNamespace(id="fixture-user")

        def forbidden_db():
            raise AssertionError("Ekstraksi OCR tidak boleh membuka sesi database")

        self.app.dependency_overrides[routes.get_db] = forbidden_db
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        pipeline_patch = patch.object(routes, "proses_gambar", return_value=accepted())
        self.pipeline = pipeline_patch.start()
        self.addCleanup(pipeline_patch.stop)
        model_patch = patch.object(routes, "_classify_without_lime")
        self.model = model_patch.start()
        self.addCleanup(model_patch.stop)
        log_patch = patch.object(routes, "PredictionLog")
        self.prediction_log = log_patch.start()
        self.addCleanup(log_patch.stop)

    def tearDown(self):
        self.model.assert_not_called()
        self.prediction_log.assert_not_called()

    def upload(self, contents=b"image-fixture", mime="image/png"):
        return self.client.post("/api/v1/detect/image", files={
            "file": ("screenshot.png", io.BytesIO(contents), mime),
        })

    def assert_readable_error(self, response, status_code):
        self.assertEqual(response.status_code, status_code, response.text)
        self.assertIsInstance(response.json()["detail"], str)
        self.assertTrue(response.json()["detail"].strip())
        self.assertNotIn(RAW_MARKER, response.text)

    def test_success_preserves_pipeline_text_and_existing_response_shape(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        self.pipeline.assert_called_once_with(b"image-fixture")
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["data"], {
            "extracted_text": TEXT, "dapat_dinilai": True, "confidence": 0.91,
            "character_count": len(TEXT), "image_url": None, "reason": None,
        })
        self.assertNotIn(RAW_MARKER, response.text)

    def test_category_and_code_mapping_keeps_error_detail_string(self):
        cases = [
            (routes.KATEGORI_INPUT, "INPUT_UKURAN_BERKAS", 413),
            (routes.KATEGORI_INPUT, "INPUT_TIDAK_TERBACA", 400),
            (routes.KATEGORI_INPUT, "INPUT_FORMAT_TIDAK_DIDUKUNG", 400),
            (routes.KATEGORI_KUALITAS, "MUTU_TEKS_PENDEK", 422),
            (routes.KATEGORI_KUALITAS, "MUTU_CONF_RENDAH", 422),
            (routes.KATEGORI_MESIN, "MESIN_GAGAL", 503),
            (routes.KATEGORI_MESIN, "MESIN_KELUARAN_TIDAK_VALID", 500),
            ("UNKNOWN", "UNKNOWN", 500),
        ]
        for category, code, expected in cases:
            with self.subTest(category=category, code=code):
                self.pipeline.return_value = dict(kategori=category, kode=code, pesan="Gunakan gambar lain.")
                self.assert_readable_error(self.upload(), expected)

    def test_empty_bytes_reach_shared_input_validation(self):
        self.pipeline.return_value = dict(kategori=routes.KATEGORI_INPUT, kode="INPUT_KOSONG", pesan="Berkas kosong.")
        self.assert_readable_error(self.upload(b""), 400)
        self.pipeline.assert_called_once_with(b"")

    def test_unsupported_mime_is_rejected_before_pipeline(self):
        self.assert_readable_error(self.upload(mime="image/gif"), 400)
        self.pipeline.assert_not_called()

    def test_bounded_read_accepts_exact_limit_and_rejects_one_byte_over(self):
        with patch.object(routes, "MAX_BYTES", 8):
            self.assertEqual(self.upload(b"x" * 8).status_code, 200)
            self.pipeline.assert_called_once_with(b"x" * 8)
            self.pipeline.reset_mock()
            self.assert_readable_error(self.upload(b"x" * 9), 413)
            self.pipeline.assert_not_called()

    def test_upload_read_failure_is_friendly_without_running_pipeline(self):
        with patch("starlette.datastructures.UploadFile.read", new=AsyncMock(side_effect=OSError(RAW_MARKER))), self.assertLogs(routes.logger, level="ERROR") as logs:
            response = self.upload()
        self.assert_readable_error(response, 400)
        self.pipeline.assert_not_called()
        self.assertNotIn(RAW_MARKER, "\n".join(logs.output))

    def test_pipeline_exception_is_friendly_without_logging_raw_exception(self):
        self.pipeline.side_effect = RuntimeError(RAW_MARKER)
        with self.assertLogs(routes.logger, level="ERROR") as logs:
            response = self.upload()
        self.assert_readable_error(response, 500)
        self.assertNotIn(RAW_MARKER, "\n".join(logs.output))

    def test_non_dict_and_inconsistent_ok_never_become_success(self):
        bad_results = [None, [RAW_MARKER], accepted(dapat_dinilai=False),
                       accepted(dapat_dinilai=None), accepted(dapat_dinilai=1),
                       accepted(teks_bersih=None), accepted(teks_bersih="   "),
                       accepted(fitur=None), accepted(fitur=[RAW_MARKER])]
        missing_flag = accepted()
        del missing_flag["dapat_dinilai"]
        bad_results.append(missing_flag)
        for result in bad_results:
            with self.subTest(result_type=type(result).__name__), self.assertLogs(routes.logger, level="ERROR") as logs:
                self.pipeline.return_value = result
                self.assert_readable_error(self.upload(), 500)
                self.assertNotIn(RAW_MARKER, "\n".join(logs.output))

    def test_confidence_is_optional_but_when_present_must_be_numeric_and_finite(self):
        for value in (None, 0, 1, 0.75):
            with self.subTest(valid=value):
                self.pipeline.return_value = accepted(fitur={"conf_rata2": value})
                self.assertEqual(self.upload().status_code, 200)
        for value in (True, "0.9", float("nan"), float("inf"), -0.1, 1.1, 10**1000):
            with self.subTest(invalid_type=type(value).__name__):
                self.pipeline.return_value = accepted(fitur={"conf_rata2": value})
                self.assert_readable_error(self.upload(), 500)

    def test_missing_or_malformed_messages_have_string_fallback(self):
        for message in (None, [], "", "   "):
            with self.subTest(message_type=type(message).__name__):
                self.pipeline.return_value = dict(kategori=routes.KATEGORI_KUALITAS, kode="MUTU_TEKS_PENDEK", pesan=message)
                self.assert_readable_error(self.upload(), 422)
                self.pipeline.return_value = accepted(pesan=message)
                response = self.upload()
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["message"].strip())

    def test_technical_report_and_raw_text_are_not_logged_or_returned(self):
        # 1. Kasus keluaran minimal (fitur & teks hilang): tepat 1 log, metrik None, marker tidak bocor
        self.pipeline.return_value = dict(
            kategori=routes.KATEGORI_KUALITAS, kode="MUTU_CONF_RENDAH", pesan="Gambar kurang jelas.",
            detail_teknis=RAW_MARKER, teks_mentah=RAW_MARKER, laporan={"text": RAW_MARKER},
        )
        with self.assertLogs(routes.logger, level="WARNING") as logs_min:
            response_min = self.upload()
        self.assert_readable_error(response_min, 422)
        self.assertEqual(len(logs_min.records), 1)
        log_minimal = "\n".join(logs_min.output)
        self.assertNotIn(RAW_MARKER, log_minimal)
        self.assertIn("karakter=None", log_minimal)
        self.assertIn("kata=None", log_minimal)
        self.assertIn("conf=None", log_minimal)

        # 2. Kasus metrik valid lengkap (kata=2, conf=0.88): tercatat tepat dan marker tidak bocor
        self.pipeline.return_value = dict(
            kategori=routes.KATEGORI_KUALITAS, kode="MUTU_TEKS_PENDEK", pesan="Teks terlalu pendek.",
            teks_bersih="Kutipan berita", fitur={"n_kata": 2, "conf_rata2": 0.88},
            detail_teknis=RAW_MARKER, teks_mentah=RAW_MARKER,
        )
        with self.assertLogs(routes.logger, level="WARNING") as logs_valid:
            response_valid = self.upload()
        self.assert_readable_error(response_valid, 422)
        self.assertEqual(len(logs_valid.records), 1)
        log_valid = "\n".join(logs_valid.output)
        self.assertNotIn(RAW_MARKER, log_valid)
        self.assertIn("karakter=14", log_valid)
        self.assertIn("kata=2", log_valid)
        self.assertIn("conf=0.88", log_valid)

        # 3. Kasus kata negatif terisolasi (kata=-2, conf=0.88): kata menjadi None, conf tetap tercatat
        self.pipeline.return_value = dict(
            kategori=routes.KATEGORI_KUALITAS, kode="MUTU_CONF_RENDAH", pesan="Gambar kurang jelas.",
            teks_bersih="abc", fitur={"n_kata": -2, "conf_rata2": 0.88},
            detail_teknis=RAW_MARKER, teks_mentah=RAW_MARKER,
        )
        with self.assertLogs(routes.logger, level="WARNING") as logs_kata:
            response_kata = self.upload()
        self.assert_readable_error(response_kata, 422)
        self.assertEqual(len(logs_kata.records), 1)
        log_kata = "\n".join(logs_kata.output)
        self.assertNotIn(RAW_MARKER, log_kata)
        self.assertIn("karakter=3", log_kata)
        self.assertIn("kata=None", log_kata)
        self.assertIn("conf=0.88", log_kata)

        # 4. Kasus conf tidak valid terisolasi (kata=2, conf=NaN / Inf / di luar [0,1]): kata tetap tercatat, conf menjadi None
        for inv_conf in (float("nan"), float("inf"), 1.2, -0.1, "0.8", True):
            with self.subTest(invalid_conf=inv_conf):
                self.pipeline.return_value = dict(
                    kategori=routes.KATEGORI_KUALITAS, kode="MUTU_CONF_RENDAH", pesan="Gambar kurang jelas.",
                    teks_bersih="abc", fitur={"n_kata": 2, "conf_rata2": inv_conf},
                    detail_teknis=RAW_MARKER, teks_mentah=RAW_MARKER,
                )
                with self.assertLogs(routes.logger, level="WARNING") as logs_conf:
                    response_conf = self.upload()
                self.assert_readable_error(response_conf, 422)
                self.assertEqual(len(logs_conf.records), 1)
                log_conf = "\n".join(logs_conf.output)
                self.assertNotIn(RAW_MARKER, log_conf)
                self.assertIn("karakter=3", log_conf)
                self.assertIn("kata=2", log_conf)
                self.assertIn("conf=None", log_conf)

        # 5. Kasus nilai nol yang sah (teks kosong, kata=0, conf=0.0): dicatat sebagai 0 dan 0.0 (bukan None)
        self.pipeline.return_value = dict(
            kategori=routes.KATEGORI_KUALITAS, kode="MUTU_TIDAK_ADA_TEKS", pesan="Tidak ada teks.",
            teks_bersih="", fitur={"n_kata": 0, "conf_rata2": 0.0},
            detail_teknis=RAW_MARKER, teks_mentah=RAW_MARKER,
        )
        with self.assertLogs(routes.logger, level="WARNING") as logs_zero:
            response_zero = self.upload()
        self.assert_readable_error(response_zero, 422)
        self.assertEqual(len(logs_zero.records), 1)
        log_zero = "\n".join(logs_zero.output)
        self.assertNotIn(RAW_MARKER, log_zero)
        self.assertIn("karakter=0", log_zero)
        self.assertIn("kata=0", log_zero)
        self.assertIn("conf=0.0", log_zero)

    def test_pipeline_runs_outside_the_event_loop_thread(self):
        threads = []

        def pipeline(_contents):
            threads.append(threading.get_ident())
            return accepted()

        async def request():
            loop_thread = threading.get_ident()
            upload = SimpleNamespace(content_type="image/png", read=AsyncMock(return_value=b"fixture"))
            response = await routes.extract_text_from_image_upload(file=upload, current_user=SimpleNamespace(id="fixture-user"))
            upload.read.assert_awaited_once_with(routes.MAX_BYTES + 1)
            return loop_thread, response

        self.pipeline.side_effect = pipeline
        loop_thread, response = asyncio.run(request())
        self.assertNotEqual(threads, [loop_thread])
        self.assertEqual(len(threads), 1)
        self.assertEqual(response.data.extracted_text, TEXT)

    def test_guest_cannot_run_ocr(self):
        del self.app.dependency_overrides[routes.get_current_user]
        self.assert_readable_error(self.upload(), 401)
        self.pipeline.assert_not_called()


if __name__ == "__main__":
    unittest.main()
