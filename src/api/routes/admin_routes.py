from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from src.database.session import get_db
from src.database.models import PredictionLog, UserFeedback, User
from src.core.auth_deps import require_admin
from src.api.schemas import ThresholdUpdateRequest

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

# Ambang keputusan per seed pada model beku (lihat src/ml/inference.py: probs >= 0.5)
FROZEN_THRESHOLD = 0.5


@router.get("/stats")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    total_detections = db.query(PredictionLog).count()

    total_hoaxes = db.query(PredictionLog).filter(
        PredictionLog.pattern_label.in_(["BERPOLA HOAKS", "HOAKS", "HOAX"])
    ).count()

    total_facts = db.query(PredictionLog).filter(
        PredictionLog.pattern_label.in_(["TIDAK BERPOLA HOAKS", "FACT", "FAKTA"])
    ).count()

    # Status baru disimpan huruf kecil ("ambigu"); data lama mungkin "AMBIGU"
    total_ambiguous = db.query(PredictionLog).filter(
        func.lower(PredictionLog.process_status) == "ambigu"
    ).count()

    total_text_inputs = db.query(PredictionLog).filter(PredictionLog.input_type == "TEXT").count()
    total_image_inputs = db.query(PredictionLog).filter(PredictionLog.input_type == "IMAGE").count()

    total_feedbacks = db.query(UserFeedback).count()
    pending_feedbacks = db.query(UserFeedback).filter(UserFeedback.review_status == "PENDING").count()

    avg_latency = db.query(func.avg(PredictionLog.latency_seconds)).scalar() or 0.0

    return {
        "status": "success",
        "data": {
            "total_detections": total_detections,
            "total_hoaxes": total_hoaxes,
            "total_facts": total_facts,
            "total_ambiguous": total_ambiguous,
            "active_threshold": FROZEN_THRESHOLD,
            "threshold_editable": False,
            "hoax_percentage": round((total_hoaxes / total_detections * 100), 1) if total_detections > 0 else 0.0,
            "input_distribution": {
                "text": total_text_inputs,
                "image": total_image_inputs
            },
            "feedbacks": {
                "total": total_feedbacks,
                "pending_review": pending_feedbacks
            },
            "average_latency_seconds": round(float(avg_latency), 3)
        }
    }


@router.get("/threshold")
def get_current_threshold(
    admin_user: User = Depends(require_admin)
):
    # Ambang tetap pada model beku; tidak membaca nilai database yang tidak dipakai inferensi
    return {
        "status": "success",
        "data": {
            "key": "classification_threshold",
            "threshold": FROZEN_THRESHOLD,
            "editable": False,
            "note": "Ambang tetap pada model beku (per seed).",
            "updated_at": None
        }
    }


@router.put("/threshold")
def update_threshold(
    payload: ThresholdUpdateRequest,
    admin_user: User = Depends(require_admin)
):
    # Tidak menyimpan apa pun dan tidak mengklaim sukses: mengubah ambang berarti mengubah model beku
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Perubahan threshold dinonaktifkan: model beku memakai ambang tetap 0,5 "
            "per seed. Pengaturan ini tidak memengaruhi inferensi."
        ),
    )


@router.get("/feedbacks")
def list_feedbacks(
    status_filter: Optional[str] = Query(None, pattern="^(PENDING|REVIEWED|DISMISSED|RETRAINED)$"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    query = db.query(UserFeedback)
    if status_filter:
        query = query.filter(UserFeedback.review_status == status_filter)

    feedbacks = query.order_by(UserFeedback.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "status": "success",
        "count": len(feedbacks),
        "data": [
            {
                "id": f.id,
                "detection_id": f.detection_id,
                "user_id": f.user_id,
                "is_agreed": f.is_agreed,
                "claimed_label": f.claimed_label,
                "user_notes": f.user_notes,
                "clarification_url": f.clarification_url,
                "review_status": f.review_status,
                "admin_notes": getattr(f, "admin_notes", None),
                "created_at": f.created_at
            } for f in feedbacks
        ]
    }
