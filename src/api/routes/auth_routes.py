import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.auth_deps import get_current_user
from src.core.config import settings
from src.core.google_auth import (
    GoogleAuthConfigError,
    GoogleServiceUnavailableError,
    GoogleTokenInvalidError,
    verify_google_id_token,
)
from src.core.security import create_access_token, hash_password, verify_password
from src.database.models import (
    GoogleAuthChallenge,
    PasswordResetToken,
    PredictionLog,
    User,
    UserFeedback,
)
from src.database.session import get_db
from src.utils.email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])
_optional_bearer = HTTPBearer(auto_error=False)


# SKEMA REQUEST
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


class GoogleChallengeRequest(BaseModel):
    purpose: Literal["login", "link"]


class GoogleLoginRequest(BaseModel):
    challenge_id: str = Field(..., min_length=1)
    credential: str = Field(..., min_length=1)


class GoogleLinkRequest(BaseModel):
    challenge_id: str = Field(..., min_length=1)
    credential: str = Field(..., min_length=1)
    current_password: str = Field(..., min_length=1)


# HELPER INTERNAL
def _user_payload(user: User, db: Session) -> dict:
    """Helper seragam untuk menyusun data user + kapabilitas di /login, /me, dan /google."""
    try:
        total_detections = (
            db.query(func.count(PredictionLog.id))
            .filter(PredictionLog.user_id == user.id)
            .scalar()
            or 0
        )
    except Exception:
        db.rollback()
        total_detections = 0

    try:
        total_feedbacks = (
            db.query(func.count(UserFeedback.id))
            .filter(UserFeedback.user_id == user.id)
            .scalar()
            or 0
        )
    except Exception:
        db.rollback()
        total_feedbacks = 0

    return {
        "id": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "role": user.role,
        "avatar_url": user.avatar_url or "",
        "is_active": user.is_active,
        "has_password": bool(user.password_hash),
        "google_linked": bool(getattr(user, "google_sub", None)),
        "email_verified_at": (
            user.email_verified_at.isoformat()
            if getattr(user, "email_verified_at", None)
            else None
        ),
        "total_detections": total_detections,
        "total_feedbacks": total_feedbacks,
    }


def _consume_google_challenge(
    db: Session,
    request: Request,
    challenge_id: str,
    purpose: str,
    nonce_from_google: Optional[str],
    expected_user_id=None,
) -> GoogleAuthChallenge:
    """Validasi dan konsumsi tantangan secara atomik (hanya berlaku 1x)."""
    cookie_val = request.cookies.get(settings.GOOGLE_CHALLENGE_COOKIE_NAME)
    if not cookie_val or not nonce_from_google:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bukti sesi tantangan Google tidak lengkap atau telah kedaluwarsa.",
        )

    now = datetime.now(timezone.utc)
    challenge = (
        db.query(GoogleAuthChallenge)
        .filter(GoogleAuthChallenge.id == challenge_id)
        .with_for_update()
        .first()
    )

    if (
        not challenge
        or challenge.purpose != purpose
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tantangan login Google tidak valid atau sudah digunakan.",
        )

    if purpose == "login" and challenge.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tantangan tidak sesuai tujuan.",
        )
    if purpose == "link" and challenge.user_id != expected_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tantangan bukan milik akun ini.",
        )

    cookie_hash = hashlib.sha256(cookie_val.encode()).hexdigest()
    nonce_hash = hashlib.sha256(nonce_from_google.encode()).hexdigest()

    if not hmac.compare_digest(challenge.browser_binding_hash, cookie_hash) or not hmac.compare_digest(
        challenge.nonce_hash, nonce_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verifikasi keamanan tantangan Google gagal.",
        )

    challenge.consumed_at = now
    return challenge


# 1. REGISTRASI
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi minimal 8 karakter.",
        )

    email_clean = req.email.lower().strip()
    existing_user = db.query(User).filter(func.lower(User.email) == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alamat email sudah terdaftar. Silakan masuk atau gunakan email lain.",
        )

    new_user = User(
        full_name=req.name.strip(),
        email=email_clean,
        password_hash=hash_password(req.password),
        role="USER",
        is_active=True,
        token_version=0,
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alamat email sudah terdaftar. Silakan masuk atau gunakan email lain.",
        )

    return {
        "status": "success",
        "message": "Akun berhasil dibuat. Silakan login.",
    }


