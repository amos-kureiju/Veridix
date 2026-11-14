import os
from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "HOAXLENS-AI Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hoax_inspect.db")
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    AUTO_CREATE_TABLES: bool = False
    AUTO_SEED_DEMO: bool = False
    
    # Setting Deteksi
    DEFAULT_HOAX_THRESHOLD: float = 0.60
    MODEL_NAME_OR_PATH: str = "indobenchmark/indobert-base-p1"
    SAVED_MODEL_PATH: str = "saved_models/indobert_focal_loss/best_model.pt"
    
    # CORS (Frontend Next.js di port 3000)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # --- Pengaturan SMTP Email (Reset Password) ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: Optional[SecretStr] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "VERIDIX Security"

    # --- Domain Frontend & Masa Berlaku Token ---
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15

    # --- Pengaturan Google Identity Services (OAuth ID Token) ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CHALLENGE_EXPIRE_MINUTES: int = 5
    GOOGLE_CERT_TIMEOUT_SECONDS: float = 5.0
    GOOGLE_CHALLENGE_COOKIE_NAME: str = "veridix_google_challenge"
    COOKIE_SECURE: bool = False  # Set True di .env produksi (HTTPS)
    COOKIE_SAMESITE: str = "lax" 

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()