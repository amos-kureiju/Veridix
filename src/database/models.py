import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Text, Float, DateTime, ForeignKey, 
    UniqueConstraint, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    feedbacks_given = relationship(
        "UserFeedback", 
        foreign_keys="UserFeedback.user_id", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    feedbacks_reviewed = relationship(
        "UserFeedback", 
        foreign_keys="UserFeedback.reviewed_by", 
        back_populates="reviewer"
    )
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    threshold_changes = relationship("ThresholdHistory", back_populates="admin_user")

    # Backward compatibility jika ada kode yang mengakses user.feedbacks
    @property
    def feedbacks(self):
        return self.feedbacks_given


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_code = Column(String(10), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reset_tokens")


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    input_text = Column(Text, nullable=False)
    input_type = Column(String(20), default="TEXT", nullable=False)  # 'TEXT' | 'IMAGE'
    image_url = Column(Text, nullable=True)                         # Mengembalikan referensi gambar OCR
    
    # Domain & Guardrail
    is_political = Column(Boolean, default=True, nullable=False)
    political_topic = Column(String(100), default="ALL", nullable=True)
    detected_entities = Column(JSONB, nullable=True)
    
    # Hasil AI
    process_status = Column(String(30), default="DINILAI", nullable=False)  # DINILAI, AMBIGU, DI_LUAR_DOMAIN, DITOLAK
    pattern_label = Column(String(50), nullable=True)                      # BERPOLA HOAKS, TIDAK BERPOLA HOAKS, PERLU KONFIRMASI
    agreement_ratio = Column(Float, nullable=True)                         # NULL jika ditolak/di luar domain
    latency_seconds = Column(Float, nullable=False)
    
    # Explainability (LIME / Attention)
    lime_explanation = Column(JSONB, nullable=True)
    narrative_text = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="detections")
    feedbacks = relationship("UserFeedback", back_populates="detection", cascade="all, delete-orphan")


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_id = Column(UUID(as_uuid=True), ForeignKey("prediction_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    is_agreed = Column(Boolean, nullable=False)
    claimed_label = Column(String(50), nullable=True)  # BERPOLA HOAKS, TIDAK BERPOLA HOAKS, PERLU KONFIRMASI
    user_notes = Column(Text, nullable=True)
    clarification_url = Column(Text, nullable=True)
    
    # Alur Review Admin & Retraining
    review_status = Column(String(30), default="PENDING", nullable=False)  # PENDING, REVIEWED, DISMISSED, RETRAINED
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('detection_id', 'user_id', name='uq_feedback_per_user_detection'),
    )

    detection = relationship("PredictionLog", back_populates="feedbacks")
    user = relationship("User", foreign_keys=[user_id], back_populates="feedbacks_given")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="feedbacks_reviewed")


class AdminSetting(Base):
    """Menyimpan konfigurasi dinamis sistem/model AI (misal: threshold, active guardrails)."""
    __tablename__ = "admin_settings"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    admin = relationship("User")


class ThresholdHistory(Base):
    """Menyimpan jejak audit saat admin mengubah threshold ambang batas keyakinan model."""
    __tablename__ = "threshold_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key = Column(String(100), default="classification_threshold", nullable=False)
    old_value = Column(Float, nullable=True)
    new_value = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    admin_user = relationship("User", back_populates="threshold_changes")