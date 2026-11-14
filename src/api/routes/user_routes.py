import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from src.database.session import get_db
from src.database.models import User, PredictionLog, UserFeedback
from src.core.auth_deps import get_current_user
from src.core.security import verify_password, hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


# SKEMA REQUEST
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, description="Kata sandi lama wajib diisi")
    new_password: str = Field(..., min_length=8, description="Kata sandi baru minimal 8 karakter")
    confirm_password: Optional[str] = Field(None, description="Konfirmasi kata sandi baru")


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    avatar_url: Optional[str] = None


# 1. PROFIL PENGGUNA
@router.get("/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "avatar_url": current_user.avatar_url
        }
    }


@router.put("/profile")
def update_user_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.full_name = payload.full_name.strip()
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip()

    db.commit()
    db.refresh(current_user)
    return {
        "status": "success",
        "message": "Profil berhasil diperbarui."
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validasi 1: Konfirmasi kecocokan password baru
    if payload.confirm_password and payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfirmasi kata sandi baru tidak cocok."
        )

    # Validasi 2: Password lama wajib benar
    if not payload.old_password or not payload.old_password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi saat ini wajib diisi."
        )

    # Validasi 2: Password lama wajib benar
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi saat ini yang Anda masukkan salah."
        )

    # Simpan password baru & NAIKKAN token_version
    current_user.password_hash = hash_password(payload.new_password)
    current_user.token_version = (getattr(current_user, "token_version", 0) or 0) + 1
    db.commit()

    # Validasi 3: Cegah password sama
    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru tidak boleh sama dengan kata sandi lama."
        )

    # Simpan password baru & NAIKKAN token_version (otomatis batalkan JWT sesi lama)
    current_user.password_hash = hash_password(payload.new_password)
    current_user.token_version = (getattr(current_user, "token_version", 0) or 0) + 1
    db.commit()

    return {
        "status": "success",
        "message": "Kata sandi berhasil diperbarui. Demi keamanan, silakan masuk kembali."
    }


