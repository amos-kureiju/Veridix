import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.session import get_db
from src.database.models import User, PredictionLog, UserFeedback, PasswordResetToken
from src.core.security import hash_password, verify_password, create_access_token
from src.core.auth_deps import get_current_user
from src.core.config import settings
from src.utils.email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =====================================================================
# SKEMA REQUEST
# =====================================================================
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Token acak dari tautan email")
    new_password: str = Field(..., min_length=8, description="Kata sandi baru minimal 8 karakter")
    confirm_password: Optional[str] = None


# =====================================================================
# 1. REGISTRASI
# =====================================================================
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi minimal 8 karakter."
        )

    existing_user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alamat email sudah terdaftar. Silakan masuk atau gunakan email lain."
        )

    new_user = User(
        full_name=req.name.strip(),
        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        role="USER",
        is_active=True,
        token_version=0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "success",
        "message": "Akun berhasil dibuat. Silakan login."
    }


# =====================================================================
# 2. LOGIN (Memuat token_version ke dalam JWT Claim)
# =====================================================================
@router.post("/login")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    # PERBAIKAN: Gunakan func.lower() agar pencarian email case-insensitive
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email_clean).first()
    
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau kata sandi tidak cocok."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan oleh Administrator."
        )

    # Sertakan version untuk session revocation
    user_version = getattr(user, "token_version", 0) or 0
    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "token_version": user_version
    })

    try:
        total_detections = db.query(func.count(PredictionLog.id)).filter(PredictionLog.user_id == user.id).scalar() or 0
    except Exception:
        db.rollback()
        total_detections = 0

    try:
        total_feedbacks = db.query(func.count(UserFeedback.id)).filter(UserFeedback.user_id == user.id).scalar() or 0
    except Exception:
        db.rollback()
        total_feedbacks = 0

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.full_name,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url or "",
            "is_active": user.is_active,
            "total_detections": total_detections,
            "total_feedbacks": total_feedbacks
        }
    }


# =====================================================================
# 3. GET PROFILE /auth/me
# =====================================================================
@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        total_detections = db.query(func.count(PredictionLog.id)).filter(PredictionLog.user_id == current_user.id).scalar() or 0
    except Exception:
        db.rollback()
        total_detections = 0

    try:
        total_feedbacks = db.query(func.count(UserFeedback.id)).filter(UserFeedback.user_id == current_user.id).scalar() or 0
    except Exception:
        db.rollback()
        total_feedbacks = 0

    return {
        "id": str(current_user.id),
        "name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url or "",
        "is_active": current_user.is_active,
        "total_detections": total_detections,
        "total_feedbacks": total_feedbacks
    }


# =====================================================================
# 4. LUPA PASSWORD (Kirim Tautan Pemulihan via Email)
# =====================================================================
@router.post("/forgot-password")
def forgot_password(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Membuat token reset acak, menyimpan hash SHA-256 ke Supabase,
    dan mengirim tautan pemulihan ke inbox Gmail via background task.
    Respon selalu seragam (anti-enumeration OWASP).
    """
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()

    if user and user.is_active:
        # 1. Buat token acak yang kuat (32 bytes = 43 karakter aman URL)
        raw_token = secrets.token_urlsafe(32)
        # 2. Hash SHA-256 token (64 hex) untuk disimpan di database
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # 3. Batalkan token lama yang belum digunakan milik akun ini
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False
        ).update({"is_used": True})

        # 4. Simpan token baru dengan masa berlaku 15 menit
        expire_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        reset_entry = PasswordResetToken(
            user_id=user.id,
            token_code=token_hash,
            expires_at=expire_at,
            is_used=False
        )
        db.add(reset_entry)
        db.commit()

        # 5. Kirim token mentah melalui background task agar API tidak freeze
        background_tasks.add_task(send_password_reset_email, user.email, raw_token)

    # Respon umum yang sama baik email terdaftar maupun tidak terdaftar
    return {
        "status": "success",
        "message": "Jika email terdaftar di sistem kami, tautan pemulihan kata sandi telah dikirim ke kotak masuk Anda."
    }


# =====================================================================
# 5. RESET PASSWORD (Validasi Hash Token & Update Password)
# =====================================================================
@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if req.confirm_password and req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfirmasi kata sandi baru tidak cocok."
        )

    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru minimal 8 karakter."
        )

    # 1. Hash token dari request untuk dicocokkan dengan data Supabase
    token_hash = hashlib.sha256(req.token.strip().encode()).hexdigest()

    # 2. Cari token yang valid dan belum kedaluwarsa
    now = datetime.utcnow()
    token_record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_code == token_hash,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > now
        )
        .first()
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tautan reset kata sandi tidak valid atau sudah kedaluwarsa."
        )

    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Akun pengguna tidak ditemukan atau dinonaktifkan."
        )

    # 3. Cegah penggunaan password yang sama persis
    if verify_password(req.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru tidak boleh sama dengan kata sandi lama."
        )

    # 4. Update password & naikkan token_version (invalidasi seluruh sesi lama)
    user.password_hash = hash_password(req.new_password)
    user.token_version = (getattr(user, "token_version", 0) or 0) + 1
    user.updated_at = now

    # 5. Tandai token sudah digunakan
    token_record.is_used = True
    db.commit()

    return {
        "status": "success",
        "message": "Kata sandi berhasil diperbarui. Silakan login menggunakan kata sandi baru Anda."
    }