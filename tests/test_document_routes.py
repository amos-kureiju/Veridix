"""Kontrak HTTP naskah dengan model tiruan dan autentikasi terisolasi."""

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

with patch.dict(os.environ, {
    "DATABASE_URL": "sqlite://",
    "JWT_SECRET_KEY": "local-document-test-secret-at-least-32-characters",
}):
    from src.api.routes import detection_routes
    from src.core.auth_deps import get_current_user
    from src.database.session import get_db

from src.ml.inference import Penilai
from tests.test_document_analysis import StubBackend


DOCUMENT_PATH = "/api/v1/detect/document"
POLITICAL_TEXT = (
    "DPR dan pemerintah membahas anggaran bantuan sosial di rapat terbuka bersama warga "
    "untuk menjelaskan manfaat program dan jadwal penyaluran."
)


class DocumentRouteTests(unittest.TestCase):
    def setUp(self):
        self.backend = StubBackend()
        self.predictor = Penilai(self.backend, decision_rule="unanimous")
        model = patch("src.ml.inference.get_predictor", return_value=self.predictor)
        model.start()
        self.addCleanup(model.stop)

        self.app = FastAPI()
        self.app.include_router(detection_routes.router, prefix="/api/v1")
        self.app.dependency_overrides[get_current_user] = lambda: object()

        def unexpected_db():
            raise AssertionError("Analisis naskah sesi tidak boleh mengakses penyimpanan.")

        self.app.dependency_overrides[get_db] = unexpected_db
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_requires_access_token(self):
        del self.app.dependency_overrides[get_current_user]
        response = self.client.post(DOCUMENT_PATH, json={"text": POLITICAL_TEXT})
        self.assertEqual(response.status_code, 401)

    def test_500_words_and_final_clarification_are_scored(self):
        words = POLITICAL_TEXT.split()
        ending = "Klarifikasi: DPR tidak pernah mengumumkan keputusan itu kepada warga.".split()
        text = " ".join((words * 30)[:500 - len(ending)] + ending)
        response = self.client.post(DOCUMENT_PATH, json={"text": text})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual((data["status"], data["total_words"], data["analyzed_words"]), ("lengkap", 500, 500))
        self.assertEqual([word for s in data["segments"] for word in s["text"].split()], text.split())
        self.assertTrue(all(len(s["text"].split()) <= 60 and s["token_count"] <= 128 for s in data["segments"]))
        self.assertTrue(self.backend.received[-1].endswith("tidak pernah mengumumkan keputusan itu kepada warga."))

    def test_result_keeps_gap_when_page_three_is_missing(self):
        texts = ["🙂 " + POLITICAL_TEXT, POLITICAL_TEXT, None, "  " + POLITICAL_TEXT]
        response = self.client.post(DOCUMENT_PATH, json={
            "pages": [{"page_number": number, "text": text} for number, text in enumerate(texts, 1)],
        })
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual((data["status"], data["missing_pages"]), ("parsial", [3]))
        self.assertEqual(data["total_words"], data["analyzed_words"])
        segments = data["segments"]
        self.assertEqual(sorted({p for s in segments for p in s["page_numbers"]}), [1, 2, 4])
        last = segments[-1]
        self.assertEqual(last["page_numbers"], [4])
        self.assertEqual(last["start_char"], len(texts[0]) + len(texts[1]) + 6)

    def test_photos_all_present(self):
        response = self.client.post(DOCUMENT_PATH, json={
            "pages": [{"page_number": number, "text": POLITICAL_TEXT} for number in range(1, 5)],
        })
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual((data["status"], data["missing_pages"]), ("lengkap", []))
        self.assertEqual(data["analyzed_words"], 4 * len(POLITICAL_TEXT.split()))
        self.assertEqual(sorted({p for s in data["segments"] for p in s["page_numbers"]}), [1, 2, 3, 4])

    def test_rejection_and_request_limits(self):
        cases = [
            ({"text": POLITICAL_TEXT, "pages": [{"page_number": 1, "text": POLITICAL_TEXT}]}, 422),
            ({"pages": [{"page_number": 2, "text": POLITICAL_TEXT}]}, 422),
            ({"pages": [{"page_number": 1, "text": " "}]}, 422),
            ({"pages": [{"page_number": number, "text": POLITICAL_TEXT} for number in range(1, 6)]}, 422),
            ({"text": POLITICAL_TEXT * 1000}, 413),
        ]
        for payload, status in cases:
            with self.subTest(status=status, fields=list(payload)):
                self.assertEqual(self.client.post(DOCUMENT_PATH, json=payload).status_code, status)

        out_of_scope = self.client.post(DOCUMENT_PATH, json={
            "text": "Saya menanam pohon di kebun dan menyiram tanaman itu setiap pagi dengan air hujan.",
        })
        self.assertEqual(out_of_scope.status_code, 200)
        self.assertEqual(out_of_scope.json()["status"], "ditolak")
        self.assertEqual(out_of_scope.json()["segments"], [])
        self.assertEqual(self.backend.received, [])

    def test_broken_span_cannot_appear_as_complete(self):
        with patch.object(detection_routes, "_analyze_document_blocks", return_value=[]):
            response = self.client.post(DOCUMENT_PATH, json={"text": POLITICAL_TEXT})
            self.assertEqual(response.status_code, 500)

        response = self.client.post(DOCUMENT_PATH, json={"text": POLITICAL_TEXT})
        self.assertEqual(response.json()["status"], "lengkap")

    def test_failed_model_has_no_label_and_busy_returns_503(self):
        with detection_routes._document_lock:
            busy = self.client.post(DOCUMENT_PATH, json={"text": POLITICAL_TEXT})
        self.assertEqual(busy.status_code, 503)

        with patch.object(self.backend, "seed_probs_each_untruncated", side_effect=RuntimeError):
            response = self.client.post(DOCUMENT_PATH, json={"text": POLITICAL_TEXT})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual((data["status"], data["analyzed_words"]), ("gagal", 0))
        self.assertTrue(all(s["label"] is None and s["votes_hoax"] is None for s in data["segments"]))
