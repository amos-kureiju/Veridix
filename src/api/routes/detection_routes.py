from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from src.api.schemas import (
    TextDetectionRequest, 
    DetectionResponse, 
    DetectionResultData,
    OCRResponse,
    OCRResultData
)
from src.database.session import get_db
from src.database.models import PredictionLog, User
from src.core.auth_deps import get_current_user
from src.ml.inference import predictor
from src.utils.text_preprocessor import clean_ocr_artifacts
from src.utils.ocr_extractor import extract_text_from_image
from src.utils.political_guardrail import check_political_domain

router = APIRouter(prefix="/detect", tags=["Detection"])


# =====================================================================
# JALUR A: DETEKSI TEKS & ANALISIS AKHIR (TEXT / OCR EDITED)
# =====================================================================
@router.post("/text", response_model=DetectionResponse)
def detect_text(
    payload: TextDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    raw_text = payload.text.strip()
    
    # 1. Validasi Batas Minimal Karakter (Layer 1)
    if len(raw_text) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah berita terlalu pendek (minimal 30 karakter)."
        )

    # 2. Guardrail Politik (Layer 2: Menghindari pemborosan komputasi LIME)
    is_political, entities = check_political_domain(raw_text)
    if not is_political:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah di luar jangkauan. Sistem dikhususkan untuk verifikasi isu sosial-politik Indonesia."
        )

    # 3. Inferensi Model IndoBERT + Explainability LIME (Layer 3 & 4)
    try:
        result = predictor.predict_and_explain(raw_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan pada mesin AI: {str(e)}"
        )

    # Pemetaan atribut (kompatibilitas dictionary hasil inferensi)
    pattern_label = result.get("pattern_label") or result.get("prediction")
    agreement_ratio = result.get("agreement_ratio") or result.get("confidence_score")
    latency_seconds = result.get("latency_seconds") or result.get("inference_time_seconds", 0.0)
    process_status = result.get("process_status", "DINILAI")
    lime_explanation = result.get("lime_explanation") or result.get("explanation")
    narrative_text = result.get("narrative_text")
    political_topic = result.get("political_topic", "ALL")

    # 4. Simpan Log Prediksi ke Database (Layer 6)
    log_entry = PredictionLog(
        user_id=current_user.id,
        input_text=raw_text,
        input_type=payload.input_type,      # 'TEXT' atau 'IMAGE'
        image_url=payload.image_url,        # Tersimpan jika berasal dari hasil upload OCR
        is_political=True,
        political_topic=political_topic,
        detected_entities=entities if entities else result.get("detected_entities", []),
        process_status=process_status,
        pattern_label=pattern_label,
        agreement_ratio=agreement_ratio,
        latency_seconds=latency_seconds,
        lime_explanation=lime_explanation,
        narrative_text=narrative_text
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # 5. Kembalikan Response Sesuai Schema DetectionResponse (Layer 5)
    return DetectionResponse(
        status="success",
        message="Verifikasi berhasil diselesaikan.",
        data=DetectionResultData(
            id=log_entry.id,
            input_text=log_entry.input_text,
            input_type=log_entry.input_type,
            image_url=log_entry.image_url,
            process_status=log_entry.process_status,
            pattern_label=log_entry.pattern_label,
            agreement_ratio=log_entry.agreement_ratio,
            latency_seconds=log_entry.latency_seconds,
            is_political=log_entry.is_political,
            political_topic=log_entry.political_topic,
            detected_entities=log_entry.detected_entities or [],
            explanation=log_entry.lime_explanation,
            narrative_text=log_entry.narrative_text,
            created_at=log_entry.created_at
        )
    )


# =====================================================================
# JALUR B: EKSTRAKSI GAMBAR (PADDLEOCR DENGAN CEK 'dapat_dinilai')
# =====================================================================
@router.post("/image", response_model=OCRResponse)
async def extract_text_from_image_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Validasi tipe konten berkas
    if file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/jpg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format file tidak didukung. Harap upload gambar JPEG, PNG, atau WEBP."
        )

    contents = await file.read()
    
    # 1. Ekstraksi Menggunakan PaddleOCR
    ocr_raw = extract_text_from_image(contents)
    if not ocr_raw.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ocr_raw.get("message", "Gagal mengekstrak teks dari gambar.")
        )

    # 2. Pemeriksaan 'dapat_dinilai' (Kualitas Teks & Keterbacaan)
    dapat_dinilai = ocr_raw.get("dapat_dinilai", True)
    if not dapat_dinilai:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ocr_raw.get("reason", "Kualitas teks gambar tidak layak untuk dianalisis (buram, terpotong, atau tidak terbaca).")
        )

    # 3. Validasi Panjang Teks Hasil OCR (Minimal 50 Karakter)
    extracted_text = ocr_raw.get("text", "").strip()
    if len(extracted_text) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teks yang terdeteksi pada gambar kurang dari 50 karakter."
        )

    # 4. Normalisasi dan Pembersihan Noise Artefak OCR
    cleaned_ocr_text = clean_ocr_artifacts(extracted_text)

    # Kembalikan teks ke frontend agar user bisa mengedit sebelum submit deteksi
    return OCRResponse(
        status="success",
        message="Teks berhasil diekstrak. Silakan periksa atau sunting sebelum dianalisis.",
        data=OCRResultData(
            extracted_text=cleaned_ocr_text,
            dapat_dinilai=dapat_dinilai,
            confidence=ocr_raw.get("confidence"),
            character_count=len(cleaned_ocr_text),
            image_url=ocr_raw.get("image_url"),
            reason=None
        )
    )