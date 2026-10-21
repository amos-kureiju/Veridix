from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from uuid import UUID

# --- REQUEST SCHEMAS ---
class TextDetectionRequest(BaseModel):
    text: str = Field(..., min_length=30, description="Naskah berita minimal 30 karakter")

class FeedbackCreateRequest(BaseModel):
    detection_id: Optional[Any] = None
    log_id: Optional[Any] = None
    is_agreed: Optional[bool] = False
    claimed_label: Optional[str] = None
    user_claimed_label: Optional[str] = None
    user_notes: Optional[str] = None
    notes: Optional[str] = None
    clarification_url: Optional[str] = None

class FeedbackReviewRequest(BaseModel):
    admin_notes: Optional[str] = Field(None, max_length=1000)
    review_status: str = Field(..., pattern="^(REVIEWED|DISMISSED)$")

# --- RESPONSE SCHEMAS ---
class LimeToken(BaseModel):
    word: str
    weight: float
    influence: str  # 'hoax', 'fact', 'KE_HOAKS', 'KE_TIDAK_HOAKS'

class TopWord(BaseModel):
    word: str
    score: float

class ExplanationSchema(BaseModel):
    tokens: List[LimeToken] = []
    top_hoax_words: List[TopWord] = []
    top_fact_words: List[TopWord] = []

class DetectionData(BaseModel):
    id: Optional[str] = None
    is_political: bool = True
    political_topic: Optional[str] = "POLITIK"
    prediction: str  # "HOAKS", "FAKTA", "PERLU KONFIRMASI"
    process_status: Optional[str] = "DINILAI"
    pattern_label: Optional[str] = None
    confidence_score: float
    agreement_ratio: Optional[float] = None
    inference_time_seconds: float
    extracted_text: str
    entities_detected: List[str] = []
    narrative_explanation: Optional[str] = None
    explanation: Optional[ExplanationSchema] = None

class DetectionResponse(BaseModel):
    status: str = "success"
    data: DetectionData
