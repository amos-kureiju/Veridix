from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from src.api.schemas import TextDetectionRequest, DetectionResponse
from src.database.session import get_db
from src.database.models import PredictionLog
from src.ml.inference import predictor
from src.utils.text_preprocessor import clean_standard_text, clean_ocr_artifacts
from src.utils.ocr_extractor import extract_text_from_image

router = APIRouter(prefix="/detect", tags=["Detection"])

# --- JALUR A: DETEKSI TEKS LANGSUNG ---
@router.post("/text", response_model=DetectionResponse)
def detect_direct_text(payload: TextDetectionRequest, db: Session = Depends(get_db)):
    # 1. Validasi minimal 30 karakter untuk teks langsung
    if len(payload.text.strip()) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah berita terlalu pendek (minimal 30 karakter)."
        )

    # 2. Pembersihan standar
    cleaned_text = clean_standard_text(payload.text)

    # 3. Masuk ke IndoBERT + LIME
    result = predictor.predict_and_explain(cleaned_text)

    if not result["is_political"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah di luar jangkauan. Sistem dikhususkan untuk verifikasi isu sosial-politik Indonesia."
        )

    # 4. Simpan ke database
    log_entry = PredictionLog(
        input_text=payload.text,
        prediction=result["prediction"],
        confidence_score=result["confidence_score"],
        is_political=result["is_political"],
        inference_time=result["inference_time_seconds"]
    )
    db.add(log_entry)
    db.commit()

    return {"status": "success", "data": result}


# --- JALUR B: EKSTRAKSI GAMBAR (OCR) ---
@router.post("/image")
async def detect_image_upload(file: UploadFile = File(...)):
    contents = await file.read()
    
    # 1. Ekstraksi OCR
    ocr_raw = extract_text_from_image(contents)
    if not ocr_raw["success"]:
        raise HTTPException(status_code=400, detail=ocr_raw["message"])

    # 2. Validasi minimal 50 karakter KHUSUS hasil OCR
    if len(ocr_raw["text"].strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teks pada gambar kurang dari 50 karakter atau gambar terlalu buram."
        )

    # 3. Pembersihan ekstra artefak OCR
    cleaned_ocr_text = clean_ocr_artifacts(ocr_raw["text"])

    # Kembalikan teks bersih ke frontend agar user bisa melihat & mengedit (Human-in-the-Loop)
    return {
        "status": "success",
        "extracted_text": cleaned_ocr_text,
        "message": "Teks berhasil diekstrak dan dibersihkan dari artefak gambar."
    }