import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import jwt

# Skema hashing bcrypt standar industri
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Kunci rahasia untuk tanda tangan JWT (bisa dipindah ke file .env)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "VERIDIX_POLITICAL_AI_SECRET_KEY_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7  # Token berlaku selama 7 hari

def hash_password(password: str) -> str:
    """Mengubah kata sandi polos menjadi hash bcrypt aman."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Mencocokkan kata sandi yang diketik user dengan hash di database."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Menerbitkan token JWT untuk autentikasi user/admin."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)