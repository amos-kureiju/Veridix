"""Integritas pelaporan API; hanya SQLite memori dan galat database tiruan."""

import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from tests import test_auth_roles as auth_fixture
from src.api.routes import user_routes
from src.database.models import AdminSetting, PredictionLog, ThresholdHistory


class TestReportingIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        auth_fixture.TestLoginRoles.setUpClass()

    def setUp(self):
        # Komposisi fixture menghindari menjalankan ulang seluruh kelas tes autentikasi.
        self.memory = auth_fixture.TestLoginRoles(methodName="runTest")
        self.memory.setUp()
        self.client = self.memory.client

    def tearDown(self):
        self.memory.tearDown()

    def add_prediction(self, label, status="dinilai", ratio=None, owner="USER", text=None):
        with self.memory.session_factory() as db:
            row = PredictionLog(
                user_id=self.memory.ids[owner],
                input_text=text or str(uuid4()),
                input_type="TEXT",
                process_status=status,
                pattern_label=label,
                agreement_ratio=ratio,
                latency_seconds=0.125,
            )
            db.add(row)
            db.commit()

    def add_legacy_threshold(self):
        with self.memory.session_factory() as db:
            db.add(AdminSetting(setting_key="classification_threshold", setting_value="0.83"))
            db.add(ThresholdHistory(
                old_threshold=0.5,
                new_threshold=0.83,
                reason="Pengaturan lama untuk tes",
                modified_by=self.memory.ids["ADMIN"],
            ))
            db.commit()

    def threshold_snapshot(self):
        with self.memory.session_factory() as db:
            setting = db.query(AdminSetting).filter_by(setting_key="classification_threshold").one()
            return setting.setting_value, db.query(ThresholdHistory).count()

    @contextmanager
    def record_sql(self):
        statements = []

        def collect(_conn, _cursor, statement, _parameters, _context, _executemany):
            statements.append(statement)

        event.listen(self.memory.engine, "before_cursor_execute", collect)
        try:
            yield statements
        finally:
            event.remove(self.memory.engine, "before_cursor_execute", collect)

    def assert_only_auth_reads(self, statements):
        self.assertTrue(statements)
        for statement in statements:
            self.assertTrue(statement.lstrip().upper().startswith("SELECT"))
            self.assertNotIn("admin_settings", statement.lower())
            self.assertNotIn("threshold_history", statement.lower())

    def test_stats_count_ambiguity_for_old_and_new_status_case(self):
        for status in ("ambigu", "AMBIGU", "AmBiGu"):
            self.add_prediction("PERLU VERIFIKASI (SEED TIDAK SEPAKAT)", status=status)
        self.add_prediction("BERPOLA HOAKS")
        self.add_prediction("HOAKS")
        self.add_prediction("TIDAK BERPOLA HOAKS")
        self.add_prediction(None, status="ditolak")

        response = self.client.get("/api/v1/admin/stats", headers=self.memory.login("ADMIN"))
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total_detections"], 7)
        self.assertEqual(data["total_ambiguous"], 3)
        self.assertEqual(data["total_hoaxes"], 2)
        self.assertEqual(data["total_facts"], 1)
        self.assertEqual(data["active_threshold"], 0.5)
        self.assertIs(data["threshold_editable"], False)

    def test_threshold_get_reports_frozen_value_without_reading_legacy_setting(self):
        self.add_legacy_threshold()
        headers = self.memory.login("ADMIN")
        before = self.threshold_snapshot()
        with self.record_sql() as statements:
            response = self.client.get("/api/v1/admin/threshold", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["threshold"], 0.5)
        self.assertIs(data["editable"], False)
        self.assertIsNone(data["updated_at"])
        self.assert_only_auth_reads(statements)
        self.assertEqual(self.threshold_snapshot(), before)

    def test_threshold_put_rejects_change_without_writes_or_audit_rows(self):
        self.add_legacy_threshold()
        headers = self.memory.login("ADMIN")
        before = self.threshold_snapshot()
        with self.record_sql() as statements:
            response = self.client.put(
                "/api/v1/admin/threshold", headers=headers,
                json={"new_threshold": 0.7, "reason": "Tidak boleh disimpan"},
            )
        self.assertEqual(response.status_code, 501)
        self.assertIn("dinonaktifkan", response.json()["detail"])
        self.assert_only_auth_reads(statements)
        self.assertEqual(self.threshold_snapshot(), before)

    def test_threshold_endpoints_remain_admin_only(self):
        headers = self.memory.login("USER")
        for supplied_headers, expected in ((headers, 403), ({}, 401)):
            with self.subTest(expected=expected):
                self.assertEqual(self.client.get(
                    "/api/v1/admin/threshold", headers=supplied_headers
                ).status_code, expected)
                self.assertEqual(self.client.put(
                    "/api/v1/admin/threshold", headers=supplied_headers,
                    json={"new_threshold": 0.7},
                ).status_code, expected)

    def test_history_preserves_unknown_zero_and_known_ratios(self):
        self.add_prediction("BERPOLA HOAKS", ratio=None, text="unknown")
        self.add_prediction("TIDAK BERPOLA HOAKS", ratio=0.0, text="actual-zero")
        self.add_prediction("BERPOLA HOAKS", ratio=0.67, text="known")
        self.add_prediction("BERPOLA HOAKS", ratio=0.9, owner="ADMIN", text="another-user")

        response = self.client.get("/api/v1/users/history", headers=self.memory.login("USER"))
        self.assertEqual(response.status_code, 200)
        rows = {row["input_text"]: row for row in response.json()["data"]}
        self.assertEqual(set(rows), {"unknown", "actual-zero", "known"})
        for field in ("agreement_ratio", "confidence_score"):
            self.assertIsNone(rows["unknown"][field])
            self.assertEqual(rows["actual-zero"][field], 0.0)
            self.assertEqual(rows["known"][field], 0.67)

    def test_history_empty_success_only_when_query_really_succeeds(self):
        response = self.client.get("/api/v1/users/history", headers=self.memory.login("USER"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "data": []})


class TestHistoryFailureReporting(unittest.TestCase):
    def test_runtime_failure_is_http_error_and_does_not_expose_private_details(self):
        private_marker = "private-query-parameter-marker"
        db = Mock()
        db.query.side_effect = RuntimeError(private_marker)
        app = FastAPI()
        app.include_router(user_routes.router, prefix="/api/v1")

        def broken_db():
            return db

        app.dependency_overrides[user_routes.get_db] = broken_db
        app.dependency_overrides[user_routes.get_current_user] = lambda: SimpleNamespace(id=uuid4())
        with TestClient(app) as client, self.assertLogs(user_routes.logger, level="ERROR") as logs:
            response = client.get("/api/v1/users/history")

        self.assertEqual(response.status_code, 500)
        self.assertNotIn(private_marker, response.text)
        self.assertNotIn(private_marker, "\n".join(logs.output))
        self.assertNotIn("data", response.json())
        db.rollback.assert_called_once_with()

    def test_sql_failure_reaches_global_handler_instead_of_false_empty_success(self):
        db = Mock()
        failure = OperationalError("SELECT private_marker", {}, RuntimeError("test DB unavailable"))
        db.query.side_effect = failure

        with self.assertRaises(OperationalError) as raised:
            user_routes.get_user_history(db=db, current_user=SimpleNamespace(id=uuid4()))
        self.assertIs(raised.exception, failure)


if __name__ == "__main__":
    unittest.main()
