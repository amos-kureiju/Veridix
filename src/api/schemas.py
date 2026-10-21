from pydantic import BaseModel, Field
from typing import List, Optional, Any

# --- SCHEMA REQUEST ---
class TextDetectionRequest(BaseModel):
    text: str = Field(..., min_length=20, description="Naskah berita minimal 20 karakter")

class FeedbackCreateRequest(BaseModel):
    log_id: Any
    user_claimed_label: str = Field(..., pattern="^(HOAKS|FAKTA|HOAX|FACT)$")
    clarification_url: Optional[str] = None
    notes: Optional[str] = None

# --- SCHEMA RESPONSE ---
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
    confidence_score: float
    inference_time_seconds: float
    extracted_text: str
    entities_detected: List[str] = []
    narrative_explanation: Optional[str] = None
    explanation: Optional[ExplanationSchema] = None

class DetectionResponse(BaseModel):
    status: str = "success"
    data: DetectionData
