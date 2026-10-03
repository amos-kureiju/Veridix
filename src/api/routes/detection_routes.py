from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from src.api.schemas import TextDetectionRequest, DetectionResponse
from src.database.session import get_db
from src.database.models import PredictionLog
from src.ml.inference import predictor
from src.utils.text_preprocessor import clean_ocr_artifacts
from src.utils.ocr_extractor import extract_text_from_image
from src.utils.political_guardrail import check_political_domain

router = APIRouter(prefix="/detect", tags=["Detection"])

# =====================================================================
# JALUR A: DETEKSI TEKS LANGSUNG (Sinkron dengan Layer 1 & 2 Diagram)
# =====================================================================
@router.post("/text", response_model=DetectionResponse)
def detect_direct_text(payload: TextDetectionRequest, db: Session = Depends(get_db)):
    raw_text = payload.text.strip()
    
    # 1. Validasi batas minimal 30 karakter (Sesuai Diagram Layer 1 Jalur A)
    if len(raw_text) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah berita terlalu pendek (minimal 30 karakter)."
        )

    # 2. GUARDRAIL POLITIK DI AWAL (Sesuai Diagram Layer 2: Cegah pemborosan LIME)
    is_political, entities = check_political_domain(raw_text)
    if not is_political:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah di luar jangkauan. Sistem dikhususkan untuk verifikasi isu sosial-politik Indonesia."
        )

    # 3. MASUK KE INDOBERT + LIME (Satu pintu: kirim raw_text murni tanpa double-cleaning)
    try:
        result = predictor.predict_and_explain(raw_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan pada mesin AI: {str(e)}"
        )

    # 4. SIMPAN KE DATABASE (Sesuai Diagram Layer 6)
    log_entry = PredictionLog(
        input_text=payload.text,
        prediction=result["prediction"],
        confidence_score=result["confidence_score"],
        is_political=result["is_political"],
        inference_time=result["inference_time_seconds"]
    )
    db.add(log_entry)
    db.commit()

    # 5. KEMBALIKAN OUTPUT 4 LAPIS (Sesuai Diagram Layer 5)
    return {"status": "success", "data": result}


# =====================================================================
# JALUR B: EKSTRAKSI GAMBAR / OCR (TETAP AMAN & TIDAK BERUBAH)
# =====================================================================
@router.post("/image")
async def detect_image_upload(file: UploadFile = File(...)):
    contents = await file.read()
    
    # 1. Ekstraksi PaddleOCR (Sesuai Diagram Layer 1 Jalur B)
    ocr_raw = extract_text_from_image(contents)
    if not ocr_raw.get("success", False):
        raise HTTPException(status_code=400, detail=ocr_raw.get("message", "Gagal membaca teks gambar."))

    # 2. Validasi minimal 50 karakter KHUSUS hasil OCR
    extracted_text = ocr_raw.get("text", "").strip()
    if len(extracted_text) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teks pada gambar kurang dari 50 karakter atau gambar terlalu buram."
        )

    # 3. Pembersihan ekstra artefak noise OCR
    cleaned_ocr_text = clean_ocr_artifacts(extracted_text)

    # Kembalikan ke frontend agar user bisa review/edit (Human-in-the-Loop)
    return {
        "status": "success",
        "extracted_text": cleaned_ocr_text,
        "message": "Teks berhasil diekstrak dan dibersihkan dari artefak gambar."
    }