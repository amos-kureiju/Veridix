from pydantic import BaseModel, Field
from typing import List, Optional

# --- SCHEMA REQUEST ---
class TextDetectionRequest(BaseModel):
    text: str = Field(..., min_length=20, description="Naskah berita minimal 20 karakter")

class FeedbackCreateRequest(BaseModel):
    log_id: int
    user_claimed_label: str = Field(..., pattern="^(HOAX|FACT)$")
    clarification_url: Optional[str] = None
    notes: Optional[str] = None

# --- SCHEMA RESPONSE ---
class LimeToken(BaseModel):
    word: str
    weight: float
    influence: str  # 'HOAX', 'FACT', atau 'NEUTRAL'

class ExplanationSchema(BaseModel):
    tokens: List[LimeToken]
    top_hoax_words: List[dict]
    top_fact_words: List[dict]

class DetectionData(BaseModel):
    is_political: bool
    prediction: str
    confidence_score: float
    inference_time_seconds: float
    extracted_text: str
    entities_detected: List[str]
    explanation: ExplanationSchema

class DetectionResponse(BaseModel):
    status: str
    data: DetectionData