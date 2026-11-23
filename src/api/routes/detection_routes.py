import hashlib
import hmac
import inspect
import logging
import math
import threading
from time import perf_counter
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.schemas import (
    TextDetectionRequest,
    DetectionResponse,
    DetectionResultData,
    DocumentAnalysisRequest,
    DocumentAnalysisResponse,
    DocumentExplanationRequest,
    DocumentSegmentResult,
    ExplanationResponse,
    OCRResponse,
    OCRResultData,
)
from src.database.session import get_db
from src.database.models import PredictionLog, User
from src.core.auth_deps import get_current_user
from src.core.security import SECRET_KEY
from src.ml.inference import predictor, validate_claim_result
from starlette.concurrency import run_in_threadpool

from src.utils.political_guardrail import check_political_domain
from src.utils.input_validation import MAX_CHARS, validate_input_text
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
_document_lock = threading.Lock()
_DOCUMENT_EXPLANATION_AUDIENCE = "veridix:document-explanation:v1"
_DOCUMENT_EXPLANATION_TTL = timedelta(hours=1)
_DOCUMENT_EXPLANATION_KEY = hmac.digest(
    SECRET_KEY.encode("utf-8"), _DOCUMENT_EXPLANATION_AUDIENCE.encode("ascii"), "sha256",
)

# Kirim explain=False hanya jika predict_and_explain memang menerimanya
try:
    _SUPPORTS_EXPLAIN_FLAG = "explain" in inspect.signature(predictor.predict_and_explain).parameters
except (TypeError, ValueError):
    _SUPPORTS_EXPLAIN_FLAG = False


def _classify_without_lime(text: str) -> dict:
    if _SUPPORTS_EXPLAIN_FLAG:
        return predictor.predict_and_explain(text, explain=False)
    return predictor.predict_and_explain(text)


def _document_blocks(payload: DocumentAnalysisRequest):
    if payload.text is not None:
        return [{"text": payload.text, "start_char": 0, "pages": []}], []

    groups = [[]]
    missing_pages = []
    for page in payload.pages or []:
        if page.text is None:
            missing_pages.append(page.page_number)
            if groups[-1]:
                groups.append([])
        else:
            groups[-1].append((page.page_number, page.text))

    blocks = []
    cursor = 0
    for group in groups:
        if not group:
            continue
        if blocks:
            cursor += 2  # Separator dalam teks sumber gabungan, tanpa jendela yang melintasi celah.
        block_start = cursor
        texts = []
        pages = []
        for page_number, page_text in group:
            if texts:
                cursor += 2
            start = cursor
            cursor += len(page_text)
            texts.append(page_text)
            pages.append((page_number, start, cursor))
        blocks.append({"text": "\n\n".join(texts), "start_char": block_start, "pages": pages})
    return blocks, missing_pages


def _analyze_document_blocks(blocks):
    from src.ml.document_analysis import analyze_document
    from src.ml.inference import get_predictor

    penilai = get_predictor()
    return analyze_document(blocks, penilai), penilai.document_model_identity()


def _document_words_analyzed(text, blocks, segments):
    cursor = 0
    next_word = 1
    analyzed_words = 0
    for segment in segments:
        start, end = segment.start_char, segment.end_char
        expected = text[start:end]
        if (
            not cursor <= start < end <= len(text)
            or text[cursor:start].strip()
            or (start and not text[start - 1].isspace())
            or (end < len(text) and not text[end].isspace())
            or expected != segment.text
            or expected != expected.strip()
        ):
            raise ValueError("Rentang segmen tidak cocok dengan sumber.")
        count = len(expected.split())
        if segment.start_word != next_word or segment.end_word != next_word + count - 1:
            raise ValueError("Nomor kata segmen tidak cocok dengan sumber.")

        block = next((
            block for block in blocks
            if block["start_char"] <= start and end <= block["start_char"] + len(block["text"])
        ), None)
        if block is None:
            raise ValueError("Segmen melintasi bagian sumber yang hilang.")
        pages = [page for page, first, last in block["pages"] if start < last and first < end]
        if segment.page_numbers != pages:
            raise ValueError("Halaman segmen tidak cocok dengan sumber.")

        if segment.status in ("dinilai", "ambigu"):
            if not segment.label or not segment.votes_hoax or not segment.token_count:
                raise ValueError("Keluaran penilaian segmen tidak lengkap.")
            analyzed_words += count
        elif segment.label is not None or segment.votes_hoax is not None or not segment.reason:
            raise ValueError("Status segmen yang belum dinilai tidak sesuai.")
        cursor = end
        next_word += count
    if text[cursor:].strip():
        raise ValueError("Bagian akhir sumber tidak tercatat.")
    return analyzed_words


