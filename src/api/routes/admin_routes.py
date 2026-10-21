from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from src.database.session import get_db
from src.database.models import PredictionLog, UserFeedback, AdminSetting, ThresholdHistory, User
from src.core.auth_deps import require_admin
from src.api.schemas import ThresholdUpdateRequest

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.get("/stats")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    total_detections = db.query(PredictionLog).count()
    
    total_hoaxes = db.query(PredictionLog).filter(
        PredictionLog.pattern_label.in_(["BERPOLA HOAKS", "HOAX"])
    ).count()

    total_facts = db.query(PredictionLog).filter(
        PredictionLog.pattern_label.in_(["TIDAK BERPOLA HOAKS", "FACT", "FAKTA"])
    ).count()

    total_ambiguous = db.query(PredictionLog).filter(
        PredictionLog.pattern_label == "PERLU KONFIRMASI"
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
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    setting = db.query(AdminSetting).filter(AdminSetting.key == "classification_threshold").first()
    threshold_val = float(setting.value) if setting else 0.5
    return {
        "status": "success",
        "data": {
            "key": "classification_threshold",
            "threshold": threshold_val,
            "updated_at": setting.updated_at if setting else None
        }
    }

@router.put("/threshold")
def update_threshold(
    payload: ThresholdUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    setting = db.query(AdminSetting).filter(AdminSetting.key == "classification_threshold").first()
    old_value = float(setting.value) if setting else 0.5

    if not setting:
        setting = AdminSetting(
            key="classification_threshold",
            value=str(payload.new_threshold),
            description="Confidence threshold for classifying news as hoaks",
            updated_by=admin_user.id
        )
        db.add(setting)
    else:
        setting.value = str(payload.new_threshold)
        setting.updated_by = admin_user.id

    history_entry = ThresholdHistory(
        setting_key="classification_threshold",
        old_value=old_value,
        new_value=payload.new_threshold,
        reason=payload.reason,
        changed_by=admin_user.id
    )
    db.add(history_entry)
    db.commit()

    return {
        "status": "success",
        "message": f"Threshold berhasil diperbarui dari {old_value} menjadi {payload.new_threshold}.",
        "data": {
            "new_threshold": payload.new_threshold,
            "changed_by": admin_user.full_name
        }
    }

@router.get("/feedbacks")
def list_feedbacks(
    status_filter: Optional[str] = Query(None, regex="^(PENDING|REVIEWED|DISMISSED|RETRAINED)$"),
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
                "created_at": f.created_at
            } for f in feedbacks
        ]
    }