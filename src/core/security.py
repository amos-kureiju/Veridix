import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, Dict
from jose import jwt
from src.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY.get_secret_value()


def _truncate_password_bytes(password: str) -> bytes:
    """Bcrypt memiliki batas maksimal 72 byte. Potong secara aman pada batas karakter UTF-8."""
    encoded = password.encode("utf-8")
    if len(encoded) <= 72:
        return encoded
    truncated = encoded[:72]
    while True:
        try:
            truncated.decode("utf-8")
            return truncated
        except UnicodeDecodeError:
            truncated = truncated[:-1]


def hash_password(password: str) -> str:
    """Meng-hash kata sandi dengan bcrypt (aman terhadap input > 72 byte)."""
    pw_bytes = _truncate_password_bytes(password)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Memverifikasi kecocokan kata sandi."""
    pw_bytes = _truncate_password_bytes(plain_password)
    try:
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Membuat JWT token yang memuat sub (user_id), role, dan token_version."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)