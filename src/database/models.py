from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.session import Base

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    input_text = Column(Text, nullable=False)
    prediction = Column(String(10), nullable=False)  # 'HOAX' atau 'FACT'
    confidence_score = Column(Float, nullable=False) # 0.0 - 1.0
    is_political = Column(Boolean, default=True)
    inference_time = Column(Float, nullable=False)    # dalam detik
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi ke feedback jika ada
    feedbacks = relationship("UserFeedback", back_populates="prediction_log")


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(Integer, ForeignKey("prediction_logs.id"), nullable=False)
    user_claimed_label = Column(String(10), nullable=False) # Klaim user: 'HOAX' / 'FACT'
    clarification_url = Column(String(500), nullable=True)  # Link bukti sumber
    notes = Column(Text, nullable=True)                     # Alasan koreksi
    status = Column(String(20), default="PENDING")          # 'PENDING' / 'VERIFIED'
    created_at = Column(DateTime, default=datetime.utcnow)

    prediction_log = relationship("PredictionLog", back_populates="feedbacks")


class AdminSetting(Base):
    __tablename__ = "admin_settings"

    key = Column(String(50), primary_key=True, index=True)
    value = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)