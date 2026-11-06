import inspect
import logging
import math
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
from starlette.concurrency import run_in_threadpool

from src.utils.political_guardrail import check_political_domain
from src.utils.ocr_extractor import MAX_BYTES
from src.utils.ocr_pipeline import (
    proses_gambar,
    KATEGORI_OK,
    KATEGORI_INPUT,
    KATEGORI_KUALITAS,
    KATEGORI_MESIN,
)

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

        # LIME gagal (_lime menangkap galat sendiri): jangan simpan, jangan dibalas "success"
    if not (isinstance(explanation, dict) and explanation.get("explanation_available")):
        raise HTTPException(
            status_code=502,
            detail="Penjelasan gagal dibuat. Hasil klasifikasi tetap berlaku; coba lagi nanti."
        )

    log.lime_explanation = explanation
    db.commit()
    return ExplanationResponse(
        status="success", message="Penjelasan berhasil dibuat.", explanation=explanation
    )


# =====================================================================
# JALUR B: EKSTRAKSI GAMBAR MELALUI PIPELINE BERSAMA
# =====================================================================
@router.post("/image", response_model=OCRResponse)
async def extract_text_from_image_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # 1. Filter awal tipe konten (MIME)
    if file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/jpg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format file tidak didukung. Harap upload gambar PNG, JPEG, atau WebP."
        )

    # 2. Baca isi berkas dengan pembatasan ukuran ketat
    try:
        contents = await file.read(MAX_BYTES + 1)
    except Exception as exc:
        logger.error("Gagal membaca berkas unggahan (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gagal membaca data berkas unggahan."
        )
    
    if len(contents) > MAX_BYTES:
        mb = MAX_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ukuran berkas melebihi batas maksimal ({mb} MB)."
        )

    # 3. Jalankan OCR via threadpool agar tidak memblokir async event-loop
    try:
        h = await run_in_threadpool(proses_gambar, contents)
    except Exception as exc:
        logger.error("Pipeline OCR mengalami galat (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal pada pemrosesan gambar."
        )

    # Kontrak diperiksa sebelum membaca metadata atau membentuk respons.
    if not isinstance(h, dict):
        logger.error("Tipe keluaran pipeline OCR tidak valid: %s", type(h).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mesin OCR mengembalikan keluaran internal yang tidak valid."
        )

    kategori = h.get("kategori")
    kode = h.get("kode")
    pesan = h.get("pesan")
    if not isinstance(pesan, str) or not pesan.strip():
        pesan = (
            "Teks berhasil diekstrak. Silakan periksa atau sunting sebelum dianalisis."
            if kategori == KATEGORI_OK else "Gambar tidak dapat diproses."
        )

    # 4. Pemetaan kategori & kode pipeline ke status HTTP (satu log per penolakan)

    if kategori == KATEGORI_INPUT:
        logger.warning(
            "Pipeline OCR: kategori=%s kode=%s",
            kategori if isinstance(kategori, str) else type(kategori).__name__,
            kode if isinstance(kode, str) else "-",
        )
        status_code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if kode == "INPUT_UKURAN_BERKAS"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=pesan)

    if kategori == KATEGORI_KUALITAS:
        # Ekstraksi tipe aman: fitur harus dict, teks_bersih harus str, jika kosong tuliskan None
        raw_fitur = h.get("fitur")
        fitur = raw_fitur if isinstance(raw_fitur, dict) else {}

        raw_teks = h.get("teks_bersih")
        n_karakter = len(raw_teks) if isinstance(raw_teks, str) else None

        raw_kata = fitur.get("n_kata")
        n_kata = raw_kata if isinstance(raw_kata, int) and not isinstance(raw_kata, bool) else None

        raw_conf = fitur.get("conf_rata2")
        conf = raw_conf if isinstance(raw_conf, (int, float)) and not isinstance(raw_conf, bool) else None

        # Catat hanya metrik numerik; detail_teknis mentah DIHAPUS agar tidak bocor ke log
        logger.warning(
            "OCR Ditolak Mutu [%s]: karakter=%s, kata=%s, conf=%s",
            kode if isinstance(kode, str) else "-",
            n_karakter,
            n_kata,
            conf,
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=pesan
        )

    if kategori == KATEGORI_MESIN:
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if kode == "MESIN_GAGAL"
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=pesan)

    if kategori != KATEGORI_OK:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kategori keluaran OCR tidak dikenal."
        )

    # 5. OK harus konsisten; ambang kualitas tetap menjadi tanggung jawab pipeline.
    teks_bersih = h.get("teks_bersih")
    fitur = h.get("fitur")
    if (h.get("dapat_dinilai") is not True
            or not isinstance(teks_bersih, str) or not teks_bersih.strip()
            or not isinstance(fitur, dict)):
        logger.error("Kontrak hasil OCR kategori OK tidak konsisten")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mesin OCR mengembalikan keluaran internal yang tidak valid."
        )
    confidence = fitur.get("conf_rata2")
    if confidence is not None and not (
        not isinstance(confidence, bool) and isinstance(confidence, (int, float))
        and 0.0 <= confidence <= 1.0 and math.isfinite(confidence)
    ):
        logger.error("Confidence hasil OCR tidak valid")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mesin OCR mengembalikan keluaran internal yang tidak valid."
        )

    # Gunakan teks pipeline apa adanya, tanpa pembersihan/gerbang kedua.
    return OCRResponse(
        status="success",
        message=pesan,
        data=OCRResultData(
            extracted_text=teks_bersih,
            dapat_dinilai=True,
            confidence=confidence,
            character_count=len(teks_bersih),
            image_url=None,
            reason=None
        )
    )
