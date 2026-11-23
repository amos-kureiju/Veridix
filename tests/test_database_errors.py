"""Regresi respons database/CORS pada app aktual tanpa DB, model, atau OCR asli.

Jalankan dengan ``python -B -X utf8 -m unittest tests.test_database_errors -v``.
TestClient sengaja tidak memasuki lifespan agar migrasi/seeding tidak berjalan.
"""

import importlib
import os
import sys
import unittest
from contextlib import contextmanager
from types import ModuleType
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    ProgrammingError,
    TimeoutError as PoolTimeoutError,
)

# These pure helpers do not initialize the lazy predictor or read checkpoints.
from src.ml.inference import validate_claim_result


_model_stub = ModuleType("src.ml.inference")
_model_stub.predictor = Mock(name="unused_predictor")
_model_stub.validate_claim_result = validate_claim_result
_ocr_stub = ModuleType("src.utils.ocr_extractor")
_ocr_stub.extract_text_from_image = Mock(name="unused_ocr")
_ocr_stub.MAX_BYTES = 10 * 1024 * 1024
_pipeline_stub = ModuleType("src.utils.ocr_pipeline")
_pipeline_stub.proses_gambar = Mock(name="unused_ocr_pipeline")
_pipeline_stub.KATEGORI_OK = "OK"
_pipeline_stub.KATEGORI_INPUT = "TOLAK_INPUT"
_pipeline_stub.KATEGORI_KUALITAS = "TOLAK_KUALITAS"
_pipeline_stub.KATEGORI_MESIN = "GALAT_MESIN"


@contextmanager
def temporary_modules(overrides):
    """Restore only our stubs; retain real dependencies loaded while importing main."""
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in overrides}
    sys.modules.update(overrides)
    try:
        yield
    finally:
        for name, module in previous.items():
            if module is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


with patch.dict(os.environ, {
    "DATABASE_URL": "sqlite://",
    "JWT_SECRET_KEY": "database-error-test-secret-at-least-32-characters",
    "AUTO_CREATE_TABLES": "false",
    "AUTO_SEED_DEMO": "false",
    "CORS_ORIGINS": '["http://localhost:3000","http://127.0.0.1:3000"]',
}), temporary_modules({
    "src.ml.inference": _model_stub,
    "src.utils.ocr_extractor": _ocr_stub,
    "src.utils.ocr_pipeline": _pipeline_stub,
}):
    import main as api_main
    session_module = importlib.import_module("src.database.session")


DATABASE_UNAVAILABLE = "Layanan database sementara tidak tersedia. Silakan coba lagi."
DATABASE_ERROR = "Terjadi kesalahan pada penyimpanan data. Silakan hubungi pengelola sistem."
ALLOWED_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
UNTRUSTED_ORIGIN = "https://untrusted.example"


class DriverError(Exception):
    sqlstate = "42703"


def programming_error():
    return ProgrammingError(
        "SELECT private_password_hash FROM private_users WHERE email=:email",
        {"email": "private-email@example.com", "password": "private-password-marker"},
        DriverError("private-driver-marker: column does not exist"),
    )


def operational_error():
    return OperationalError(
        "SELECT private_connection_marker FROM private_users",
        {"password": "private-password-marker"},
        DriverError("private-driver-marker: connection refused"),
    )


