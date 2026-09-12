from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.schemas import TextDetectionRequest, DetectionResponse
from src.database.session import get_db
from src.database.models import PredictionLog
from src.ml.inference import predictor

router = APIRouter(prefix="/detect", tags=["Detection"])

@router.post("/text", response_model=DetectionResponse)
def detect_hoax_text(payload: TextDetectionRequest, db: Session = Depends(get_db)):
    result = predictor.predict_and_explain(payload.text)

    # Tolak jika bukan domain politik (Guardrail aktif)
    if not result["is_political"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah berita di luar jangkauan sistem. Sistem ini dikhususkan untuk verifikasi isu sosial-politik Indonesia."
        )

    # Simpan log ke database (SQLite / Supabase)
    log_entry = PredictionLog(
        input_text=payload.text,
        prediction=result["prediction"],
        confidence_score=result["confidence_score"],
        is_political=result["is_political"],
        inference_time=result["inference_time_seconds"]
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "success",
        "data": result
    }
