from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from src.api.schemas import (
    TextDetectionRequest, 
    DetectionResponse, 
    DetectionData, 
    ExplanationSchema, 
    LimeToken, 
    TopWord
)
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
    is_political, detected_topic, entities = check_political_domain(raw_text)
    if not is_political:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Naskah di luar jangkauan. Sistem dikhususkan untuk verifikasi isu sosial-politik Indonesia."
        )

    # 3. MASUK KE INDOBERT + LIME (Satu pintu: kirim raw_text murni tanpa double-cleaning)
    try:
        result = predictor.predict_and_explain(raw_text, explain=True, debug=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan pada mesin AI: {str(e)}"
        )

    # Mapping vonis dari output label sistem ke ENUM database & schema
    raw_label = str(result.get("label", ""))
    if "BERPOLA HOAKS" in raw_label or raw_label == "HOAKS":
        verdict = "HOAKS"
    elif "TIDAK BERPOLA HOAKS" in raw_label or raw_label == "FAKTA":
        verdict = "FAKTA"
    else:
        verdict = "PERLU KONFIRMASI"

    # Perhitungan Skor Keyakinan (Confidence Score)
    probs = result.get("debug", {}).get("prob_hoax_per_seed", [])
    if probs:
        mean_p = float(sum(probs) / len(probs))
        if verdict == "HOAKS":
            conf = mean_p
        elif verdict == "FAKTA":
            conf = 1.0 - mean_p
        else:
            conf = max(mean_p, 1.0 - mean_p)
    else:
        conf = 0.88
    confidence_score = round(float(conf), 4)

    # Waktu Inferensi & Topik
    latency_seconds = float(result.get("latency_seconds", 0.35))
    latency_ms = int(latency_seconds * 1000)
    topic = result.get("sub_topik") or "Politik Nasional"
    detected_terms = result.get("istilah", []) or entities or []

    # Penjelasan LIME & Distribusi Kata Kunci
    raw_explanation = result.get("explanation", {})
    lime_tokens_raw = raw_explanation.get("tokens", [])
    
    formatted_tokens: list[LimeToken] = []
    top_hoax: list[TopWord] = []
    top_fact: list[TopWord] = []

    for item in lime_tokens_raw:
        word = str(item.get("word", ""))
        weight = float(item.get("weight", 0.0))
        raw_influence = str(item.get("influence", "")).upper()
        
        # Standarisasi nilai influence untuk frontend: 'hoax' atau 'fact'
        influence = "hoax" if ("HOAKS" in raw_influence or weight > 0) else "fact"
        formatted_tokens.append(LimeToken(word=word, weight=abs(weight), influence=influence))
        
        if influence == "hoax":
            top_hoax.append(TopWord(word=word, score=abs(weight)))
        else:
            top_fact.append(TopWord(word=word, score=abs(weight)))

    top_hoax_sorted = sorted(top_hoax, key=lambda x: x.score, reverse=True)[:5]
    top_fact_sorted = sorted(top_fact, key=lambda x: x.score, reverse=True)[:5]

    explanation_schema = ExplanationSchema(
        tokens=formatted_tokens,
        top_hoax_words=top_hoax_sorted,
        top_fact_words=top_fact_sorted
    )

    narrative_explanation = (
        f"Model mendeteksi teks ini berkategori '{verdict}' pada topik '{topic}'. "
        f"Keyakinan prediksi tercatat sebesar {round(confidence_score * 100, 1)}%."
    )

    # 4. SIMPAN KE DATABASE (Sesuai Diagram Layer 6)
    log_entry = PredictionLog(
        input_text=payload.text,
        input_type="TEXT",
        political_topic=topic,
        verdict=verdict,
        confidence_score=confidence_score,
        inference_time_ms=latency_ms,
        lime_explanation=raw_explanation,
        narrative_text=narrative_explanation
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # 5. KEMBALIKAN OUTPUT SESUAI SCHEMA (Sesuai Diagram Layer 5)
    response_data = DetectionData(
        id=str(log_entry.id),
        is_political=True,
        political_topic=topic,
        prediction=verdict,
        confidence_score=confidence_score,
        inference_time_seconds=latency_seconds,
        extracted_text=result.get("teks_dinilai", raw_text),
        entities_detected=detected_terms,
        narrative_explanation=narrative_explanation,
        explanation=explanation_schema
    )

    return DetectionResponse(status="success", data=response_data)


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
