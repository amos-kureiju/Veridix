from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from src.database.session import get_db
from src.database.models import UserFeedback, PredictionLog, User
from src.core.auth_deps import get_current_user, require_admin
from src.api.schemas import (
    FeedbackCreateRequest, 
    FeedbackReviewRequest, 
    FeedbackResponse, 
    FeedbackResponseData
)

router = APIRouter(prefix="/feedback", tags=["Feedback"])

# 1. USER: KIRIM / PERBARUI FEEDBACK (UPSERT)
@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validasi keberadaan log deteksi
    detection = db.query(PredictionLog).filter(PredictionLog.id == payload.detection_id).first()
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data deteksi tidak ditemukan."
        )

    # 2. Cek apakah feedback sudah ada (Mencegah pelanggaran uq_feedback_per_user_detection)
    existing_feedback = db.query(UserFeedback).filter(
        UserFeedback.detection_id == payload.detection_id,
        UserFeedback.user_id == current_user.id
    ).first()

    if existing_feedback:
        # Perbarui feedback yang sudah ada
        existing_feedback.is_agreed = payload.is_agreed
        existing_feedback.claimed_label = payload.claimed_label
        existing_feedback.user_notes = payload.user_notes
        existing_feedback.clarification_url = str(payload.clarification_url) if payload.clarification_url else None
        existing_feedback.review_status = "PENDING"  # Reset status review jika user memperbarui klaim
        feedback_obj = existing_feedback
    else:
        # Buat feedback baru
        feedback_obj = UserFeedback(
            detection_id=payload.detection_id,
            user_id=current_user.id,
            is_agreed=payload.is_agreed,
            claimed_label=payload.claimed_label,
            user_notes=payload.user_notes,
            clarification_url=str(payload.clarification_url) if payload.clarification_url else None,
            review_status="PENDING"
        )
        db.add(feedback_obj)

    db.commit()
    db.refresh(feedback_obj)

    return FeedbackResponse(
        status="success",
        message="Feedback Anda berhasil disimpan.",
        data=FeedbackResponseData(
            id=feedback_obj.id,
            detection_id=feedback_obj.detection_id,
            user_id=feedback_obj.user_id,
            is_agreed=feedback_obj.is_agreed,
            claimed_label=feedback_obj.claimed_label,
            user_notes=feedback_obj.user_notes,
            clarification_url=feedback_obj.clarification_url,
            review_status=feedback_obj.review_status,
            admin_notes=feedback_obj.admin_notes,
            reviewed_at=feedback_obj.reviewed_at,
            created_at=feedback_obj.created_at
        )
    )


# 2. ADMIN: TINJAU FEEDBACK (REVIEW / DISMISS / RETRAINED)
@router.put("/{feedback_id}/review", response_model=FeedbackResponse)
def review_user_feedback(
    feedback_id: UUID,
    payload: FeedbackReviewRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    feedback = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data feedback tidak ditemukan."
        )

    # Update status verifikasi admin
    feedback.review_status = payload.review_status  # REVIEWED, DISMISSED, atau RETRAINED
    feedback.admin_notes = payload.admin_notes
    feedback.reviewed_by = admin_user.id
    feedback.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        status="success",
        message=f"Feedback berhasil ditandai sebagai {feedback.review_status}.",
        data=FeedbackResponseData(
            id=feedback.id,
            detection_id=feedback.detection_id,
            user_id=feedback.user_id,
            is_agreed=feedback.is_agreed,
            claimed_label=feedback.claimed_label,
            user_notes=feedback.user_notes,
            clarification_url=feedback.clarification_url,
            review_status=feedback.review_status,
            admin_notes=feedback.admin_notes,
            reviewed_at=feedback.reviewed_at,
            created_at=feedback.created_at
        )
    )