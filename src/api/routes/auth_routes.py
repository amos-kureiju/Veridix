from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.session import get_db
from src.database.models import User, PredictionLog, UserFeedback
from src.core.security import hash_password, verify_password, create_access_token
from src.core.auth_deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# 1. REGISTRASI
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
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "success",
        "message": "Akun berhasil dibuat. Silakan login."
    }


# 2. LOGIN (Perbaikan: Query COUNT Ringan Tanpa Lazy Load Kolom AI)
@router.post("/login")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    
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

    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    # Hitung total deteksi secara aman (HANYA membaca kolom id & user_id)
    try:
        total_detections = db.query(func.count(PredictionLog.id)).filter(PredictionLog.user_id == user.id).scalar() or 0
    except Exception:
        db.rollback()
        total_detections = 0

    # Hitung total feedback secara aman
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


# 3. GET PROFILE /auth/me (Perbaikan: Query COUNT Ringan)
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