from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from src.database.session import get_db
from src.database.models import User
from src.core.security import hash_password, verify_password
from src.core.auth_deps import get_current_user

router = APIRouter(prefix="/user", tags=["User Operations"])

class UpdateProfilePayload(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None

class ChangePasswordPayload(BaseModel):
    old_password: Optional[str] = None
    new_password: str
    confirm_password: str

@router.patch("/profile")
def update_profile(
    payload: UpdateProfilePayload, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.name:
        current_user.full_name = payload.name.strip()
    if payload.email:
        new_email = payload.email.lower().strip()
        if new_email != current_user.email:
            existing = db.query(User).filter(User.email == new_email).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Alamat email sudah digunakan oleh akun lain."
                )
            current_user.email = new_email
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    db.commit()
    db.refresh(current_user)

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

@router.post("/change-password")
def change_password(
    payload: ChangePasswordPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfirmasi kata sandi tidak cocok."
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru minimal 8 karakter."
        )

    # Jika old_password disediakan, lakukan verifikasi
    if payload.old_password and not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama tidak sesuai."
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "success", "message": "Kata sandi berhasil diperbarui."}

@router.delete("/delete-account")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.delete(current_user)
    db.commit()
    return {"status": "success", "message": "Akun berhasil dihapus."}
