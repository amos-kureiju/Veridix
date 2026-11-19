"""Text-route contracts with mocked inference/session, without app lifespan or real data."""

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from tests import test_database_errors as fixture


routes = fixture.api_main.detection_routes
TEXT = (
    "Presiden dan pemerintah membahas kebijakan bantuan sosial bersama anggota "
    "DPR untuk menjelaskan penyaluran anggaran kepada masyarakat."
)


def valid_result(votes=0, rule="unanimous"):
    """Explicit expected outcomes; no checkpoint or model implementation is invoked."""
    if rule == "unanimous" and votes in (1, 2):
        status, label = "ambigu", "PERLU VERIFIKASI (SEED TIDAK SEPAKAT)"
    else:
        status = "dinilai"
        label = "BERPOLA HOAKS" if votes >= 2 else "TIDAK BERPOLA HOAKS"
    return {
        "success": True,
        "status": status,
        "label": label,
        "seed_decisions": {seed: int(index < votes) for index, seed in enumerate((42, 123, 999))},
        "decision_rule": rule,
        "votes_hoax": f"{votes}/3",
        "agreement_ratio": max(votes, 3 - votes) / 3,
        "latency_seconds": 0.0,
        "teks_dinilai": TEXT,
        "terpotong": False,
    }


class TestTextDetectionIntegrity(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.pending = []
        self.committed = []
        self.user = SimpleNamespace(id=uuid4())
        self.db = Mock(name="isolated_request_session")
        self.db.add.side_effect = self.add
        self.db.flush.side_effect = self.flush
        self.db.commit.side_effect = self.commit
        self.db.rollback.side_effect = self.rollback

        self.original_overrides = dict(fixture.api_main.app.dependency_overrides)
        fixture.api_main.app.dependency_overrides.clear()
        fixture.api_main.app.dependency_overrides[routes.get_current_user] = lambda: self.user

        def make_log(**values):
            return SimpleNamespace(id=None, created_at=None, **values)

        response_type = routes.DetectionResponse

        def make_response(*args, **kwargs):
            response = response_type(*args, **kwargs)
            self.events.append("response_validated")
            return response

        patches = (
            patch.object(fixture.session_module, "SessionLocal", return_value=self.db),
            patch.object(routes, "PredictionLog", side_effect=make_log),
            patch.object(routes, "DetectionResponse", side_effect=make_response),
            patch.object(routes, "check_political_domain", return_value=(True, "kebijakan", [])),
            patch.object(routes, "_classify_without_lime", return_value=valid_result()),
        )
        self.patchers = list(patches)
        self.patched = [patcher.start() for patcher in self.patchers]
        self.classify = self.patched[-1]
        # Do not enter TestClient as a context manager: app startup/seeding must not run.
        self.client = TestClient(fixture.api_main.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        for patcher in reversed(self.patchers):
            patcher.stop()
        fixture.api_main.app.dependency_overrides.clear()
        fixture.api_main.app.dependency_overrides.update(self.original_overrides)

    def add(self, row):
        self.events.append("add")
        self.pending.append(row)

    def flush(self):
        self.events.append("flush")
        for row in self.pending:
            row.id = uuid4()
            row.created_at = datetime.now(timezone.utc)

    def commit(self):
        self.events.append("commit")
        self.committed.extend(deepcopy(self.pending))
        self.pending.clear()

    def rollback(self):
        self.events.append("rollback")
        self.pending.clear()

    def post(self, **extra):
        return self.client.post("/api/v1/detect/text", json={"text": TEXT, **extra})

    def reset_recording(self):
        self.events.clear()
        self.pending.clear()
        self.committed.clear()
        self.db.reset_mock()

    def assert_no_write(self):
        self.db.add.assert_not_called()
        self.db.flush.assert_not_called()
        self.db.commit.assert_not_called()
        self.assertEqual(self.committed, [])

    def test_both_supported_rules_preserve_every_valid_vote_outcome(self):
        for rule in ("unanimous", "majority"):
            for votes in range(4):
                with self.subTest(rule=rule, votes=votes):
                    self.reset_recording()
                    result = valid_result(votes, rule)
                    self.classify.return_value = result
                    response = self.post()
                    self.assertEqual(response.status_code, 200, response.text)
                    body = response.json()
                    self.assertEqual(body["status"], "success")
                    self.assertEqual(body["data"]["process_status"], result["status"])
                    self.assertEqual(body["data"]["pattern_label"], result["label"])
                    self.assertEqual(body["data"]["votes_hoax"], result["votes_hoax"])
                    self.assertEqual(body["data"]["agreement_ratio"], result["agreement_ratio"])
                    self.assertEqual(body["data"]["latency_seconds"], 0.0)
                    self.assertEqual(self.events, ["add", "flush", "response_validated", "commit"])
                    self.assertEqual(len(self.committed), 1)
                    self.db.rollback.assert_not_called()

    def test_missing_or_malformed_model_output_never_writes_a_log(self):
        cases = [None, [], {}, {**valid_result(), "success": 1}, {**valid_result(), "success": False}]
        for key in ("success", "status", "label", "seed_decisions", "decision_rule", "votes_hoax", "agreement_ratio", "latency_seconds"):
            result = valid_result()
            result.pop(key)
            cases.append(result)
        for result in cases:
            with self.subTest(result=result):
                self.reset_recording()
                self.classify.return_value = result
                response = self.post()
                self.assertEqual(response.status_code, 500, response.text)
                self.assert_no_write()
                self.db.rollback.assert_called_once_with()

    def test_contradictory_decision_metadata_never_writes_a_log(self):
        changes = (
            {"status": "unknown"}, {"status": "ambigu"}, {"label": "BERPOLA HOAKS"},
            {"label": "FAKTA"}, {"decision_rule": "unknown"}, {"votes_hoax": "3/3"},
            {"votes_hoax": "0/2"}, {"agreement_ratio": 2 / 3},
            {"seed_decisions": {42: 0, 123: 0}},
            {"seed_decisions": {42: 0, 123: 0, 999: 0, 7: 0}},
            {"seed_decisions": {"42": 0, "123": 0, "999": 0}},
            {"seed_decisions": {42: False, 123: 0, 999: 0}},
            {"seed_decisions": {42: 0.0, 123: 0, 999: 0}},
            {"seed_decisions": {42: 2, 123: 0, 999: 0}},
        )
        for change in changes:
            with self.subTest(change=change):
                self.reset_recording()
                self.classify.return_value = {**valid_result(), **change}
                response = self.post()
                self.assertEqual(response.status_code, 500, response.text)
                self.assert_no_write()
                self.db.rollback.assert_called_once_with()

    def test_invalid_numeric_measurements_never_become_zero_or_success(self):
        for key, values in (
            ("agreement_ratio", (None, True, "1", -0.1, 1.1, float("nan"), float("inf"))),
            ("latency_seconds", (None, False, "0", -0.01, float("nan"), float("inf"))),
        ):
            for value in values:
                with self.subTest(key=key, value=value):
                    self.reset_recording()
                    self.classify.return_value = {**valid_result(), key: value}
                    response = self.post()
                    self.assertEqual(response.status_code, 500, response.text)
                    self.assert_no_write()
                    self.db.rollback.assert_called_once_with()

    def test_proper_input_rejections_are_saved_without_model_decision_metadata(self):
        for process_status, label in (
            ("ditolak", "TIDAK DAPAT DINILAI"),
            ("di_luar_domain", "DI LUAR CAKUPAN (BUKAN TOPIK POLITIK)"),
        ):
            with self.subTest(process_status=process_status):
                self.reset_recording()
                self.classify.return_value = {
                    "success": False, "status": process_status, "label": label,
                    "reason": "Informasi tidak memenuhi kelayakan analisis.",
                    "latency_seconds": 0.01,
                }
                response = self.post()
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["status"], "rejected")
                self.assertEqual(body["data"]["process_status"], process_status)
                for key in ("pattern_label", "agreement_ratio", "seed_decisions", "votes_hoax"):
                    self.assertIsNone(body["data"][key])
                self.assertEqual(self.events, ["add", "flush", "response_validated", "commit"])
                self.assertIsNone(self.committed[0].pattern_label)
                self.assertIsNone(self.committed[0].agreement_ratio)

    def test_predictor_exception_has_no_success_or_private_diagnostic(self):
        marker = "private-fixture-engine-message"
        self.classify.side_effect = RuntimeError(marker)
        with self.assertLogs(routes.logger, level="ERROR") as captured:
            response = self.post()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(marker, response.text + " ".join(captured.output))
        self.assert_no_write()
        self.db.rollback.assert_called_once_with()

    def test_request_fields_cannot_replace_model_decision_or_owner(self):
        foreign_id = uuid4()
        response = self.post(
            user_id=str(foreign_id), process_status="dinilai", pattern_label="BERPOLA HOAKS",
            votes_hoax="3/3", agreement_ratio=0.0,
        )
        self.assertEqual(response.status_code, 200, response.text)
        saved = self.committed[0]
        self.assertEqual(saved.user_id, self.user.id)
        self.assertEqual(saved.input_text, TEXT)
        self.assertEqual(saved.pattern_label, "TIDAK BERPOLA HOAKS")
        self.assertEqual(saved.agreement_ratio, 1.0)

    def test_response_validation_failure_rolls_back_before_commit(self):
        self.db.flush.side_effect = lambda: self.events.append("flush_without_generated_id")
        response = self.post()
        self.assertEqual(response.status_code, 500, response.text)
        self.db.add.assert_called_once()
        self.db.flush.assert_called_once_with()
        self.db.commit.assert_not_called()
        self.db.rollback.assert_called_once_with()
        self.assertEqual(self.pending, [])
        self.assertEqual(self.committed, [])

    def test_flush_database_failure_rolls_back_without_committing(self):
        self.db.flush.side_effect = OperationalError("fixture query", {}, RuntimeError("fixture database down"))
        response = self.post()
        self.assertEqual(response.status_code, 503, response.text)
        self.db.rollback.assert_called_once_with()
        self.db.commit.assert_not_called()
        self.assertEqual(self.pending, [])
        self.assertEqual(self.committed, [])

    def test_commit_database_failure_is_not_reported_as_success(self):
        self.db.commit.side_effect = SQLAlchemyError("fixture commit failure")
        response = self.post()
        self.assertEqual(response.status_code, 500, response.text)
        self.db.rollback.assert_called_once_with()
        self.assertIn("response_validated", self.events)
        self.assertEqual(self.pending, [])
        self.assertEqual(self.committed, [])


if __name__ == "__main__":
    unittest.main()