def _document_explanation_token(user: User, segment: DocumentSegmentResult, model_identity: str) -> str:
    claims = {
        "aud": _DOCUMENT_EXPLANATION_AUDIENCE,
        "exp": datetime.now(timezone.utc) + _DOCUMENT_EXPLANATION_TTL,
        "sub": str(user.id),
        "jti": uuid4().hex,
        "token_version": user.token_version,
        "model": model_identity,
        "text_sha256": hashlib.sha256(segment.text.encode("utf-8")).hexdigest(),
        "token_count": segment.token_count,
    }
    return jwt.encode(claims, _DOCUMENT_EXPLANATION_KEY, algorithm="HS256")


def _document_explanation_claims(payload: DocumentExplanationRequest, user: User) -> dict:
    not_found = HTTPException(status_code=404, detail="Segmen analisis tidak ditemukan.")
    try:
        claims = jwt.decode(
            payload.explanation_token, _DOCUMENT_EXPLANATION_KEY,
            algorithms=["HS256"], audience=_DOCUMENT_EXPLANATION_AUDIENCE,
            options={"verify_exp": False, "require_aud": True, "require_sub": True},
        )
    except JWTError:
        raise not_found from None
    if claims.get("sub") != str(user.id) or claims.get("token_version") != user.token_version:
        raise not_found
    try:
        text_hash = hashlib.sha256(payload.text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        raise not_found from None
    if claims.get("text_sha256") != text_hash or type(claims.get("token_count")) is not int:
        raise not_found
    # Beberkan pesan kedaluwarsa hanya setelah pemilik dan teks cocok.
    expires = claims.get("exp")
    if type(expires) is not int:
        raise not_found
    if expires <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=409, detail="Akses penjelasan telah berakhir. Analisis ulang naskah.")
    return claims


