from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from src.api.schemas import TextDetectionRequest, DetectionResponse
from src.database.session import get_db
from src.database.models import PredictionLog
from src.ml.inference import predictor
from src.utils.ocr_extractor import extract_text_from_image

router = APIRouter(prefix="/detect", tags=["Detection"])

# 1. Endpoint Deteksi Teks Utama
@router.post("/text", response_model=DetectionResponse)
def detect_hoax_text(payload: TextDetectionRequest, db: Session = Depends(get_db)):
    result = predictor.predict_and_explain(payload.text)

    # Guardrail: Tolak jika bukan isu politik
    if not result["is_political"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah di luar jangkauan sistem. Sistem ini dikhususkan untuk verifikasi isu sosial-politik Indonesia."
        )

    # Simpan riwayat ke database
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

# 2. Endpoint Khusus Ekstraksi Gambar OCR (Human-in-the-Loop)
@router.post("/ocr")
async def extract_text_from_upload(file: UploadFile = File(...)):
    """
    Menerima file gambar (PNG/JPG), mengembalikan teks hasil baca EasyOCR
    agar pengguna bisa memeriksa & mengedit teksnya sebelum dianalisis IndoBERT.
    """
    contents = await file.read()
    ocr_result = extract_text_from_image(contents)

    if not ocr_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ocr_result["message"]
        )

    return {
        "status": "success",
        "extracted_text": ocr_result["text"]
    }