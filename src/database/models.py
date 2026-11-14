import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Text, Float, DateTime, ForeignKey, 
    UniqueConstraint, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import relationship
from src.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    google_sub = Column(String(255), unique=True, nullable=True, index=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    google_challenges = relationship("GoogleAuthChallenge", back_populates="user", cascade="all, delete-orphan")
    full_name = Column(String(150), nullable=False)
    avatar_url = Column(Text, nullable=True)
    role = Column(
        ENUM("USER", "ADMIN", name="user_role_enum", create_type=False, validate_strings=True),
        default="USER",
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    threshold_changes = relationship("ThresholdHistory", foreign_keys="ThresholdHistory.modified_by", back_populates="admin_user")

    @property
    def feedbacks(self):
        return self.feedbacks_given


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_code = Column(String(64), nullable=False, index=True)
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
    image_url = Column(Text, nullable=True)
    
    is_political = Column(Boolean, default=True, nullable=False)
    political_topic = Column(String(100), default="ALL", nullable=True)
    detected_entities = Column(JSONB, nullable=True)
    
    process_status = Column(String(30), default="DINILAI", nullable=False)
    pattern_label = Column(String(50), nullable=True)
    agreement_ratio = Column(Float, nullable=True)
    latency_seconds = Column(Float, nullable=False)
    
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
    claimed_label = Column(String(50), nullable=True)
    user_notes = Column(Text, nullable=True)
    clarification_url = Column(Text, nullable=True)
    
    review_status = Column(String(30), default="PENDING", nullable=False)
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
    __tablename__ = "admin_settings"

    # Sinkron dengan DDL Supabase: memiliki id dan memakai setting_key/setting_value
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    admin = relationship("User")

    # Properti alias untuk kompatibilitas ke belakang
    @property
    def key(self):
        return self.setting_key
    @key.setter
    def key(self, val):
        self.setting_key = val

    @property
    def value(self):
        return self.setting_value
    @value.setter
    def value(self, val):
        self.setting_value = val


class ThresholdHistory(Base):
    # Sinkron dengan DDL Supabase: nama tabel 'threshold_history' (singular)
    __tablename__ = "threshold_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    old_threshold = Column(Float, nullable=True)
    new_threshold = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    admin_user = relationship("User", foreign_keys=[modified_by], back_populates="threshold_changes")

class GoogleAuthChallenge(Base):
    __tablename__ = "google_auth_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nonce_hash = Column(String(64), nullable=False, index=True)
    browser_binding_hash = Column(String(64), nullable=False)
    purpose = Column(String(20), nullable=False)  # 'login' atau 'link'
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="google_challenges")
