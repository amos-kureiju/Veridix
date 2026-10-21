from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime

# 1. DETECTION SCHEMAS (TEXT & IMAGE)

class TextDetectionRequest(BaseModel):
    """
    Digunakan untuk teks langsung maupun teks hasil verifikasi/koreksi OCR.
    Jika input berasal dari OCR, sertakan input_type="IMAGE" dan image_url.
    """
    text: str = Field(..., min_length=30, description="Naskah berita minimal 30 karakter")
    input_type: str = Field("TEXT", pattern="^(TEXT|IMAGE)$", description="Asal input: TEXT atau IMAGE")
    image_url: Optional[str] = Field(None, description="URL gambar jika bersumber dari proses OCR")


class OCRResultData(BaseModel):
    """Payload hasil ekstraksi teks dari gambar melalui PaddleOCR."""
    extracted_text: str
    dapat_dinilai: bool = Field(..., description="True jika kualitas teks layak untuk dianalisis oleh IndoBERT")
    confidence: Optional[float] = None
    character_count: int
    image_url: Optional[str] = None
    reason: Optional[str] = Field(None, description="Alasan jika teks tidak layak dinilai (misal: teks terlalu pendek/buram)")


class OCRResponse(BaseModel):
    status: str
    message: str
    data: OCRResultData


class DetectionResultData(BaseModel):
    id: UUID
    input_text: str
    input_type: str
    image_url: Optional[str] = None
    process_status: str             # DINILAI, AMBIGU, DI_LUAR_DOMAIN, DITOLAK
    pattern_label: Optional[str]    # BERPOLA HOAKS, TIDAK BERPOLA HOAKS, PERLU KONFIRMASI
    agreement_ratio: Optional[float]
    latency_seconds: float
    is_political: bool
    political_topic: Optional[str]
    detected_entities: List[str] = []
    explanation: Optional[Dict[str, Any]] = None
    narrative_text: Optional[str] = None
    created_at: Optional[datetime] = None


class DetectionResponse(BaseModel):
    status: str
    message: str
    data: DetectionResultData


# ==========================================
# 2. FEEDBACK SCHEMAS
# ==========================================

class FeedbackCreateRequest(BaseModel):
    detection_id: UUID
    is_agreed: bool
    claimed_label: Optional[str] = Field(
        None, 
        pattern="^(BERPOLA HOAKS|TIDAK BERPOLA HOAKS|PERLU KONFIRMASI)$"
    )
    user_notes: Optional[str] = Field(None, max_length=1000)
    clarification_url: Optional[str] = None


class FeedbackReviewRequest(BaseModel):
    admin_notes: Optional[str] = Field(None, max_length=1000)
    review_status: str = Field(..., pattern="^(REVIEWED|DISMISSED|RETRAINED)$")


class FeedbackResponseData(BaseModel):
    id: UUID
    detection_id: UUID
    user_id: UUID
    is_agreed: bool
    claimed_label: Optional[str]
    user_notes: Optional[str]
    clarification_url: Optional[str]
    review_status: str
    admin_notes: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime


class FeedbackResponse(BaseModel):
    status: str
    message: str
    data: Optional[FeedbackResponseData] = None


# ==========================================
# 3. ADMIN SETTING & THRESHOLD SCHEMAS
# ==========================================

class ThresholdUpdateRequest(BaseModel):
    new_threshold: float = Field(..., ge=0.0, le=1.0, description="Nilai threshold keyakinan (0.0 - 1.0)")
    reason: Optional[str] = Field(None, max_length=500, description="Alasan perubahan threshold")


class SettingUpdateRequest(BaseModel):
    value: str
    description: Optional[str] = None