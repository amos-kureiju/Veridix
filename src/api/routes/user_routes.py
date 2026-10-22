from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from src.database.session import get_db
from src.database.models import User, PredictionLog, UserFeedback
from src.core.auth_deps import get_current_user
from src.core.security import verify_password, hash_password

router = APIRouter(prefix="/users", tags=["Users"])


# SKEMA REQUEST
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, description="Kata sandi lama wajib diisi")
    new_password: str = Field(..., min_length=8, description="Kata sandi baru minimal 8 karakter")


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
    if not payload.old_password or not payload.old_password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama wajib diisi."
        )

    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama yang Anda masukkan salah."
        )

    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru tidak boleh sama dengan kata sandi lama."
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {
        "status": "success",
        "message": "Kata sandi berhasil diperbarui. Silakan gunakan kata sandi baru untuk login."
    }


# 2. RIWAYAT DETEKSI PENGGUNA (GET /api/v1/users/history)
@router.get("/history")
def get_user_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengambil daftar riwayat deteksi pengguna dari yang terbaru.
    Menggunakan proyeksi kolom spesifik untuk menghindari error kolom 'is_political'.
    """
    try:
        # 1. Pilih hanya kolom yang pasti ada (hindari memuat is_political)
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
            .order_by(PredictionLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # 2. Kumpulkan feedback milik user untuk detection_id terkait secara efisien
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

        # 3. Susun data respons
        results = []
        for row in logs:
            fb_info = feedbacks_map.get(row.id)
            results.append({
                "id": str(row.id),
                "input_text": row.input_text,
                "input_type": row.input_type,
                "image_url": row.image_url,
                "political_topic": row.political_topic or "Sosial Politik",
                "process_status": row.process_status or "DINILAI",
                "pattern_label": row.pattern_label,
                # Kompatibilitas untuk frontend lama yang masih membaca .prediction / .confidence_score
                "prediction": row.pattern_label or "PERLU KONFIRMASI",
                "agreement_ratio": row.agreement_ratio,
                "confidence_score": row.agreement_ratio or 0.0,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "has_feedback": fb_info is not None,
                "feedback": fb_info
            })

        return {
            "status": "success",
            "data": results
        }
    except Exception:
        db.rollback()
        # Fallback aman jika tabel kosong atau ada perbedaan skema
        return {
            "status": "success",
            "data": []
        }