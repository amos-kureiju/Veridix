import inspect
import logging
import threading
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from src.api.schemas import (
    TextDetectionRequest,
    DetectionResponse,
    DetectionResultData,
    ExplanationResponse,
    OCRResponse,
    OCRResultData,
)
from src.database.session import get_db
from src.database.models import PredictionLog, User
from src.core.auth_deps import get_current_user
from src.ml.inference import predictor
from src.utils.text_preprocessor import clean_ocr_artifacts
from src.utils.ocr_extractor import extract_text_from_image
from src.utils.political_guardrail import check_political_domain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detect", tags=["Detection"])

# Satu komputasi LIME pada satu waktu (per proses) agar CPU dan kunci inferensi tidak berebut
_lime_lock = threading.Lock()

# Kirim explain=False hanya jika predict_and_explain memang menerimanya
try:
    _SUPPORTS_EXPLAIN_FLAG = "explain" in inspect.signature(predictor.predict_and_explain).parameters
except (TypeError, ValueError):
    _SUPPORTS_EXPLAIN_FLAG = False


def _classify_without_lime(text: str) -> dict:
    if _SUPPORTS_EXPLAIN_FLAG:
        return predictor.predict_and_explain(text, explain=False)
    return predictor.predict_and_explain(text)


# =====================================================================
# JALUR A: DETEKSI TEKS (KLASIFIKASI CEPAT, TANPA LIME)
# =====================================================================
@router.post("/text", response_model=DetectionResponse)
def detect_text(
    payload: TextDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    raw_text = payload.text.strip()

    # 1. Validasi Batas Minimal Karakter
    if len(raw_text) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah berita terlalu pendek (minimal 30 karakter)."
        )

    # 2. Guardrail Politik
    is_political, guardrail_topic, entities = check_political_domain(raw_text)
    if not is_political:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah di luar jangkauan. Sistem dikhususkan untuk verifikasi isu sosial-politik Indonesia."
        )

    # 3. Inferensi AI (tanpa LIME; penjelasan diminta lewat endpoint /explain)
    try:
        result = _classify_without_lime(raw_text)
    except Exception:
        logger.exception("Inferensi gagal")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan pada mesin AI. Silakan coba lagi."
        )

    # 4. Pemetaan Output Inferensi (status diseragamkan huruf kecil)
    process_status = str(
        result.get("status") or result.get("process_status") or "dinilai"
    ).lower()
    model_ran = process_status in ("dinilai", "ambigu")

    if process_status in ("ditolak", "di_luar_domain"):
        pattern_label = None
        agreement_ratio = None
    else:
        pattern_label = result.get("label") or result.get("pattern_label")
        agreement_ratio = result.get("agreement_ratio")

    political_topic = result.get("sub_topik") or guardrail_topic or "ALL"
    latency_seconds = result.get("latency_seconds") or result.get("inference_time_seconds", 0.0)
    lime_explanation = result.get("lime_explanation") or result.get("explanation")
    narrative_text = result.get("narrative_text")

    # Metadata konsensus: None bila model tidak dijalankan (jangan diisi "0/3")
    votes_hoax = result.get("votes_hoax") if model_ran else None
    seed_decisions = result.get("seed_decisions") if model_ran else None
    sub_topik = result.get("sub_topik")
    reason = result.get("reason")
    terpotong = bool(result.get("terpotong", False))

    # 5. Simpan ke Database
    log_entry = PredictionLog(
        user_id=current_user.id,
        input_text=raw_text,
        input_type=payload.input_type,
        image_url=payload.image_url,
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

    # 6. Response
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
            votes_hoax=votes_hoax,
            seed_decisions=seed_decisions,
            sub_topik=sub_topik,
            reason=reason,
            terpotong=terpotong,
            explanation=log_entry.lime_explanation,
            narrative_text=log_entry.narrative_text,
            created_at=log_entry.created_at
        )
    )


# =====================================================================
# JALUR A2: PENJELASAN LIME SESUAI PERMINTAAN
# =====================================================================
@router.post("/{detection_id}/explain", response_model=ExplanationResponse)
def explain_detection(
    detection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Hanya pemilik; 404 agar keberadaan data pengguna lain tidak terungkap
    log = db.query(PredictionLog).filter(
        PredictionLog.id == detection_id,
        PredictionLog.user_id == current_user.id,
    ).first()
    if log is None:
        raise HTTPException(status_code=404, detail="Hasil deteksi tidak ditemukan.")

    if str(log.process_status).lower() not in ("dinilai", "ambigu"):
        raise HTTPException(
            status_code=409,
            detail="Penjelasan hanya tersedia untuk hasil yang dinilai."
        )

    # Sudah pernah dihitung: kembalikan tanpa komputasi ulang
    existing = log.lime_explanation
    if isinstance(existing, dict) and existing.get("explanation_available"):
        return ExplanationResponse(
            status="success", message="Penjelasan tersedia.", explanation=existing
        )

    explain_fn = getattr(predictor, "explain", None)
    if explain_fn is None:
        raise HTTPException(
            status_code=501,
            detail="Penjelasan LIME belum tersedia pada mesin AI."
        )

    if not _lime_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="Penjelasan lain sedang diproses. Coba lagi sebentar."
        )
    try:
        explanation = explain_fn(log.input_text)
    except Exception:
        logger.exception("LIME gagal")
        raise HTTPException(status_code=500, detail="Penjelasan gagal dibuat.")
    finally:
        _lime_lock.release()

    log.lime_explanation = explanation
    db.commit()
    return ExplanationResponse(
        status="success", message="Penjelasan berhasil dibuat.", explanation=explanation
    )


# =====================================================================
# JALUR B: EKSTRAKSI GAMBAR (PADDLEOCR)  -- tidak diubah
# =====================================================================
@router.post("/image", response_model=OCRResponse)
async def extract_text_from_image_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/jpg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format file tidak didukung. Harap upload gambar JPEG, PNG, atau WEBP."
        )

    contents = await file.read()
    ocr_raw = extract_text_from_image(contents)
    if not ocr_raw.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ocr_raw.get("message", "Gagal mengekstrak teks dari gambar.")
        )

    dapat_dinilai = ocr_raw.get("dapat_dinilai", True)
    alasan_penolakan = ocr_raw.get("alasan") or ocr_raw.get("reason")

    if not dapat_dinilai:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=alasan_penolakan or "Kualitas teks gambar tidak layak untuk dianalisis (buram atau teks tidak koheren)."
        )

    extracted_text = ocr_raw.get("text", "").strip()
    if len(extracted_text) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teks yang terdeteksi pada gambar kurang dari 50 karakter."
        )

    fitur_dict = ocr_raw.get("fitur", {})
    confidence_score = (
        fitur_dict.get("conf_rata2")
        if isinstance(fitur_dict, dict)
        else ocr_raw.get("confidence")
    )

    cleaned_ocr_text = clean_ocr_artifacts(extracted_text)

    return OCRResponse(
        status="success",
        message="Teks berhasil diekstrak. Silakan periksa atau sunting sebelum dianalisis.",
        data=OCRResultData(
            extracted_text=cleaned_ocr_text,
            dapat_dinilai=dapat_dinilai,
            confidence=confidence_score,
            character_count=len(cleaned_ocr_text),
            image_url=ocr_raw.get("image_url"),
            reason=alasan_penolakan
        )
    )