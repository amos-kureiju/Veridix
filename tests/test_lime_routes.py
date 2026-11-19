"""Regresi handler LIME/metadata dengan sesi dan predictor tiruan.

Tidak membuka database, kamera, checkpoint, atau lifespan aplikasi. Fixture impor
menonaktifkan startup/seeding dan mengganti mesin model/OCR sebelum mengimpor app.
"""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from tests import test_database_errors as fixture


routes = fixture.api_main.detection_routes
TEXT = (
    "Presiden dan pemerintah membahas kebijakan bantuan sosial bersama anggota "
    "DPR untuk menjelaskan penyaluran anggaran kepada masyarakat."
)


class RecordingLock:
    def __init__(self, events, acquired=True, on_acquire=None):
        self.events = events
        self.acquired = acquired
        self.on_acquire = on_acquire
        self.active = False
        self.release_count = 0

    def acquire(self, **kwargs):
        self.events.append("acquire")
        if self.acquired:
            self.active = True
            if self.on_acquire:
                self.on_acquire()
        return self.acquired

    def release(self):
        if not self.active:
            raise AssertionError("Lock dilepas tanpa dimiliki")
        self.events.append("release")
        self.release_count += 1
        self.active = False


class TestLimeRoutes(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.user = SimpleNamespace(id=uuid4())
        self.log = SimpleNamespace(
            id=uuid4(), user_id=self.user.id, input_text=TEXT,
            process_status="dinilai", lime_explanation=None,
        )
        self.explanation = {
            "explanation_available": True,
            "tokens": [{"word": "Presiden", "weight": 0.2, "influence": "KE_HOAKS"}],
            "teks_dijelaskan": TEXT,
        }
        self.db = Mock()
        self.db.query.return_value.filter.return_value.first.return_value = self.log
        self.db.refresh.side_effect = lambda _log: self.events.append("refresh")
        self.db.commit.side_effect = lambda: self.events.append("commit")
        self.lock = RecordingLock(self.events)
        self.explain = Mock(return_value=self.explanation)
        self.predictor_patch = patch.object(routes, "predictor", SimpleNamespace(explain=self.explain))
        self.lock_patch = patch.object(routes, "_lime_lock", self.lock)
        self.predictor_patch.start()
        self.lock_patch.start()
        self.addCleanup(self.predictor_patch.stop)
        self.addCleanup(self.lock_patch.stop)

    def request(self):
        return routes.explain_detection(self.log.id, db=self.db, current_user=self.user)

    def test_new_explanation_commits_once_before_releasing_lock(self):
        response = self.request()
        self.assertEqual(response.status, "success")
        self.assertEqual(response.explanation, self.explanation)
        self.explain.assert_called_once_with(TEXT)
        self.db.commit.assert_called_once_with()
        self.db.rollback.assert_not_called()
        self.assertEqual(self.events, ["acquire", "refresh", "commit", "release"])
        self.assertEqual(self.lock.release_count, 1)

    def test_cached_explanation_does_not_acquire_lock_compute_or_commit(self):
        self.log.lime_explanation = self.explanation
        response = self.request()
        self.assertEqual(response.explanation, self.explanation)
        self.explain.assert_not_called()
        self.db.refresh.assert_not_called()
        self.db.commit.assert_not_called()
        self.assertEqual(self.events, [])

    def test_cache_populated_while_waiting_is_rechecked_without_computation(self):
        # Simulasi interleaving: request pertama menyimpan saat request kedua menunggu.
        saved = {}
        self.lock.on_acquire = lambda: saved.update(explanation=self.explanation)

        def refresh(log):
            self.events.append("refresh")
            log.lime_explanation = saved["explanation"]

        self.db.refresh.side_effect = refresh
        response = self.request()
        self.assertEqual(response.explanation, self.explanation)
        self.explain.assert_not_called()
        self.db.commit.assert_not_called()
        self.assertEqual(self.events, ["acquire", "refresh", "release"])

    def test_non_boolean_cached_availability_does_not_count_as_success(self):
        self.log.lime_explanation = {"explanation_available": "false", "tokens": []}
        response = self.request()
        self.assertEqual(response.explanation, self.explanation)
        self.explain.assert_called_once_with(TEXT)
        self.db.commit.assert_called_once_with()

    def test_busy_lock_returns_503_without_computation_or_release(self):
        self.lock.acquired = False
        with self.assertRaises(HTTPException) as caught:
            self.request()
        self.assertEqual(caught.exception.status_code, 503)
        self.explain.assert_not_called()
        self.db.refresh.assert_not_called()
        self.db.commit.assert_not_called()
        self.assertEqual(self.events, ["acquire"])

    def test_failed_model_releases_lock_and_does_not_log_private_exception(self):
        marker = "private-input-from-model-exception"
        self.explain.side_effect = RuntimeError(marker)
        with self.assertLogs(routes.logger, level="ERROR") as logs:
            with self.assertRaises(HTTPException) as caught:
                self.request()
        self.assertEqual(caught.exception.status_code, 500)
        self.assertNotIn(marker, " ".join(logs.output))
        self.db.commit.assert_not_called()
        self.assertIsNone(self.log.lime_explanation)
        self.assertFalse(self.lock.active)

    def test_unavailable_or_malformed_explanation_is_not_saved(self):
        for result in (
            None, [], {}, {"explanation_available": False},
            {"explanation_available": "true"}, {"explanation_available": 1},
        ):
            with self.subTest(result=result):
                self.explain.return_value = result
                with self.assertRaises(HTTPException) as caught:
                    self.request()
                self.assertEqual(caught.exception.status_code, 502)
                self.db.commit.assert_not_called()
                self.assertIsNone(self.log.lime_explanation)
                self.assertFalse(self.lock.active)

    def test_commit_error_rolls_back_and_propagates_to_database_handler(self):
        failure = SQLAlchemyError("test-commit-error")
        self.db.commit.side_effect = failure
        with self.assertRaises(SQLAlchemyError) as caught:
            self.request()
        self.assertIs(caught.exception, failure)
        self.db.commit.assert_called_once_with()
        self.db.rollback.assert_called_once_with()
        self.assertEqual(self.lock.release_count, 1)
        self.assertFalse(self.lock.active)

    def test_refresh_error_rolls_back_and_does_not_compute(self):
        failure = SQLAlchemyError("test-refresh-error")
        self.db.refresh.side_effect = failure
        with self.assertRaises(SQLAlchemyError) as caught:
            self.request()
        self.assertIs(caught.exception, failure)
        self.explain.assert_not_called()
        self.db.commit.assert_not_called()
        self.db.rollback.assert_called_once_with()
        self.assertFalse(self.lock.active)

    def test_missing_or_unrated_record_does_not_compute(self):
        self.db.query.return_value.filter.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as caught:
            self.request()
        self.assertEqual(caught.exception.status_code, 404)
        self.db.query.return_value.filter.return_value.first.return_value = self.log
        self.log.process_status = "ditolak"
        with self.assertRaises(HTTPException) as caught:
            self.request()
        self.assertEqual(caught.exception.status_code, 409)
        self.explain.assert_not_called()
        self.assertEqual(self.events, [])

    def test_text_response_preserves_known_and_unknown_truncation(self):
        result = {
            "success": True, "status": "dinilai", "label": "TIDAK BERPOLA HOAKS",
            "agreement_ratio": 1.0, "latency_seconds": 0.1,
            "votes_hoax": "0/3", "decision_rule": "unanimous",
            "seed_decisions": {42: 0, 123: 0, 999: 0},
            "teks_dinilai": TEXT,
        }
        payload = routes.TextDetectionRequest(text=TEXT)

        def log_factory(**kwargs):
            return SimpleNamespace(id=uuid4(), created_at=datetime.now(timezone.utc), **kwargs)

        with patch.object(routes, "PredictionLog", side_effect=log_factory), \
                patch.object(routes, "check_political_domain", return_value=(True, "kebijakan", [])), \
                patch.object(routes, "_classify_without_lime", return_value=result):
            for raw, expected in ((True, True), (False, False), (None, None), ("false", None), (0, None)):
                with self.subTest(raw=raw):
                    result["terpotong"] = raw
                    response = routes.detect_text(payload, db=self.db, current_user=self.user)
                    self.assertIs(response.data.terpotong, expected)
            result.pop("terpotong")
            response = routes.detect_text(payload, db=self.db, current_user=self.user)
            self.assertIsNone(response.data.terpotong)


if __name__ == "__main__":
    unittest.main()
