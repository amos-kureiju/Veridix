import unittest
import uuid
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.database.session import SessionLocal
from src.database.models import PredictionLog
import src.api.routes.detection_routes as dr

class TestDetectionAndAuthAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Setup mock predictor agar tes stabil tanpa GPU/torch
        self.orig_predictor = dr.predictor.predict_and_explain
        dr.predictor.predict_and_explain = MagicMock(return_value={
            "success": True,
            "status": "dinilai",
            "label": "BERPOLA HOAKS",
            "votes_hoax": "3/3",
            "decision_rule": "unanimous",
            "sub_topik": "Politik & Pemilu",
            "istilah": ["kpu", "pemilu"],
            "teks_dinilai": "kpu ri mengumumkan jadwal pemilu serentak",
            "terpotong": False,
            "input_flags": {},
            "disclaimer": "Sistem mendeteksi...",
            "explanation": {
                "tokens": [
                    {"word": "kpu", "weight": 0.42, "influence": "KE_HOAKS"},
                    {"word": "resmi", "weight": -0.15, "influence": "KE_TIDAK_HOAKS"}
                ]
            },
            "debug": {"prob_hoax_per_seed": [0.94, 0.91, 0.95]},
            "latency_seconds": 0.32
        })

    def tearDown(self):
        dr.predictor.predict_and_explain = self.orig_predictor

    # 1. Tes Validasi Input Terlalu Pendek (< 30 Karakter)
    def test_detection_short_text_rejected(self):
        res = self.client.post("/api/v1/detect/text", json={"text": "Pendek sekali"})
        self.assertIn(res.status_code, [400, 422])

    # 2. Tes Guardrail Domain Politik (Teks non-politik ditolak)
    def test_detection_out_of_domain_rejected(self):
        non_political_text = "Resep membuat bolu kukus pandan manis dan lembut untuk cemilan keluarga di rumah sore hari."
        res = self.client.post("/api/v1/detect/text", json={"text": non_political_text})
        self.assertEqual(res.status_code, 400)
        self.assertIn("di luar jangkauan", res.json().get("detail", "").lower())

    # 3. Tes Deteksi Valid & Keselarasan Skema Response
    def test_detection_valid_text_success(self):
        political_text = "KPU RI secara resmi mengumumkan jadwal pelaksanaan tahapan pemilu serentak dan pilpres tahun depan."
        res = self.client.post("/api/v1/detect/text", json={"text": political_text})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        
        payload = data["data"]
        self.assertIn(payload["prediction"], ["HOAKS", "FAKTA", "PERLU KONFIRMASI"])
        self.assertGreater(payload["confidence_score"], 0)
        self.assertGreater(payload["inference_time_seconds"], 0)
        self.assertIn("explanation", payload)
        self.assertGreater(len(payload["explanation"]["tokens"]), 0)

        # Verifikasi data tersimpan di database
        db = SessionLocal()
        saved = db.query(PredictionLog).filter(PredictionLog.id == uuid.UUID(payload["id"])).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.verdict, payload["prediction"])
        self.assertEqual(saved.input_text, political_text)
        db.close()

    # 4. Tes Backend Gagal dengan Jelas jika Mesin AI Mengalami Kesalahan
    def test_detection_ai_engine_failure_handled(self):
        dr.predictor.predict_and_explain = MagicMock(side_effect=RuntimeError("Model checkpoint korup atau tidak dapat dimuat"))
        political_text = "DPR RI menggelar rapat koordinasi bersama menteri membahas RUU pemilu dan anggaran negara."
        res = self.client.post("/api/v1/detect/text", json={"text": political_text})
        self.assertEqual(res.status_code, 500)
        self.assertIn("kesalahan pada mesin ai", res.json().get("detail", "").lower())

    # 5. Tes Alur Autentikasi & Akun Demo
    def test_auth_login_demo_admin(self):
        res = self.client.post("/api/v1/auth/login", json={
            "email": "admin@veridix.id",
            "password": "admin123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "ADMIN")

        # Akses /me dengan token
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_res = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["email"], "admin@veridix.id")

    # 6. Tes Admin Dashboard Stats & Logs
    def test_admin_stats_and_logs(self):
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": "admin@veridix.id",
            "password": "admin123"
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ambil stats
        stats_res = self.client.get("/api/v1/admin/stats", headers=headers)
        self.assertEqual(stats_res.status_code, 200)
        self.assertIn("total_detections_today", stats_res.json())

        # Ambil logs
        logs_res = self.client.get("/api/v1/admin/logs/recent", headers=headers)
        self.assertEqual(logs_res.status_code, 200)
        self.assertIsInstance(logs_res.json(), list)

if __name__ == "__main__":
    unittest.main()
