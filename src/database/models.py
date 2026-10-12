import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, 
    ForeignKey, DateTime, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# =========================================================================
# 1. TABEL USERS (Autentikasi Akun & Peran)
# =========================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    avatar_url = Column(Text, nullable=True)
    role = Column(
        SQLEnum("USER", "ADMIN", name="user_role_enum"), 
        default="USER", 
        nullable=False, 
        index=True
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relasi
    detections = relationship("PredictionLog", back_populates="user", cascade="all, delete-orphan")
    feedbacks_given = relationship("UserFeedback", back_populates="user", foreign_keys="UserFeedback.user_id", cascade="all, delete-orphan")
    feedbacks_reviewed = relationship("UserFeedback", back_populates="reviewer", foreign_keys="UserFeedback.reviewed_by")


# =========================================================================
# 2. TABEL PREDICTION_LOGS (Log Inferensi IndoBERT + OCR)
# =========================================================================
class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    input_type = Column(
        SQLEnum("TEXT", "IMAGE", name="input_type_enum"), 
        default="TEXT", 
        nullable=False
    )
    input_text = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    political_topic = Column(String(100), default="ALL", nullable=False)
    verdict = Column(
        SQLEnum("HOAKS", "FAKTA", "PERLU KONFIRMASI", name="verdict_enum"), 
        nullable=False, 
        index=True
    )
    confidence_score = Column(Numeric(5, 4), nullable=False)
    inference_time_ms = Column(Integer, nullable=False)
    lime_explanation = Column(JSONB, nullable=True)
    narrative_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relasi
    user = relationship("User", back_populates="detections")
    feedbacks = relationship("UserFeedback", back_populates="detection", cascade="all, delete-orphan")


# =========================================================================
# 3. TABEL USER_FEEDBACKS (Active Learning / Sanggahan)
# =========================================================================
class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_id = Column(UUID(as_uuid=True), ForeignKey("prediction_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_agreed = Column(Boolean, nullable=False)
    claimed_label = Column(
        SQLEnum("HOAKS", "FAKTA", "PERLU KONFIRMASI", name="verdict_enum"), 
        nullable=True
    )
    user_notes = Column(Text, nullable=True)
    status = Column(
        SQLEnum("PENDING", "REVIEWED", "RETRAINED", "DISMISSED", name="feedback_status_enum"), 
        default="PENDING", 
        nullable=False, 
        index=True
    )
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("detection_id", "user_id", name="uq_feedback_per_user_detection"),
    )

    # Relasi
    detection = relationship("PredictionLog", back_populates="feedbacks")
    user = relationship("User", foreign_keys=[user_id], back_populates="feedbacks_given")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="feedbacks_reviewed")


# =========================================================================
# 4. TABEL ADMIN_SETTINGS & THRESHOLD_HISTORY (Audit Trail Ilmiah)
# =========================================================================
class AdminSetting(Base):
    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ThresholdHistory(Base):
    __tablename__ = "threshold_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    old_threshold = Column(Numeric(4, 2), nullable=False)
    new_threshold = Column(Numeric(4, 2), nullable=False)
    reason = Column(Text, nullable=True)
    # SET NULL: Agar catatan eksperimen historis tetap abadi walau admin terkait dihapus
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)