class TestDatabaseErrorResponses(unittest.TestCase):
    def setUp(self):
        self.db = Mock(name="request_session")
        self.session_patch = patch.object(session_module, "SessionLocal", return_value=self.db)
        self.session_factory = self.session_patch.start()
        self.original_overrides = dict(api_main.app.dependency_overrides)
        api_main.app.dependency_overrides.clear()
        self.client = TestClient(api_main.app, raise_server_exceptions=False)
        _model_stub.predictor.reset_mock()
        _ocr_stub.extract_text_from_image.reset_mock()
        _pipeline_stub.proses_gambar.reset_mock()

    def tearDown(self):
        self.client.close()
        self.session_patch.stop()
        api_main.app.dependency_overrides.clear()
        api_main.app.dependency_overrides.update(self.original_overrides)
        _model_stub.predictor.assert_not_called()
        _model_stub.predictor.predict_and_explain.assert_not_called()
        _ocr_stub.extract_text_from_image.assert_not_called()
        _pipeline_stub.proses_gambar.assert_not_called()

    def failed_login(self, error, origin=ALLOWED_ORIGINS[0]):
        self.db.reset_mock()
        self.db.query.side_effect = error
        with self.assertLogs(api_main.logger, level="ERROR") as captured:
            response = self.client.post(
                "/api/v1/auth/login",
                headers={"Origin": origin},
                json={"email": "request@example.com", "password": "request-password-marker"},
            )
        self.db.rollback.assert_called_once_with()
        self.db.close.assert_called_once_with()
        combined = response.text + "\n" + "\n".join(captured.output)
        for secret in (
            "SELECT", "private_password_hash", "private_users", "private-email@example.com",
            "private-password-marker", "private-driver-marker", "private_connection_marker",
            "request-password-marker", "request@example.com",
        ):
            self.assertNotIn(secret, combined)
        self.assertNotIn("Traceback", response.text)
        self.assertTrue(response.headers["content-type"].startswith("application/json"))
        self.assertIn(type(error).__name__, "\n".join(captured.output))
        for record in captured.records:
            self.assertIsNone(record.exc_info)
        return response

    def assert_allowed_cors(self, response, origin):
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_programming_error_is_safe_json_500_with_cors(self):
        for origin in ALLOWED_ORIGINS:
            with self.subTest(origin=origin):
                response = self.failed_login(programming_error(), origin)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json(), {"detail": DATABASE_ERROR})
                self.assertNotIn("retry-after", response.headers)
                self.assert_allowed_cors(response, origin)

    def test_operational_error_is_retryable_json_503_with_cors(self):
        response = self.failed_login(operational_error())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": DATABASE_UNAVAILABLE})
        self.assertEqual(response.headers.get("retry-after"), "5")
        self.assert_allowed_cors(response, ALLOWED_ORIGINS[0])

    def test_pool_timeout_is_retryable_json_503(self):
        response = self.failed_login(PoolTimeoutError("private-driver-marker"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": DATABASE_UNAVAILABLE})
        self.assertEqual(response.headers.get("retry-after"), "5")
        self.assert_allowed_cors(response, ALLOWED_ORIGINS[0])

    def test_disconnection_is_retryable_json_503(self):
        response = self.failed_login(DisconnectionError("private-driver-marker"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": DATABASE_UNAVAILABLE})
        self.assertEqual(response.headers.get("retry-after"), "5")
        self.assert_allowed_cors(response, ALLOWED_ORIGINS[0])

    def test_database_error_does_not_allow_an_unknown_origin(self):
        response = self.failed_login(programming_error(), UNTRUSTED_ORIGIN)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": DATABASE_ERROR})
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_healthy_root_is_unchanged_and_does_not_open_a_session(self):
        response = self.client.get("/", headers={"Origin": ALLOWED_ORIGINS[0]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "online")
        self.assertEqual(response.json()["docs"], "/docs")
        self.assert_allowed_cors(response, ALLOWED_ORIGINS[0])
        self.session_factory.assert_not_called()

    def test_unauthenticated_request_remains_json_401(self):
        response = self.client.get(
            "/api/v1/auth/me", headers={"Origin": ALLOWED_ORIGINS[0]}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIsInstance(response.json()["detail"], str)
        self.assertEqual(response.headers.get("www-authenticate"), "Bearer")
        self.assert_allowed_cors(response, ALLOWED_ORIGINS[0])
        self.db.query.assert_not_called()

    def test_allowed_preflight_remains_successful(self):
        response = self.client.options("/api/v1/auth/login", headers={
            "Origin": ALLOWED_ORIGINS[0],
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assert_allowed_cors(response, ALLOWED_ORIGINS[0])
        self.session_factory.assert_not_called()

    def test_unknown_origin_preflight_is_rejected(self):
        response = self.client.options("/api/v1/auth/login", headers={
            "Origin": UNTRUSTED_ORIGIN,
            "Access-Control-Request-Method": "POST",
        })
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)
        self.session_factory.assert_not_called()

    def test_session_dependency_rolls_back_and_reraises_database_errors(self):
        for error in (programming_error(), operational_error()):
            with self.subTest(error=type(error).__name__):
                self.db.reset_mock()
                dependency = session_module.get_db()
                self.assertIs(next(dependency), self.db)
                with self.assertRaises(type(error)) as caught:
                    dependency.throw(error)
                self.assertIs(caught.exception, error)
                self.db.rollback.assert_called_once_with()
                self.db.close.assert_called_once_with()

    def test_successful_session_dependency_closes_without_rollback(self):
        dependency = session_module.get_db()
        self.assertIs(next(dependency), self.db)
        with self.assertRaises(StopIteration):
            next(dependency)
        self.db.rollback.assert_not_called()
        self.db.close.assert_called_once_with()

    def test_non_database_exception_is_not_swallowed_and_session_is_closed(self):
        dependency = session_module.get_db()
        self.assertIs(next(dependency), self.db)
        with self.assertRaisesRegex(ValueError, "application-error-marker"):
            dependency.throw(ValueError("application-error-marker"))
        self.db.rollback.assert_not_called()
        self.db.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
