import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

# Sesuaikan dengan letak file models dan session database Anda
from src.database.models import User
from src.database.session import get_db
from src.core.security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Memvalidasi token JWT dan mengambil data pengguna yang sedang aktif."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesi login kedaluwarsa atau tidak valid. Silakan login kembali.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Decode dan validasi tanda tangan + masa berlaku token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 2. Pastikan ID pengguna berupa UUID yang valid
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        raise credentials_exception

    # 3. Ambil pengguna aktif dari database
    user = db.query(User).filter(
        User.id == user_uuid,
        User.is_active == True,
    ).first()

    if user is None:
        raise credentials_exception

    # 4. Cabut token lama: versi di JWT harus sama dengan versi di database.
    #    type(...) is not int menolak boolean (True == 1) dan pecahan (1.0 == 1).
    payload_version = payload.get("token_version")
    if (
        type(payload_version) is not int
        or payload_version < 0
        or payload_version != user.token_version
    ):
        raise credentials_exception

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Memastikan hanya akun dengan role ADMIN yang bisa mengakses endpoint."""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Fitur ini hanya dapat diakses oleh Administrator.",
        )
    return current_user