@router.post("/document", response_model=DocumentAnalysisResponse)
def detect_document(
    payload: DocumentAnalysisRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """Analisis naskah eksperimental untuk sesi aktif."""
    started = perf_counter()
    response.headers["Cache-Control"] = "no-store"
    blocks, missing_pages = _document_blocks(payload)
    text = "\n\n".join(block["text"] for block in blocks)
    if len(text) > MAX_CHARS:
        raise HTTPException(status_code=413, detail=f"Naskah melebihi {MAX_CHARS} karakter. Bagi naskah menjadi beberapa pengiriman.")

    total_words = len(text.split())
    validation = validate_input_text(text)
    rejection = None
    sub_topik = None
    if not validation["ok"]:
        rejection = validation["reason"]
    else:
        in_domain, topic, _ = check_political_domain(validation["text"])
        if in_domain:
            sub_topik = topic
        else:
            rejection = "Naskah berada di luar cakupan politik Indonesia."
    if rejection:
        return DocumentAnalysisResponse(
            status="ditolak", total_words=total_words, analyzed_words=0,
            missing_pages=missing_pages, segments=[], reason=rejection,
            latency_seconds=round(perf_counter() - started, 3),
        )

    if not _document_lock.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Analisis naskah lain sedang diproses. Silakan coba lagi.")
    try:
        rows, model_identity = _analyze_document_blocks(blocks)
        segments = [DocumentSegmentResult.model_validate(row) for row in rows]
        analyzed_words = _document_words_analyzed(text, blocks, segments)
        for segment in segments:
            if model_identity and segment.status in ("dinilai", "ambigu"):
                segment.explanation_token = _document_explanation_token(current_user, segment, model_identity)
    except Exception as exc:
        logger.error("Analisis naskah gagal (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Analisis naskah gagal. Silakan coba lagi.") from None
    finally:
        _document_lock.release()

    if not analyzed_words:
        outcome = "gagal"
        reason = "Tidak ada segmen yang berhasil dinilai. Periksa alasan pada segmen."
    elif missing_pages or analyzed_words < total_words:
        outcome = "parsial"
        reason = "Sebagian sumber belum dinilai. Periksa halaman dan segmen yang belum tersedia."
    else:
        outcome = "lengkap"
        reason = None
    return DocumentAnalysisResponse(
        status=outcome, total_words=total_words, analyzed_words=analyzed_words,
        missing_pages=missing_pages, segments=segments, reason=reason,
        sub_topik=sub_topik, latency_seconds=round(perf_counter() - started, 3),
    )


@router.post("/document/explain", response_model=ExplanationResponse)
def explain_document(
    payload: DocumentExplanationRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """Jelaskan segmen utuh yang telah dinilai untuk akun ini."""
    from src.ml.inference import get_predictor

    response.headers["Cache-Control"] = "no-store"
    claims = _document_explanation_claims(payload, current_user)

    if not _lime_lock.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Penjelasan lain sedang diproses. Coba lagi sebentar.")
    try:
        penilai = get_predictor()
        if penilai.document_model_identity() != claims.get("model"):
            raise HTTPException(status_code=409, detail="Model telah berubah. Analisis ulang naskah untuk meminta penjelasan.")
        explanation = penilai.explain_document_segment(payload.text, claims["token_count"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("LIME segmen naskah gagal (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Penjelasan segmen gagal dibuat. Silakan coba lagi.") from None
    finally:
        _lime_lock.release()

    if (
        not isinstance(explanation, dict)
        or explanation.get("explanation_available") is not True
        or explanation.get("teks_dijelaskan") != payload.text
    ):
        raise HTTPException(status_code=502, detail="Penjelasan segmen gagal dibuat. Hasil klasifikasi tetap berlaku.")
    return ExplanationResponse(status="success", message="Penjelasan segmen tersedia.", explanation=explanation)


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
    except Exception as exc:
        db.rollback()
        logger.error("Inferensi gagal (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan pada mesin AI. Silakan coba lagi."
        ) from None

    try:
        validate_claim_result(result)
    except (ValueError, OverflowError):
        db.rollback()
        logger.error("Keluaran mesin AI tidak memenuhi kontrak deteksi teks")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan pada mesin AI. Silakan coba lagi."
        ) from None

    process_status = result["status"]
    model_ran = process_status in ("dinilai", "ambigu")
    reason = result.get("reason")
    sub_topik = result.get("sub_topik")
    raw_terpotong = result.get("terpotong")
    terpotong = raw_terpotong if isinstance(raw_terpotong, bool) else None
    log_entry = PredictionLog(
        user_id=current_user.id,
        input_text=raw_text,
        input_type=payload.input_type,
        image_url=payload.image_url,
        is_political=True,
        political_topic=sub_topik or guardrail_topic or "ALL",
        detected_entities=entities if entities else result.get("detected_entities", []),
        process_status=process_status,
        pattern_label=result["label"] if model_ran else None,
        agreement_ratio=result.get("agreement_ratio"),
        latency_seconds=result["latency_seconds"],
        lime_explanation=result.get("lime_explanation") or result.get("explanation"),
        narrative_text=result.get("narrative_text"),
    )

    if not model_ran:
        resp_message = reason
    elif process_status == "ambigu":
        resp_message = "Verifikasi selesai: hasil konsensus model menunjukkan ambiguitas."
    else:
        resp_message = "Verifikasi berhasil diselesaikan."

    db.add(log_entry)
    db.flush()
    try:
        response = DetectionResponse(
            status="success" if model_ran else "rejected",
            message=resp_message,
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
                votes_hoax=result.get("votes_hoax"),
                seed_decisions=result.get("seed_decisions"),
                sub_topik=sub_topik,
                reason=reason,
                terpotong=terpotong,
                teks_dinilai=result.get("teks_dinilai"),
                explanation=log_entry.lime_explanation,
                narrative_text=log_entry.narrative_text,
                created_at=log_entry.created_at,
            ),
        )
    except ValidationError:
        db.rollback()
        logger.error("Respons deteksi teks tidak memenuhi kontrak API")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan pada mesin AI. Silakan coba lagi."
        ) from None

    db.commit()
    return response


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
    if isinstance(existing, dict) and existing.get("explanation_available") is True:
        return ExplanationResponse(
            status="success", message="Penjelasan tersedia.", explanation=existing
        )

    explain_fn = getattr(predictor, "explain", None)
    if explain_fn is None:
        raise HTTPException(
            status_code=501,
            detail="Penjelasan LIME belum tersedia pada mesin AI."
        )

    if not _lime_lock.acquire(timeout=15.0):
        raise HTTPException(
            status_code=503,
            detail="Penjelasan lain sedang diproses. Coba lagi sebentar."
        )
    try:
        # Baca ulang dari DB setelah memperoleh lock agar request bersamaan tidak menghitung ulang
        db.refresh(log)
        existing = log.lime_explanation
        if isinstance(existing, dict) and existing.get("explanation_available") is True:
            return ExplanationResponse(
                status="success", message="Penjelasan tersedia.", explanation=existing
            )

        try:
            explanation = explain_fn(log.input_text)
        except Exception as exc:
            logger.error("LIME gagal (%s)", type(exc).__name__)
            raise HTTPException(status_code=500, detail="Penjelasan gagal dibuat.")

        # LIME gagal (_lime menangkap galat sendiri): jangan simpan, jangan dibalas "success"
        if not (isinstance(explanation, dict) and explanation.get("explanation_available") is True):
            raise HTTPException(
                status_code=502,
                detail="Penjelasan gagal dibuat. Hasil klasifikasi tetap berlaku; coba lagi nanti."
            )

        log.lime_explanation = explanation
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Gagal menyimpan penjelasan LIME (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Penjelasan gagal disimpan.")
    finally:
        _lime_lock.release()

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
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
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
            status.HTTP_413_CONTENT_TOO_LARGE
            if kode == "INPUT_UKURAN_BERKAS"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=pesan)

    if kategori == KATEGORI_KUALITAS:
        raw_fitur = h.get("fitur")
        fitur = raw_fitur if isinstance(raw_fitur, dict) else {}

        raw_teks = h.get("teks_bersih")
        n_karakter = len(raw_teks) if isinstance(raw_teks, str) else None

        # n_kata: integer, bukan boolean, dan tidak boleh negatif
        raw_kata = fitur.get("n_kata")
        n_kata = (
            raw_kata
            if isinstance(raw_kata, int) and not isinstance(raw_kata, bool) and raw_kata >= 0
            else None
        )

        # conf: angka, bukan boolean, rentang [0.0, 1.0], dan finite (bukan NaN / Inf)
        raw_conf = fitur.get("conf_rata2")
        conf = (
            raw_conf
            if not isinstance(raw_conf, bool)
            and isinstance(raw_conf, (int, float))
            and 0.0 <= raw_conf <= 1.0
            and math.isfinite(raw_conf)
            else None
        )

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
