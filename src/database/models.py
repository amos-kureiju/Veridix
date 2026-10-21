import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Text, Float, DateTime, ForeignKey, 
    UniqueConstraint, Enum, Integer
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

    detections = relationship("PredictionLog", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", foreign_keys="UserFeedback.user_id")
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_code = Column(String(10), nullable=False, index=True)  # Sesuai kode Anda (VARCHAR 10)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reset_tokens")


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    input_text = Column(Text, nullable=False)
    input_type = Column(String(20), default="TEXT", nullable=False)
    
    # Domain & Guardrail
    is_political = Column(Boolean, default=True, nullable=False)
    political_topic = Column(String(100), default="ALL", nullable=True)
    detected_entities = Column(JSONB, nullable=True)  # List entitas dari guardrail
    
    # Hasil AI yang jujur
    process_status = Column(String(30), default="DINILAI", nullable=False) # DINILAI, AMBIGU, DI_LUAR_DOMAIN, DITOLAK
    pattern_label = Column(String(50), nullable=True)                     # BERPOLA HOAKS, TIDAK BERPOLA HOAKS, PERLU KONFIRMASI
    agreement_ratio = Column(Float, nullable=True)                        # Rasio konsensus seed (misal 1.0 = 3/3, 0.67 = 2/3), NULL jika ditolak
    latency_seconds = Column(Float, nullable=False)                       # Latensi komputasi aktual
    
    # Explainability (LIME / Token Attention)
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
    claimed_label = Column(String(50), nullable=True)  # BERPOLA HOAKS / TIDAK BERPOLA HOAKS
    user_notes = Column(Text, nullable=True)
    clarification_url = Column(Text, nullable=True)    # Ditampung pada model agar tidak error saat diisi
    
    # Review Admin
    review_status = Column(String(30), default="PENDING", nullable=False) # PENDING, REVIEWED, DISMISSED
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('detection_id', 'user_id', name='uq_feedback_per_user_detection'),
    )

    detection = relationship("PredictionLog", back_populates="feedbacks")
    user = relationship("User", foreign_keys=[user_id], back_populates="feedbacks")
    reviewer = relationship("User", foreign_keys=[reviewed_by])