from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Any, Dict
from uuid import UUID

# --- REQUEST SCHEMAS ---
class TextDetectionRequest(BaseModel):
    text: str = Field(..., min_length=30, description="Naskah berita minimal 30 karakter")

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
    review_status: str = Field(..., pattern="^(REVIEWED|DISMISSED)$")

# --- RESPONSE SCHEMAS ---
class DetectionResultData(BaseModel):
    id: UUID
    process_status: str             # DINILAI, AMBIGU, DI_LUAR_DOMAIN
    pattern_label: Optional[str]    # BERPOLA HOAKS, TIDAK BERPOLA HOAKS, atau None jika ditolak
    agreement_ratio: Optional[float]
    latency_seconds: float
    is_political: bool
    political_topic: Optional[str]
    detected_entities: List[str] = []
    explanation: Optional[Dict[str, Any]] = None
    narrative_text: Optional[str] = None

class DetectionResponse(BaseModel):
    status: str
    message: str
    data: DetectionResultData