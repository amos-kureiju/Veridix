from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.database.session import get_db
from src.database.models import User
from src.core.auth_deps import get_current_user
from src.core.security import verify_password, hash_password

router = APIRouter(prefix="/users", tags=["Users"])


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, description="Kata sandi lama wajib diisi")
    new_password: str = Field(..., min_length=8, description="Kata sandi baru minimal 8 karakter")


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    avatar_url: str = None


@router.get("/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "avatar_url": current_user.avatar_url
        }
    }


@router.put("/profile")
def update_user_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.full_name = payload.full_name.strip()
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip()

    db.commit()
    db.refresh(current_user)
    return {
        "status": "success",
        "message": "Profil berhasil diperbarui."
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Perbaikan: Validasi ketat kata sandi lama (tidak boleh kosong atau salah)
    if not payload.old_password or not payload.old_password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama wajib diisi."
        )

    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama yang Anda masukkan salah."
        )

    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru tidak boleh sama dengan kata sandi lama."
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

    return {
        "status": "success",
        "message": "Kata sandi berhasil diperbarui. Silakan gunakan kata sandi baru untuk login."
    }