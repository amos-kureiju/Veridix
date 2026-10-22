from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime

# DETECTION SCHEMAS
class TextDetectionRequest(BaseModel):
    text: str = Field(..., min_length=30, description="Naskah berita minimal 30 karakter")
    input_type: str = Field("TEXT", pattern="^(TEXT|IMAGE)$")
    image_url: Optional[str] = None

class OCRResultData(BaseModel):
    extracted_text: str
    dapat_dinilai: bool
    confidence: Optional[float] = None
    character_count: int
    image_url: Optional[str] = None
    reason: Optional[str] = None

class OCRResponse(BaseModel):
    status: str
    message: str
    data: OCRResultData

class DetectionResultData(BaseModel):
    id: UUID
    input_text: str
    input_type: str
    image_url: Optional[str] = None
    process_status: str
    pattern_label: Optional[str]
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

# FEEDBACK SCHEMAS
class FeedbackCreateRequest(BaseModel):
    detection_id: UUID
    is_agreed: bool
    claimed_label: Optional[str] = Field(None, pattern="^(BERPOLA HOAKS|TIDAK BERPOLA HOAKS|PERLU KONFIRMASI)$")
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

# ADMIN SCHEMAS
class ThresholdUpdateRequest(BaseModel):
    new_threshold: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = Field(None, max_length=500)

class SettingUpdateRequest(BaseModel):
    value: str
    description: Optional[str] = None

    # UBAH HISTORY SCHEMAS ( Penyelarasan Riwayat )

class UserHistoryFeedbackItem(BaseModel):
    id: UUID
    is_agreed: bool
    claimed_label: Optional[str] = None
    review_status: Optional[str] = None
    admin_notes: Optional[str] = None

class UserHistoryItem(BaseModel):
    id: UUID
    input_text: str
    input_type: str
    image_url: Optional[str] = None
    political_topic: Optional[str] = None
    process_status: str = "DINILAI"
    pattern_label: Optional[str] = None
    prediction: Optional[str] = None
    agreement_ratio: Optional[float] = None
    confidence_score: Optional[float] = None
    created_at: Optional[datetime] = None
    has_feedback: bool = False
    feedback: Optional[UserHistoryFeedbackItem] = None

class UserHistoryResponse(BaseModel):
    status: str = "success"
    data: List[UserHistoryItem] = []