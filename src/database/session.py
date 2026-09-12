from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.core.config import settings

# Jika menggunakan Supabase Pooler
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Mengecek koneksi masih aktif sebelum kirim query
    pool_size=10,             # Batas jumlah koneksi
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()