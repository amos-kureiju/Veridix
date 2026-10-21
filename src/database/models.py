import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, Float,
    ForeignKey, DateTime, Enum as SQLEnum, UniqueConstraint, JSON, Uuid
)
from sqlalchemy.orm import relationship
from src.database.session import Base

# =========================================================================
# 1. TABEL USERS (Autentikasi Akun & Peran)
# =========================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    avatar_url = Column(Text, nullable=True)
    role = Column(String(20), default="USER", nullable=False)  # 'USER' | 'ADMIN'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relasi
    detections = relationship("PredictionLog", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", foreign_keys="UserFeedback.user_id")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

    @property
    def feedbacks_given(self):
        return self.feedbacks or []


# =========================================================================
# 2. TABEL PASSWORD RESET TOKENS
# =========================================================================
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_code = Column(String(10), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reset_tokens")


# =========================================================================
# 3. TABEL PREDICTION_LOGS (Log Inferensi IndoBERT + OCR)
# =========================================================================
class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    input_text = Column(Text, nullable=False)
    input_type = Column(String(20), default="TEXT", nullable=False)
    image_url = Column(Text, nullable=True)
    
    # Domain & Guardrail
    is_political = Column(Boolean, default=True, nullable=False)
    political_topic = Column(String(100), default="ALL", nullable=True)
    detected_entities = Column(JSON, nullable=True)  # List entitas / istilah
    
    # Hasil Klasifikasi
    process_status = Column(String(30), default="DINILAI", nullable=False) # DINILAI, AMBIGU, DI_LUAR_DOMAIN, DITOLAK
    pattern_label = Column(String(50), nullable=True)                     # BERPOLA HOAKS, TIDAK BERPOLA HOAKS, PERLU KONFIRMASI
    verdict = Column(String(50), nullable=True, index=True)               # HOAKS, FAKTA, PERLU KONFIRMASI
    confidence_score = Column(Float, nullable=True)
    agreement_ratio = Column(Float, nullable=True)
    inference_time_ms = Column(Integer, nullable=True)
    latency_seconds = Column(Float, nullable=True)
    
    # Explainability (LIME / Token Attention)
    lime_explanation = Column(JSON, nullable=True)
    narrative_text = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relasi
    user = relationship("User", back_populates="detections")
    feedbacks = relationship("UserFeedback", back_populates="detection", cascade="all, delete-orphan")


# =========================================================================
# 4. TABEL USER_FEEDBACKS (Active Learning / Sanggahan)
# =========================================================================
class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    detection_id = Column(Uuid, ForeignKey("prediction_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    is_agreed = Column(Boolean, nullable=False)
    claimed_label = Column(String(50), nullable=True)  # BERPOLA HOAKS / TIDAK BERPOLA HOAKS
    user_notes = Column(Text, nullable=True)
    clarification_url = Column(Text, nullable=True)
    
    # Review Admin
    review_status = Column(String(30), default="PENDING", nullable=False) # PENDING, REVIEWED, DISMISSED
    reviewed_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('detection_id', 'user_id', name='uq_feedback_per_user_detection'),
    )

    # Relasi
    detection = relationship("PredictionLog", back_populates="feedbacks")
    user = relationship("User", foreign_keys=[user_id], back_populates="feedbacks")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


# =========================================================================
# 5. TABEL ADMIN_SETTINGS & THRESHOLD_HISTORY (Audit Trail Ilmiah)
# =========================================================================
class AdminSetting(Base):
    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ThresholdHistory(Base):
    __tablename__ = "threshold_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    old_threshold = Column(Numeric(4, 2), nullable=False)
    new_threshold = Column(Numeric(4, 2), nullable=False)
    reason = Column(Text, nullable=True)
    modified_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