# =====================================================================
# 2. LOGIN (Memuat token_version ke dalam JWT Claim)
# =====================================================================
@router.post("/login")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email_clean).first()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau kata sandi tidak cocok.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan oleh Administrator.",
        )

    user_version = getattr(user, "token_version", 0) or 0
    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "token_version": user_version,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_payload(user, db),
    }


# =====================================================================
# 3. GET PROFILE /auth/me
# =====================================================================
@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _user_payload(current_user, db)


# =====================================================================
# 4. LUPA PASSWORD (Kirim Tautan Pemulihan via Email)
# =====================================================================
@router.post("/forgot-password")
def forgot_password(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Membuat token reset acak, menyimpan hash SHA-256 ke Supabase,
    dan mengirim tautan pemulihan ke inbox Gmail via background task.
    Respon selalu seragam (anti-enumeration OWASP).
    """
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email_clean).first()

    if user and user.is_active and user.password_hash:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
        ).update({"is_used": True}, synchronize_session=False)

        expire_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )
        reset_entry = PasswordResetToken(
            user_id=user.id,
            token_code=token_hash,
            expires_at=expire_at,
            is_used=False,
        )
        db.add(reset_entry)
        db.commit()

        background_tasks.add_task(send_password_reset_email, user.email, raw_token)

    return {
        "status": "success",
        "message": "Jika email terdaftar di sistem kami, tautan pemulihan kata sandi telah dikirim ke kotak masuk Anda.",
    }


# =====================================================================
# 5. RESET PASSWORD (Validasi Hash Token & Update Password)
# =====================================================================
@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if req.confirm_password is not None and req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konfirmasi kata sandi baru tidak cocok.",
        )

    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru minimal 8 karakter.",
        )

    token_hash = hashlib.sha256(req.token.strip().encode()).hexdigest()
    now = datetime.now(timezone.utc)

    try:
        token_record = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_code == token_hash,
                PasswordResetToken.is_used == False,
                PasswordResetToken.expires_at > now,
            )
            .with_for_update()
            .first()
        )

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tautan reset kata sandi tidak valid atau sudah kedaluwarsa.",
            )

        user = (
            db.query(User)
            .filter(User.id == token_record.user_id)
            .with_for_update()
            .first()
        )
        if not user or not user.is_active or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Akun pengguna tidak ditemukan atau tidak mendukung reset sandi lokal.",
            )

        if verify_password(req.new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kata sandi baru tidak boleh sama dengan kata sandi lama.",
            )

        user.password_hash = hash_password(req.new_password)
        user.token_version = (getattr(user, "token_version", 0) or 0) + 1
        user.updated_at = now

        token_record.is_used = True
        db.commit()

        return {
            "status": "success",
            "message": "Kata sandi berhasil diperbarui. Silakan login menggunakan kata sandi baru Anda.",
        }
    except HTTPException:
        db.rollback()
        raise


# =====================================================================
# 6. GOOGLE CHALLENGE (Terbitkan Nonce + HttpOnly Browser Binding)
# =====================================================================
@router.post("/google/challenge")
def create_google_challenge(
    req: GoogleChallengeRequest,
    response: Response,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    db: Session = Depends(get_db),
):
    target_user_id = None
    if req.purpose == "link":
        if not creds:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autentikasi diperlukan untuk menautkan akun.",
            )
        # Catatan: pastikan parameter di src/core/auth_deps.py bernama `token` (atau sesuaikan)
        current_user = get_current_user(token=creds.credentials, db=db)
        if str(current_user.role).upper() == "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun administrator hanya menggunakan kata sandi lokal.",
            )
        target_user_id = current_user.id

    now = datetime.now(timezone.utc)
    db.query(GoogleAuthChallenge).filter(GoogleAuthChallenge.expires_at < now).delete(
        synchronize_session=False
    )

    raw_nonce = secrets.token_urlsafe(32)
    raw_browser_secret = secrets.token_urlsafe(32)
    expires_at = now + timedelta(minutes=settings.GOOGLE_CHALLENGE_EXPIRE_MINUTES)

    challenge = GoogleAuthChallenge(
        nonce_hash=hashlib.sha256(raw_nonce.encode()).hexdigest(),
        browser_binding_hash=hashlib.sha256(raw_browser_secret.encode()).hexdigest(),
        purpose=req.purpose,
        user_id=target_user_id,
        expires_at=expires_at,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    response.set_cookie(
        key=settings.GOOGLE_CHALLENGE_COOKIE_NAME,
        value=raw_browser_secret,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.GOOGLE_CHALLENGE_EXPIRE_MINUTES * 60,
        path="/api/v1/auth/google",
    )

    return {
        "challenge_id": str(challenge.id),
        "nonce": raw_nonce,
        "expires_at": expires_at.isoformat(),
    }


# =====================================================================
# 7. LOGIN DENGAN GOOGLE
# =====================================================================
@router.post("/google")
def login_with_google(
    req: GoogleLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        identity = verify_google_id_token(req.credential)
    except GoogleAuthConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except GoogleServiceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except GoogleTokenInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        _consume_google_challenge(db, request, req.challenge_id, "login", identity.nonce)

        user = db.query(User).filter(User.google_sub == identity.sub).first()
        if user:
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Akun Anda telah dinonaktifkan oleh Administrator.",
                )
            if str(user.role).upper() == "ADMIN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Akun administrator wajib masuk menggunakan kata sandi.",
                )
        else:
            existing_email_user = (
                db.query(User).filter(func.lower(User.email) == identity.email).first()
            )
            if existing_email_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email ini sudah terdaftar dengan akun kata sandi. Silakan masuk menggunakan kata sandi lalu tautkan akun Google di halaman Profil.",
                )

            now = datetime.now(timezone.utc)
            user = User(
                full_name=identity.full_name,
                email=identity.email,
                password_hash=None,
                google_sub=identity.sub,
                email_verified_at=now if identity.is_google_hosted_email else None,
                avatar_url=identity.avatar_url,
                role="USER",
                is_active=True,
                token_version=0,
            )
            db.add(user)

        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Terjadi konflik pembuatan akun. Silakan coba masuk kembali.",
        )

    response.delete_cookie(
        key=settings.GOOGLE_CHALLENGE_COOKIE_NAME,
        path="/api/v1/auth/google",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "token_version": getattr(user, "token_version", 0) or 0,
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_payload(user, db),
    }


# =====================================================================
# 8. PENAUTAN AKUN GOOGLE KE AKUN LOKAL
# =====================================================================
@router.post("/google/link")
def link_google_account(
    req: GoogleLinkRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if str(current_user.role).upper() == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun administrator tidak mendukung penautan Google.",
        )

    if not current_user.password_hash or not verify_password(
        req.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi saat ini tidak cocok.",
        )

    try:
        identity = verify_google_id_token(req.credential)
    except (GoogleAuthConfigError, GoogleServiceUnavailableError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except GoogleTokenInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        _consume_google_challenge(
            db,
            request,
            req.challenge_id,
            "link",
            identity.nonce,
            expected_user_id=current_user.id,
        )

        user = db.query(User).filter(User.id == current_user.id).with_for_update().first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun tidak aktif.")

        other_user = (
            db.query(User)
            .filter(User.google_sub == identity.sub, User.id != user.id)
            .first()
        )
        if other_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Akun Google ini sudah tertaut ke akun lain.",
            )

        if user.google_sub and user.google_sub != identity.sub:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Akun Anda sudah tertaut ke identitas Google yang berbeda.",
            )

        if user.google_sub != identity.sub:
            now = datetime.now(timezone.utc)
            user.google_sub = identity.sub
            user.token_version = (getattr(user, "token_version", 0) or 0) + 1
            user.updated_at = now
            if (
                not user.email_verified_at
                and identity.is_google_hosted_email
                and user.email.lower() == identity.email
            ):
                user.email_verified_at = now

        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Akun Google ini sudah tertaut ke akun lain.",
        )

    response.delete_cookie(
        key=settings.GOOGLE_CHALLENGE_COOKIE_NAME,
        path="/api/v1/auth/google",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    new_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "token_version": getattr(user, "token_version", 0) or 0,
        }
    )
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "user": _user_payload(user, db),
    }