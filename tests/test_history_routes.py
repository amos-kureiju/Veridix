"""tests/test_history_routes.py — Pengujian endpoint detail riwayat GET /api/v1/users/history/{history_id}."""

from datetime import datetime, timezone
import unittest
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

from tests import test_auth_roles as auth_fixture
from src.database.models import PredictionLog, UserFeedback


class TestHistoryDetailRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        auth_fixture.TestLoginRoles.setUpClass()

    @classmethod
    def tearDownClass(cls):
        if hasattr(auth_fixture.TestLoginRoles, "tearDownClass"):
            auth_fixture.TestLoginRoles.tearDownClass()

    def setUp(self):
        # Gunakan komposisi fixture otentikasi resmi yang sama dengan test_reporting_integrity
        self.memory = auth_fixture.TestLoginRoles(methodName="runTest")
        self.memory.setUp()
        self.client = TestClient(self.memory.app, raise_server_exceptions=False)

        self.user_id = self.memory.ids["USER"]
        self.admin_id = self.memory.ids["ADMIN"]

        self.user_headers = self.memory.login("USER")
        self.admin_headers = self.memory.login("ADMIN")

    def tearDown(self):
        if hasattr(self.memory, "tearDown"):
            self.memory.tearDown()

    def _create_prediction(self, user_id, **kwargs):
        log_id = kwargs.pop("id", uuid4())
        defaults = {
            "id": log_id,
            "user_id": user_id,
            "input_text": "Pemerintah memastikan penyaluran bantuan sosial 2026 transparan.",
            "input_type": "IMAGE",
            "image_url": "https://example.com/sample.png",
            "political_topic": "Kebijakan & Bansos",
            "process_status": "dinilai",
            "pattern_label": "TIDAK BERPOLA HOAKS",
            "agreement_ratio": 1.0,
            "latency_seconds": 1.84,
            "narrative_text": "Naskah merupakan pernyataan resmi kementerian.",
            "lime_explanation": {"explanation_available": True, "tokens": [{"word": "bansos", "weight": -0.4}]},
            "detected_entities": ["Pemerintah", "Bansos 2026"],
            "created_at": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        with self.memory.session_factory() as db:
            row = PredictionLog(**defaults)
            db.add(row)
            db.commit()
        return log_id

    # 1. Pemilik sah dapat membaca detail riwayat lengkap beserta LIME dan feedback
    def test_owner_can_get_history_detail_with_explanation_and_feedback(self):
        log_id = self._create_prediction(self.user_id)
        fb_id = uuid4()

        with self.memory.session_factory() as db:
            fb = UserFeedback(
                id=fb_id,
                detection_id=log_id,
                user_id=self.user_id,
                is_agreed=True,
                claimed_label="TIDAK BERPOLA HOAKS",
                user_notes="Hasil analisis akurat",
                clarification_url="https://kemenkeu.go.id/rilis",
                review_status="PENDING",
                admin_notes=None,
                reviewed_at=None,
                created_at=datetime.now(timezone.utc),
            )
            db.add(fb)
            db.commit()

        res = self.client.get(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
        self.assertEqual(res.status_code, 200)

        body = res.json()
        self.assertEqual(body["status"], "success")
        data = body["data"]

        # Kolom umum
        self.assertEqual(data["id"], str(log_id))
        self.assertEqual(data["input_text"], "Pemerintah memastikan penyaluran bantuan sosial 2026 transparan.")
        self.assertEqual(data["input_type"], "IMAGE")
        self.assertEqual(data["process_status"], "dinilai")
        self.assertEqual(data["pattern_label"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(data["prediction"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(data["agreement_ratio"], 1.0)

        # Field khusus detail
        self.assertEqual(data["latency_seconds"], 1.84)
        self.assertEqual(data["narrative_text"], "Naskah merupakan pernyataan resmi kementerian.")
        self.assertTrue(data["explanation"]["explanation_available"])
        self.assertEqual(data["detected_entities"], ["Pemerintah", "Bansos 2026"])

        # Field feedback lengkap
        self.assertTrue(data["has_feedback"])
        self.assertIsNotNone(data["feedback"])
        self.assertEqual(data["feedback"]["id"], str(fb_id))
        self.assertTrue(data["feedback"]["is_agreed"])
        self.assertEqual(data["feedback"]["user_notes"], "Hasil analisis akurat")
        self.assertEqual(data["feedback"]["clarification_url"], "https://kemenkeu.go.id/rilis")

    # 2. Akun lain mendapatkan 404 (isolasi data antar-pengguna)
    def test_other_user_gets_404_for_existing_history(self):
        log_id = self._create_prediction(self.user_id)

        # Akses menggunakan header ADMIN (akun berbeda)
        res = self.client.get(f"/api/v1/users/history/{log_id}", headers=self.admin_headers)
        self.assertEqual(res.status_code, 404)
        self.assertIn("tidak ditemukan", res.json()["detail"].lower())

    # 3. ID yang tidak ada di database mendapatkan 404
    def test_non_existent_history_id_gets_404(self):
        random_id = uuid4()
        res = self.client.get(f"/api/v1/users/history/{random_id}", headers=self.user_headers)
        self.assertEqual(res.status_code, 404)

    # 4. Akses tanpa login mendapatkan 401
    def test_unauthenticated_request_gets_401(self):
        log_id = self._create_prediction(self.user_id)
        res = self.client.get(f"/api/v1/users/history/{log_id}")
        self.assertEqual(res.status_code, 401)

    # 5. Metadata kosong tetap None dan aman dari galat
    def test_history_detail_preserves_null_metadata(self):
        log_id = self._create_prediction(
            self.user_id,
            process_status="ditolak",
            pattern_label=None,
            agreement_ratio=None,
            latency_seconds=0.0,  # <-- 1. Gunakan 0.0 yang sah untuk nullable=False
            narrative_text=None,
            lime_explanation=None,
            detected_entities=None,
        )

        res = self.client.get(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
        self.assertEqual(res.status_code, 200)

        data = res.json()["data"]
        self.assertEqual(data["process_status"], "ditolak")
        self.assertIsNone(data["pattern_label"])
        self.assertIsNone(data["prediction"])
        self.assertIsNone(data["agreement_ratio"])
        self.assertEqual(data["latency_seconds"], 0.0)  # <-- 2. Pastikan nilai nol tetap dipertahankan
        self.assertIsNone(data["narrative_text"])
        self.assertIsNone(data["explanation"])
        self.assertEqual(data["detected_entities"], [])
        self.assertFalse(data["has_feedback"])
        self.assertIsNone(data["feedback"])

    # 6. Feedback akun lain pada detection_id ini tidak ikut terbaca
    def test_other_user_feedback_is_not_read_in_detail(self):
        log_id = self._create_prediction(self.user_id)

        # Buat feedback milik admin (bukan pemilik log deteksi)
        with self.memory.session_factory() as db:
            fb_admin = UserFeedback(
                id=uuid4(),
                detection_id=log_id,
                user_id=self.admin_id,
                is_agreed=False,
                claimed_label="BERPOLA HOAKS",
                review_status="PENDING",
            )
            db.add(fb_admin)
            db.commit()

        res = self.client.get(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]

        # Feedback admin tidak boleh bocor ke respons pemilik log
        self.assertFalse(data["has_feedback"])
        self.assertIsNone(data["feedback"])

    # 7. Status dinilai dengan agreement_ratio kosong tetap menghasilkan None pada respons
    def test_history_detail_evaluated_with_null_agreement_ratio(self):
        log_id = self._create_prediction(
            self.user_id,
            process_status="dinilai",
            pattern_label="BERPOLA HOAKS",
            agreement_ratio=None,
            latency_seconds=0.5,
        )

        res = self.client.get(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
        self.assertEqual(res.status_code, 200)

        data = res.json()["data"]
        self.assertEqual(data["process_status"], "dinilai")
        self.assertEqual(data["pattern_label"], "BERPOLA HOAKS")
        self.assertEqual(data["prediction"], "BERPOLA HOAKS")
        self.assertIsNone(data["agreement_ratio"])
        self.assertIsNone(data["confidence_score"])


# 8. Pemilik sah berhasil menghapus riwayat dan feedback terkait ikut terhapus
    def test_owner_can_delete_history_and_cascade_feedback(self):
        log_id = self._create_prediction(self.user_id)
        fb_id = uuid4()

        with self.memory.session_factory() as db:
            fb = UserFeedback(
                id=fb_id,
                detection_id=log_id,
                user_id=self.user_id,
                is_agreed=True,
                claimed_label="TIDAK BERPOLA HOAKS",
                review_status="PENDING",
            )
            db.add(fb)
            db.commit()

        # Eksekusi DELETE
        res = self.client.delete(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
        self.assertEqual(res.status_code, 200)

        body = res.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["data"]["id"], str(log_id))
        self.assertIn("berhasil dihapus", body["message"])

        # Verifikasi data benar-benar hilang dari database
        with self.memory.session_factory() as db:
            self.assertIsNone(db.query(PredictionLog).filter(PredictionLog.id == log_id).first())
            self.assertIsNone(db.query(UserFeedback).filter(UserFeedback.id == fb_id).first())

    # 9. Akun lain tidak dapat menghapus riwayat pengguna lain (404)
    def test_other_user_cannot_delete_history_gets_404(self):
        log_id = self._create_prediction(self.user_id)

        # Coba hapus memakai akun ADMIN (bukan pemilik)
        res = self.client.delete(f"/api/v1/users/history/{log_id}", headers=self.admin_headers)
        self.assertEqual(res.status_code, 404)

        # Verifikasi riwayat milik user tetap utuh
        with self.memory.session_factory() as db:
            self.assertIsNotNone(db.query(PredictionLog).filter(PredictionLog.id == log_id).first())

    # 10. Hapus ID acak yang tidak ada menghasilkan 404
    def test_delete_non_existent_history_gets_404(self):
        random_id = uuid4()
        res = self.client.delete(f"/api/v1/users/history/{random_id}", headers=self.user_headers)
        self.assertEqual(res.status_code, 404)

    # 11. Hapus tanpa login menghasilkan 401
    def test_delete_unauthenticated_gets_401(self):
        log_id = self._create_prediction(self.user_id)
        res = self.client.delete(f"/api/v1/users/history/{log_id}")
        self.assertEqual(res.status_code, 401)

    # 12. Menghapus kembali ID yang sudah terhapus menghasilkan 404
    def test_delete_repeated_same_id_returns_404(self):
        log_id = self._create_prediction(self.user_id)

        # Hapus pertama: 200 OK
        res1 = self.client.delete(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
        self.assertEqual(res1.status_code, 200)

        # Hapus kedua kali pada ID yang sama: wajib 404
        res2 = self.client.delete(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
        self.assertEqual(res2.status_code, 404)

    # 13. Menghapus satu riwayat mempertahankan riwayat dan feedback pengguna lainnya
    def test_delete_one_history_retains_other_histories_and_feedbacks(self):
        log_a = self._create_prediction(self.user_id, input_text="Naskah A")
        log_b = self._create_prediction(self.user_id, input_text="Naskah B")
        fb_b_id = uuid4()

        with self.memory.session_factory() as db:
            fb_b = UserFeedback(
                id=fb_b_id,
                detection_id=log_b,
                user_id=self.user_id,
                is_agreed=True,
                claimed_label="TIDAK BERPOLA HOAKS",
                review_status="PENDING",
            )
            db.add(fb_b)
            db.commit()

        # Hapus log A
        res = self.client.delete(f"/api/v1/users/history/{log_a}", headers=self.user_headers)
        self.assertEqual(res.status_code, 200)

        # Verifikasi log B dan feedback B tetap utuh
        with self.memory.session_factory() as db:
            self.assertIsNone(db.query(PredictionLog.id).filter(PredictionLog.id == log_a).first())
            self.assertIsNotNone(db.query(PredictionLog.id).filter(PredictionLog.id == log_b).first())
            self.assertIsNotNone(db.query(UserFeedback.id).filter(UserFeedback.id == fb_b_id).first())

    # 14. Kegagalan commit() memicu rollback penuh (riwayat & feedback tidak terhapus sebagian)
    def test_delete_rollback_on_commit_failure_preserves_both_log_and_feedback(self):
        log_id = self._create_prediction(self.user_id)
        fb_id = uuid4()

        with self.memory.session_factory() as db:
            fb = UserFeedback(
                id=fb_id,
                detection_id=log_id,
                user_id=self.user_id,
                is_agreed=True,
                claimed_label="TIDAK BERPOLA HOAKS",
                review_status="PENDING",
            )
            db.add(fb)
            db.commit()

        # Simulasikan kegagalan database saat commit dijalankan
        with patch("sqlalchemy.orm.Session.commit", side_effect=SQLAlchemyError("Simulasi galat transaksi commit")):
            res = self.client.delete(f"/api/v1/users/history/{log_id}", headers=self.user_headers)
            # Re-raise SQLAlchemyError ditangkap sebagai HTTP 500 oleh handler aplikasi
            self.assertEqual(res.status_code, 500)

        # Verifikasi integritas: kedua data wajib tetap ada di database karena rollback
        with self.memory.session_factory() as db:
            self.assertIsNotNone(db.query(PredictionLog.id).filter(PredictionLog.id == log_id).first())
            self.assertIsNotNone(db.query(UserFeedback.id).filter(UserFeedback.id == fb_id).first())




if __name__ == "__main__":
    unittest.main()