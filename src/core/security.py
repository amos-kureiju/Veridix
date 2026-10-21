import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import jwt

# Kunci rahasia untuk tanda tangan JWT (bisa dipindah ke file .env)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "VERIDIX_POLITICAL_AI_SECRET_KEY_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7  # Token berlaku selama 7 hari

def hash_password(password: str) -> str:
    """Mengubah kata sandi polos menjadi hash bcrypt aman."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Mencocokkan kata sandi yang diketik user dengan hash di database."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Menerbitkan token JWT untuk autentikasi user/admin."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
