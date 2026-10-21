import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.database.session import engine, SessionLocal
from src.database.models import Base, User
from src.core.security import hash_password

# Import modul rute
from src.api.routes import detection_routes, auth_routes, feedback_routes, admin_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIDIX-API")


def seed_default_accounts():
    """Memastikan akun Admin dan User demo selalu tersedia saat inisialisasi awal."""
    db = SessionLocal()
    try:
        # 1. Pastikan Akun Admin Demo Ada (Gmail)
        admin_email = "admin.veridix@gmail.com"  # Sesuaikan jika perlu
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                password_hash=hash_password("admin123"),
                full_name="Administrator Veridix",
                role="ADMIN",
                is_active=True,
            )
            db.add(admin)
            logger.info(f"Akun demo ADMIN berhasil di-seed: {admin_email}")

        # 2. Pastikan Akun User Demo Ada (Gmail)
        user_email = "amoskurniawan@gmail.com"  # Sesuaikan jika perlu
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(
                email=user_email,
                password_hash=hash_password("password123"),
                full_name="Amos Kurniawan",
                role="USER",
                is_active=True,
            )
            db.add(user)
            logger.info(f"Akun demo USER berhasil di-seed: {user_email}")

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Gagal melakukan database seeding: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Memeriksa dan menginisialisasi skema database...")
    Base.metadata.create_all(bind=engine)
    
    if getattr(settings, "AUTO_SEED_DEMO", True):
        seed_default_accounts()
        
    yield
    logger.info("Mematikan server API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

# Konfigurasi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pendaftaran Router (Tanpa Prefix Ganda)
app.include_router(auth_routes.router, prefix=settings.API_V1_STR)
app.include_router(detection_routes.router, prefix=settings.API_V1_STR)
app.include_router(feedback_routes.router, prefix=settings.API_V1_STR)
app.include_router(admin_routes.router, prefix=settings.API_V1_STR)


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