import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Ambil DATABASE_URL dari .env (default ke PostgreSQL lokal jika env tidak terbaca)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@127.0.0.1:5432/veridix_db"
)

# Konfigurasi engine dengan pool pre-ping agar tidak drop koneksi
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency FastAPI untuk Session DB per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()