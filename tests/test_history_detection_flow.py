from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from tests import test_auth_roles as auth_fixture
from src.api.routes import detection_routes
from src.database.models import PredictionLog, UserFeedback


def mock_classify_result(text):
    """Menirukan keluaran model inferensi yang valid dengan konsensus."""
    return {
        "success": True,
        "status": "dinilai",
        "label": "TIDAK BERPOLA HOAKS",
        "votes_hoax": "0/3",
        "agreement_ratio": 1.0,
        "decision_rule": "unanimous",
        "seed_decisions": {42: 0, 123: 0, 999: 0},
        "sub_topik": "Kebijakan & Bansos",
        "istilah": ["bansos", "pemerintah"],
        "teks_dinilai": text,
        "terpotong": False,
        "flags": [],
        "latency_seconds": 0.185,
        "narrative_text": "Pernyataan resmi pemerintah mengenai alokasi anggaran.",
    }


class TestHistoryDetectionFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        auth_fixture.TestLoginRoles.setUpClass()

    @classmethod
    def tearDownClass(cls):
        if hasattr(auth_fixture.TestLoginRoles, "tearDownClass"):
            auth_fixture.TestLoginRoles.tearDownClass()

    def setUp(self):
        self.memory = auth_fixture.TestLoginRoles(methodName="runTest")
        self.memory.setUp()
        self.client = self.memory.client

        # Pasang router deteksi ke aplikasi pengujian via self.client.app
        app = self.client.app
        if not any(getattr(r, "path", "").startswith("/api/v1/detect") for r in app.routes):
            app.include_router(detection_routes.router, prefix="/api/v1")

        self.user_id = self.memory.ids["USER"]
        self.admin_id = self.memory.ids["ADMIN"]

        self.user_headers = self.memory.login("USER")
        self.admin_headers = self.memory.login("ADMIN")

        # Naskah teks politik valid hasil suntingan OCR (lolos batas 30 karakter & guardrail)
        self.edited_ocr_text = (
            "Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial "
            "tahun anggaran baru harus tepat sasaran kepada masyarakat penerima manfaat."
        )

    def tearDown(self):
        if hasattr(self.memory, "tearDown"):
            self.memory.tearDown()

    def test_full_detection_to_history_lifecycle(self):

        # 1. Kirim Analisis Naskah Hasil Suntingan OCR (input_type: IMAGE)
        payload = {
            "text": self.edited_ocr_text,
            "input_type": "IMAGE",
            "image_url": "https://storage.example.com/ocr_samples/sample_panjang_sintetis.png"
        }

        with patch.object(detection_routes, "_classify_without_lime", side_effect=mock_classify_result) as classify_mock:
            res_detect = self.client.post("/api/v1/detect/text", json=payload, headers=self.user_headers)

        self.assertEqual(res_detect.status_code, 200)
        detect_body = res_detect.json()
        self.assertEqual(detect_body["status"], "success")

        detect_data = detect_body["data"]
        detection_id = UUID(detect_data["id"])

        # Verifikasi respons endpoint deteksi awal
        self.assertEqual(detect_data["input_text"], self.edited_ocr_text)
        self.assertEqual(detect_data["input_type"], "IMAGE")
        self.assertEqual(detect_data["image_url"], "https://storage.example.com/ocr_samples/sample_panjang_sintetis.png")
        self.assertEqual(detect_data["process_status"], "dinilai")
        self.assertEqual(detect_data["pattern_label"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(detect_data["agreement_ratio"], 1.0)
        self.assertEqual(detect_data["votes_hoax"], "0/3")
        classify_mock.assert_called_once_with(self.edited_ocr_text)

        # 2. Verifikasi Penyimpanan Data di Database
        with self.memory.session_factory() as db:
            log_db = db.query(PredictionLog).filter(PredictionLog.id == detection_id).first()
            self.assertIsNotNone(log_db)
            self.assertEqual(log_db.user_id, self.user_id)
            self.assertEqual(log_db.input_text, self.edited_ocr_text)
            self.assertEqual(log_db.input_type, "IMAGE")
            self.assertEqual(log_db.process_status, "dinilai")
            self.assertEqual(log_db.pattern_label, "TIDAK BERPOLA HOAKS")
            self.assertEqual(log_db.agreement_ratio, 1.0)

        # 3. Ambil Daftar Riwayat (GET /users/history)
        res_list = self.client.get("/api/v1/users/history", headers=self.user_headers)
        self.assertEqual(res_list.status_code, 200)
        list_data = res_list.json()["data"]

        # Pastikan ada tepat 1 entri riwayat dan nilainya cocok
        self.assertEqual(len(list_data), 1)
        item_list = list_data[0]
        self.assertEqual(item_list["id"], str(detection_id))
        self.assertEqual(item_list["input_text"], self.edited_ocr_text)
        self.assertEqual(item_list["input_type"], "IMAGE")
        self.assertEqual(item_list["process_status"], "dinilai")
        self.assertEqual(item_list["pattern_label"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(item_list["prediction"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(item_list["agreement_ratio"], 1.0)

        # 4. Ambil Detail Riwayat (GET /users/history/{id})
        res_detail = self.client.get(f"/api/v1/users/history/{detection_id}", headers=self.user_headers)
        self.assertEqual(res_detail.status_code, 200)
        item_detail = res_detail.json()["data"]

        self.assertEqual(item_detail["id"], str(detection_id))
        self.assertEqual(item_detail["input_text"], self.edited_ocr_text)
        self.assertEqual(item_detail["input_type"], "IMAGE")
        self.assertEqual(item_detail["process_status"], "dinilai")
        self.assertEqual(item_detail["pattern_label"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(item_detail["prediction"], "TIDAK BERPOLA HOAKS")
        self.assertEqual(item_detail["agreement_ratio"], 1.0)
        self.assertEqual(item_detail["narrative_text"], "Pernyataan resmi pemerintah mengenai alokasi anggaran.")
        self.assertEqual(item_detail["latency_seconds"], 0.185)

        # 5. Uji Idempotensi: Membaca Riwayat Tidak Menambah Entri Database
        with self.memory.session_factory() as db:
            total_logs = db.query(PredictionLog).count()
            self.assertEqual(total_logs, 1)

        # 6. Tambahkan Feedback Pengguna & Uji Penghapusan Atomik (DELETE)
        fb_id = uuid4()
        with self.memory.session_factory() as db:
            fb = UserFeedback(
                id=fb_id,
                detection_id=detection_id,
                user_id=self.user_id,
                is_agreed=True,
                claimed_label="TIDAK BERPOLA HOAKS",
                user_notes="Koreksi teks OCR akurat dan vonis sesuai",
                review_status="PENDING",
                created_at=datetime.now(timezone.utc),
            )
            db.add(fb)
            db.commit()

        # Verifikasi bahwa detail riwayat mengenali feedback tersebut
        res_detail_fb = self.client.get(f"/api/v1/users/history/{detection_id}", headers=self.user_headers)
        self.assertTrue(res_detail_fb.json()["data"]["has_feedback"])
        self.assertEqual(res_detail_fb.json()["data"]["feedback"]["id"], str(fb_id))

        # Eksekusi DELETE /api/v1/users/history/{id}
        res_del = self.client.delete(f"/api/v1/users/history/{detection_id}", headers=self.user_headers)
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["data"]["id"], str(detection_id))

        # Verifikasi riwayat dan feedback terhapus bersih dari database
        with self.memory.session_factory() as db:
            self.assertIsNone(db.query(PredictionLog).filter(PredictionLog.id == detection_id).first())
            self.assertIsNone(db.query(UserFeedback).filter(UserFeedback.id == fb_id).first())

        # Pastikan daftar riwayat sekarang kembali kosong
        res_list_after = self.client.get("/api/v1/users/history", headers=self.user_headers)
        self.assertEqual(res_list_after.json()["data"], [])

    def test_cross_user_isolation(self):
        """Memastikan data riwayat dan hak kelola terisolasi ketat antar-akun."""
        # 1. User A membuat analisis
        payload = {"text": self.edited_ocr_text, "input_type": "IMAGE"}
        with patch.object(detection_routes, "_classify_without_lime", side_effect=mock_classify_result):
            res_user = self.client.post("/api/v1/detect/text", json=payload, headers=self.user_headers)
        det_id = res_user.json()["data"]["id"]

        # 2. Akun User B (Admin) tidak boleh melihat riwayat User A di daftarnya
        res_admin_list = self.client.get("/api/v1/users/history", headers=self.admin_headers)
        self.assertEqual(res_admin_list.json()["data"], [])

        # 3. Akun User B tidak boleh membaca detail riwayat milik User A (wajib 404)
        res_admin_detail = self.client.get(f"/api/v1/users/history/{det_id}", headers=self.admin_headers)
        self.assertEqual(res_admin_detail.status_code, 404)

        # 4. Akun User B tidak boleh menghapus riwayat milik User A (wajib 404)
        res_admin_del = self.client.delete(f"/api/v1/users/history/{det_id}", headers=self.admin_headers)
        self.assertEqual(res_admin_del.status_code, 404)

        # 5. Data User A wajib tetap utuh di database
        with self.memory.session_factory() as db:
            self.assertIsNotNone(db.query(PredictionLog).filter(PredictionLog.id == UUID(det_id)).first())


if __name__ == "__main__":
    unittest.main()