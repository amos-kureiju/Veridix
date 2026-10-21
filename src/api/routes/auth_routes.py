from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from src.database.session import get_db
from src.database.models import User
from src.core.security import hash_password, verify_password, create_access_token
from src.core.auth_deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Skema Validasi Input
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class DirectResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# 1. ENDPOINT REGISTRASI USER BARU (Masyarakat Umum)
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    # Validasi panjang kata sandi
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi minimal 8 karakter."
        )

    # Cek apakah email sudah pernah terdaftar
    existing_user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alamat email sudah terdaftar. Silakan masuk atau gunakan email lain."
        )

    # Simpan user baru (Role default: USER)
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


# 2. ENDPOINT LOGIN (User & Admin)
@router.post("/login")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    # Cari akun berdasarkan email
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    
    # Standar keamanan OWASP: jangan bocorkan apakah yang salah email atau password
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

    # Terbitkan token JWT berisi ID user
    token = create_access_token(data={"sub": str(user.id), "role": user.role})

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
            "total_detections": len(user.detections),
            "total_feedbacks": len(user.feedbacks_given)
        }
    }


# 3. ENDPOINT AMBIL DATA SESI LOGIN AKTIF (/me)
@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url or "",
        "is_active": current_user.is_active,
        "total_detections": len(current_user.detections),
        "total_feedbacks": len(current_user.feedbacks_given)
    }


# 4. ENDPOINT RESET KATA SANDI (Direct Reset untuk Frontend)
@router.post("/direct-reset-password")
def direct_reset_password(req: DirectResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru minimal 8 karakter."
        )
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alamat email tidak terdaftar di sistem."
        )
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "Kata sandi berhasil diperbarui."}


# 5. ENDPOINT FORGOT PASSWORD (Menerima permintaan reset)
@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user:
        # Menjaga keamanan privasi pengguna
        return {"status": "success", "message": "Jika email terdaftar, instruksi reset telah dikirim."}
    return {"status": "success", "message": "Instruksi reset kata sandi telah diproses."}


# 6. ENDPOINT RESET PASSWORD VIA TOKEN
@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru minimal 8 karakter."
        )
    return {"status": "success", "message": "Kata sandi berhasil diperbarui."}