# 2. RIWAYAT DETEKSI PENGGUNA (GET /api/v1/users/history)
def _format_datetime_utc(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.astimezone(timezone.utc).isoformat()


def _build_history_response_item(row, fb_info: Optional[dict] = None, detail: bool = False) -> dict:
    # 1. Normalisasi status: kosong/None menjadi 'tidak_diketahui'
    raw_status = getattr(row, "process_status", None)
    if raw_status is None or not str(raw_status).strip():
        status_norm = "tidak_diketahui"
    else:
        status_norm = str(raw_status).strip().lower()

    # 2. Hanya status 'dinilai' dan 'ambigu' yang diizinkan memiliki label & konsensus
    if status_norm in ("dinilai", "ambigu"):
        label_pola = getattr(row, "pattern_label", None)
        prediction_display = label_pola or "PERLU KONFIRMASI"
        raw_agreement = getattr(row, "agreement_ratio", None)
        agreement = raw_agreement if isinstance(raw_agreement, (int, float)) and not isinstance(raw_agreement, bool) else None
    else:
        label_pola = None
        prediction_display = None
        agreement = None

    item = {
        "id": str(row.id),
        "input_text": row.input_text,
        "input_type": getattr(row, "input_type", None) or "TEXT",
        "image_url": getattr(row, "image_url", None),
        "political_topic": getattr(row, "political_topic", None) or "Sosial Politik",
        "process_status": status_norm,
        "pattern_label": label_pola,
        "prediction": prediction_display,
        "agreement_ratio": agreement,
        "confidence_score": agreement,
        "created_at": _format_datetime_utc(getattr(row, "created_at", None)),
        "has_feedback": fb_info is not None,
        "feedback": fb_info,
    }

    if detail:
        item.update({
            "latency_seconds": getattr(row, "latency_seconds", None),
            "narrative_text": getattr(row, "narrative_text", None),
            "explanation": getattr(row, "lime_explanation", None),
            "detected_entities": getattr(row, "detected_entities", None) or [],
        })

    return item

# 2. DAFTAR RIWAYAT DETEKSI (GET /api/v1/users/history)
@router.get("/history")
def get_user_history(
    limit: int = Query(50, ge=1, le=100, description="Jumlah data yang diambil (1-100)"),
    offset: int = Query(0, ge=0, description="Offset data untuk pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengambil daftar riwayat deteksi pengguna secara stabil dan konsisten.
    Menggunakan proyeksi kolom spesifik untuk efisiensi dan keamanan skema.
    """
    try:
        # 1. Ambil baris dengan proyeksi kolom eksplisit & urutan deterministik
        logs = (
            db.query(
                PredictionLog.id,
                PredictionLog.input_text,
                PredictionLog.input_type,
                PredictionLog.image_url,
                PredictionLog.political_topic,
                PredictionLog.process_status,
                PredictionLog.pattern_label,
                PredictionLog.agreement_ratio,
                PredictionLog.created_at
            )
            .filter(PredictionLog.user_id == current_user.id)
            .order_by(PredictionLog.created_at.desc(), PredictionLog.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # 2. Kumpulkan feedback milik pengguna untuk detection_id terkait secara efisien
        log_ids = [row.id for row in logs]
        feedbacks_map = {}
        if log_ids:
            fb_records = (
                db.query(
                    UserFeedback.detection_id,
                    UserFeedback.id,
                    UserFeedback.is_agreed,
                    UserFeedback.claimed_label,
                    UserFeedback.review_status,
                    UserFeedback.admin_notes
                )
                .filter(
                    UserFeedback.user_id == current_user.id,
                    UserFeedback.detection_id.in_(log_ids)
                )
                .all()
            )
            for fb in fb_records:
                feedbacks_map[fb.detection_id] = {
                    "id": str(fb.id),
                    "is_agreed": fb.is_agreed,
                    "claimed_label": fb.claimed_label,
                    "review_status": fb.review_status,
                    "admin_notes": fb.admin_notes
                }

        # 3. Format hasil secara konsisten tanpa duplikasi
        results = [
            _build_history_response_item(row, fb_info=feedbacks_map.get(row.id), detail=False)
            for row in logs
        ]

        return {
            "status": "success",
            "data": results
        }
    except SQLAlchemyError:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Gagal membaca riwayat deteksi: error=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Riwayat tidak dapat dimuat saat ini. Silakan coba lagi."
        )

# 3. DETAIL SATU RIWAYAT DETEKSI (GET /api/v1/users/history/{history_id})
@router.get("/history/{history_id}")
def get_user_history_detail(
    history_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengambil rincian lengkap satu riwayat deteksi beserta penjelasan LIME dan feedback.
    Membatasi akses hanya pada riwayat milik pengguna yang sedang terautentikasi (404 jika bukan pemilik).
    """
    try:
        # 1. Ambil satu entri dengan validasi kepemilikan ganda
        log = (
            db.query(
                PredictionLog.id,
                PredictionLog.input_text,
                PredictionLog.input_type,
                PredictionLog.image_url,
                PredictionLog.political_topic,
                PredictionLog.process_status,
                PredictionLog.pattern_label,
                PredictionLog.agreement_ratio,
                PredictionLog.created_at,
                PredictionLog.latency_seconds,
                PredictionLog.narrative_text,
                PredictionLog.lime_explanation,
                PredictionLog.detected_entities
            )
            .filter(
                PredictionLog.id == history_id,
                PredictionLog.user_id == current_user.id
            )
            .first()
        )

        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Riwayat deteksi tidak ditemukan."
            )

        # 2. Ambil rincian feedback lengkap milik pengguna untuk deteksi ini
        fb = (
            db.query(
                UserFeedback.id,
                UserFeedback.is_agreed,
                UserFeedback.claimed_label,
                UserFeedback.user_notes,
                UserFeedback.clarification_url,
                UserFeedback.review_status,
                UserFeedback.admin_notes,
                UserFeedback.reviewed_at,
                UserFeedback.created_at
            )
            .filter(
                UserFeedback.detection_id == history_id,
                UserFeedback.user_id == current_user.id
            )
            .first()
        )

        fb_info = None
        if fb:
            fb_info = {
                "id": str(fb.id),
                "is_agreed": fb.is_agreed,
                "claimed_label": fb.claimed_label,
                "user_notes": fb.user_notes,
                "clarification_url": fb.clarification_url,
                "review_status": fb.review_status,
                "admin_notes": fb.admin_notes,
                "reviewed_at": _format_datetime_utc(fb.reviewed_at),
                "created_at": _format_datetime_utc(fb.created_at),
            }

        # 3. Bentuk respons detail lengkap
        detail_data = _build_history_response_item(log, fb_info=fb_info, detail=True)

        return {
            "status": "success",
            "data": detail_data
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Gagal membaca detail riwayat: error=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detail riwayat tidak dapat dimuat saat ini. Silakan coba lagi."
        )


@router.delete("/history/{history_id}")
def delete_user_history(
    history_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menghapus satu riwayat deteksi beserta feedback terkait secara transaksional (atomik).
    Hanya mengambil ID (proyeksi kolom) untuk menghindari kegagalan skema kolom lama.
    Menggunakan delete() kueri langsung dan meneruskan SQLAlchemyError ke handler global.
    """
    try:
        # 1. Cari riwayat berdasarkan ID dan kepemilikan (hanya ambil kolom ID dengan kunci baris)
        log_id_row = (
            db.query(PredictionLog.id)
            .filter(
                PredictionLog.id == history_id,
                PredictionLog.user_id == current_user.id
            )
            .with_for_update()
            .first()
        )
        if not log_id_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Riwayat deteksi tidak ditemukan."
            )

        # 2. Hapus feedback terkait pengguna dalam transaksi yang sama
        db.query(UserFeedback).filter(
            UserFeedback.detection_id == history_id,
            UserFeedback.user_id == current_user.id
        ).delete(synchronize_session=False)

        # 3. Hapus entri riwayat deteksi secara langsung tanpa memuat seluruh kolom objek
        deleted_count = (
            db.query(PredictionLog)
            .filter(
                PredictionLog.id == history_id,
                PredictionLog.user_id == current_user.id
            )
            .delete(synchronize_session=False)
        )

        if deleted_count != 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Riwayat deteksi tidak ditemukan."
            )

        deleted_id_str = str(history_id)
        db.commit()

        return {
            "status": "success",
            "message": "Riwayat berhasil dihapus.",
            "data": {
                "id": deleted_id_str
            }
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        # Rollback transaksi dan teruskan galat ke handler database global di main.py
        db.rollback()
        raise