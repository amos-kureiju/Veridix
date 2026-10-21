import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.database.session import engine, SessionLocal
from src.database.models import Base, User
from src.core.security import get_password_hash

# Import semua modul rute
from src.api.routes import detection_routes, auth_routes, feedback_routes, admin_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIDIX-API")


def seed_default_accounts():
    """Memastikan akun Admin dan User demo selalu tersedia di database Supabase."""
    db = SessionLocal()
    try:
        # 1. Pastikan Akun Admin Demo Ada
        admin = db.query(User).filter(User.email == "admin@veridix.id").first()
        if not admin:
            admin = User(
                email="admin@veridix.id",
                password_hash=get_password_hash("admin123"),
                full_name="Administrator Veridix",
                role="ADMIN",
                is_active=True,
            )
            db.add(admin)
            logger.info("Akun demo ADMIN berhasil di-seed: admin@veridix.id")

        # 2. Pastikan Akun User Demo Ada
        user = db.query(User).filter(User.email == "amos@veridix.id").first()
        if not user:
            user = User(
                email="amos@veridix.id",
                password_hash=get_password_hash("password123"),
                full_name="Amos Kurniawan",
                role="USER",
                is_active=True,
            )
            db.add(user)
            logger.info("Akun demo USER berhasil di-seed: amos@veridix.id")

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Gagal melakukan database seeding: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Inisialisasi tabel (jika belum ada) dan jalankan seeder
    logger.info("Menginisialisasi skema database...")
    Base.metadata.create_all(bind=engine)
    seed_default_accounts()
    yield
    # Shutdown logic (jika diperlukan)
    logger.info("Mematikan server API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",  # Swagger UI interaktif
    lifespan=lifespan,
)

# Set CORS agar Next.js di localhost:3000 bisa memanggil API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan Seluruh Router
app.include_router(auth_routes.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(detection_routes.router, prefix=settings.API_V1_STR, tags=["Detection"])
app.include_router(feedback_routes.router, prefix=f"{settings.API_V1_STR}/feedback", tags=["Feedbacks"])
app.include_router(admin_routes.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin Operations"])


@app.get("/")
def root_check():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)