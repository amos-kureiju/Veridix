import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.schemas import FeedbackCreateRequest
from src.database.session import get_db
from src.database.models import UserFeedback, PredictionLog

router = APIRouter(prefix="/feedback", tags=["User Feedback"])

@router.post("/submit")
def submit_feedback(payload: FeedbackCreateRequest, db: Session = Depends(get_db)):
    raw_id = payload.detection_id or payload.log_id
    if not raw_id:
        raise HTTPException(status_code=400, detail="ID deteksi wajib diisi.")

    try:
        det_id = uuid.UUID(str(raw_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Format ID deteksi tidak valid.")

    log = db.query(PredictionLog).filter(PredictionLog.id == det_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Riwayat deteksi tidak ditemukan.")

    feedback_entry = UserFeedback(
        detection_id=det_id,
        is_agreed=payload.is_agreed if payload.is_agreed is not None else False,
        claimed_label=payload.claimed_label or payload.user_claimed_label,
        clarification_url=payload.clarification_url,
        user_notes=payload.user_notes or payload.notes
    )
    db.add(feedback_entry)
    db.commit()

    return {
        "status": "success",
        "message": "Umpan balik berhasil dikirim untuk ditinjau oleh verifikator."
    }
