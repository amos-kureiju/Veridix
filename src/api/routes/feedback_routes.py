from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.schemas import FeedbackCreateRequest
from src.database.session import get_db
from src.database.models import UserFeedback, PredictionLog

router = APIRouter(prefix="/feedback", tags=["User Feedback"])

@router.post("/submit")
def submit_feedback(payload: FeedbackCreateRequest, db: Session = Depends(get_db)):
    # Pastikan log_id valid
    log = db.query(PredictionLog).filter(PredictionLog.id == payload.log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Riwayat deteksi tidak ditemukan.")

    feedback_entry = UserFeedback(
        log_id=payload.log_id,
        user_claimed_label=payload.user_claimed_label,
        clarification_url=payload.clarification_url,
        notes=payload.notes
    )
    db.add(feedback_entry)
    db.commit()

    return {
        "status": "success",
        "message": "Umpan balik berhasil dikirim untuk ditinjau oleh verifikator."
    }