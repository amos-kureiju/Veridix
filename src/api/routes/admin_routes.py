from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.session import get_db
from src.database.models import PredictionLog, UserFeedback, AdminSetting

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.get("/stats")
def get_admin_dashboard_stats(db: Session = Depends(get_db)):
    """
    Menampilkan metrik statistik deteksi riil dari database lokal.
    """
    total_detections = db.query(PredictionLog).count()
    total_hoaxes = db.query(PredictionLog).filter(PredictionLog.verdict == "HOAKS").count()
    total_facts = db.query(PredictionLog).filter(PredictionLog.verdict == "FAKTA").count()
    total_feedbacks = db.query(UserFeedback).count()
    
    avg_latency = db.query(func.avg(PredictionLog.inference_time_ms)).scalar() or 0.0

    return {
        "status": "success",
        "data": {
            "total_detections": total_detections,
            "total_hoaxes": total_hoaxes,
            "total_facts": total_facts,
            "hoax_percentage": round((total_hoaxes / total_detections * 100), 1) if total_detections > 0 else 0,
            "total_feedbacks": total_feedbacks,
            "average_latency_seconds": round(float(avg_latency), 2)
        }
    }