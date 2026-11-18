from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from typing import List, Optional, Any, Dict, Literal
from uuid import UUID
from datetime import datetime

from src.utils.input_validation import MAX_CHARS

# DETECTION SCHEMAS
class TextDetectionRequest(BaseModel):
    text: str = Field(..., min_length=30, description="Naskah berita minimal 30 karakter")
    input_type: str = Field("TEXT", pattern="^(TEXT|IMAGE)$")
    image_url: Optional[str] = None

DOCUMENT_MAX_PAGES = 4


class DocumentPageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_number: StrictInt = Field(ge=1, le=DOCUMENT_MAX_PAGES)
    text: Optional[str]


class DocumentAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Optional[str] = None
    pages: Optional[List[DocumentPageRequest]] = Field(default=None, min_length=1, max_length=DOCUMENT_MAX_PAGES)

    @model_validator(mode="after")
    def check_source(self):
        if (self.text is None) == (self.pages is None):
            raise ValueError("Kirim satu naskah teks atau halaman dari satu dokumen.")
        if self.pages is not None:
            for position, page in enumerate(self.pages, start=1):
                if page.page_number != position:
                    raise ValueError("Nomor halaman harus berurutan mulai dari satu.")
                if page.text is not None and not page.text.strip():
                    raise ValueError("Isi teks halaman atau tandai halaman belum terbaca dengan null.")
        return self


class DocumentSegmentResult(BaseModel):
    start_char: StrictInt = Field(ge=0)
    end_char: StrictInt = Field(gt=0)
    start_word: StrictInt = Field(gt=0)
    end_word: StrictInt = Field(gt=0)
    text: str
    token_count: Optional[StrictInt] = Field(gt=0)
    status: Literal["dinilai", "ambigu", "ditolak", "gagal", "belum_dinilai"]
    label: Optional[str]
    votes_hoax: Optional[str]
    reason: Optional[str]
    page_numbers: List[StrictInt]
    explanation_token: Optional[str] = None


class DocumentAnalysisResponse(BaseModel):
    status: Literal["lengkap", "parsial", "gagal", "ditolak"]
    total_words: int
    analyzed_words: int
    missing_pages: List[int]
    segments: List[DocumentSegmentResult]
    reason: Optional[str]
    sub_topik: Optional[str] = None
    latency_seconds: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)


class DocumentExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_CHARS)
    explanation_token: str = Field(min_length=1, max_length=2048)


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
    pattern_label: Optional[str] = None
    agreement_ratio: Optional[float] = None
    latency_seconds: float
    is_political: bool
    political_topic: Optional[str] = None
    detected_entities: List[str] = []
    votes_hoax: Optional[str] = None
    seed_decisions: Optional[Dict[int, Literal[0, 1]]] = None
    sub_topik: Optional[str] = None
    reason: Optional[str] = None
    terpotong: Optional[bool] = None
    teks_dinilai: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None
    narrative_text: Optional[str] = None
    created_at: Optional[datetime] = None

class DetectionResponse(BaseModel):
    status: str
    message: str
    data: DetectionResultData

class ExplanationResponse(BaseModel):
    status: str
    message: str
    explanation: Dict[str, Any]

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

class ManagedUserItem(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    analysis_count: int = Field(..., ge=0)
    has_password: bool
    google_linked: bool

class AdminUserListResponse(BaseModel):
    status: str = "success"
    data: List[ManagedUserItem] = []
    count: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    skip: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class UserStatusUpdateData(BaseModel):
    id: UUID
    is_active: bool


class UserStatusUpdateResponse(BaseModel):
    status: str = "success"
    message: str
    data: UserStatusUpdateData
