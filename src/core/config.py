import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "HOAXLENS-AI Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database URL (Default SQLite jika .env kosong, atau Supabase Postgres)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hoax_inspect.db")
    
    # Setting Deteksi
    DEFAULT_HOAX_THRESHOLD: float = 0.60
    MODEL_NAME_OR_PATH: str = "indobenchmark/indobert-base-p1"
    SAVED_MODEL_PATH: str = "saved_models/indobert_focal_loss/best_model.pt"
    
    # CORS (Frontend Next.js di port 3000)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()