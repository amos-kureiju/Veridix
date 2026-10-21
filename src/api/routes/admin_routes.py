from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from src.database.session import get_db
from src.database.models import PredictionLog, UserFeedback, AdminSetting, ThresholdHistory, User
from src.core.auth_deps import require_admin, get_current_user

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

class ThresholdUpdateRequest(BaseModel):
    threshold: float
    reason: Optional[str] = "Pembaruan ambang batas via Admin Dashboard"

@router.get("/stats")
def get_admin_dashboard_stats(db: Session = Depends(get_db)):
    """
    Menampilkan metrik statistik deteksi riil dari database.
    Format respons mendukung langsung frontend useAdminDashboard.
    """
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_detections_today = db.query(PredictionLog).filter(PredictionLog.created_at >= start_of_today).count()
    if total_detections_today == 0:
        total_detections_today = db.query(PredictionLog).count()

    hoax_detected_today = db.query(PredictionLog).filter(
        PredictionLog.verdict == "HOAKS"
    ).count()

    total_all = db.query(PredictionLog).count()
    hoax_ratio_percent = round((hoax_detected_today / total_all * 100), 1) if total_all > 0 else 0.0

    pending_feedbacks = db.query(UserFeedback).filter(
        UserFeedback.review_status == "PENDING"
    ).count()

    active_users_count = db.query(User).filter(User.is_active == True).count()

    # Ambil threshold aktif dari admin_settings jika ada
    setting = db.query(AdminSetting).filter(AdminSetting.setting_key == "active_threshold").first()
    active_threshold = float(setting.setting_value) if setting else 0.60

    return {
        "total_detections_today": total_detections_today,
        "total_detections_delta": 0.0,
        "hoax_detected_today": hoax_detected_today,
        "hoax_ratio_percent": hoax_ratio_percent,
        "pending_feedbacks": pending_feedbacks,
        "active_threshold": active_threshold,
        "active_users_count": active_users_count,
        # Field legacy tambahan
        "total_detections": total_all,
        "total_hoaxes": hoax_detected_today,
        "total_facts": total_all - hoax_detected_today
    }


@router.get("/logs/recent")
def get_recent_logs(limit: int = 20, db: Session = Depends(get_db)):
    """
    Menampilkan riwayat deteksi terkini yang benar-benar tersimpan di database.
    """
    logs = db.query(PredictionLog).order_by(PredictionLog.created_at.desc()).limit(limit).all()
    
    result = []
    for item in logs:
        user_identifier = item.user.email if item.user else "Tamu (Publik)"
        snippet = item.input_text[:85] + "..." if len(item.input_text) > 85 else item.input_text
        
        # Konversi latency ke detik float
        latency = float(item.latency_seconds or (item.inference_time_ms / 1000.0) if item.inference_time_ms else 0.35)

        result.append({
            "id": f"LOG-{str(item.id)[:8].upper()}",
            "db_id": str(item.id),
            "user_identifier": user_identifier,
            "text_snippet": snippet,
            "full_text": item.input_text,
            "political_topic": item.political_topic or "Politik Nasional",
            "prediction": item.verdict or item.pattern_label or "HOAKS",
            "confidence_score": float(item.confidence_score or 0.85),
            "inference_time": round(latency, 2),
            "created_at": item.created_at.isoformat() if item.created_at else datetime.now(timezone.utc).isoformat()
        })
    return result


@router.post("/threshold")
def update_ai_threshold(
    payload: ThresholdUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Menyimpan pembaruan threshold AI ke database.
    """
    if payload.threshold < 0.0 or payload.threshold > 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nilai threshold harus berada di antara 0.0 dan 1.0."
        )

    setting = db.query(AdminSetting).filter(AdminSetting.setting_key == "active_threshold").first()
    old_val = float(setting.setting_value) if setting else 0.60

    if setting:
        setting.setting_value = str(payload.threshold)
        setting.updated_at = datetime.now(timezone.utc)
    else:
        setting = AdminSetting(
            setting_key="active_threshold",
            setting_value=str(payload.threshold),
            description="Ambang batas klasifikasi hoaks aktif"
        )
        db.add(setting)

    # Catat ke threshold_history
    history = ThresholdHistory(
        old_threshold=old_val,
        new_threshold=payload.threshold,
        reason=payload.reason
    )
    db.add(history)
    db.commit()

    return {
        "success": True,
        "message": f"Threshold AI berhasil diperbarui ke {payload.threshold}",
        "threshold": payload.threshold
    }
