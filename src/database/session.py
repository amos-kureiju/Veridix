import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Ambil DATABASE_URL dari .env (default ke SQLite lokal jika env tidak terdefinisi)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./hoax_inspect.db"
)

# Konfigurasi engine (support SQLite & PostgreSQL)
is_sqlite = DATABASE_URL.startswith("sqlite")
engine_kwargs = {"pool_pre_ping": True}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency FastAPI untuk Session DB per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
