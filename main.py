import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as DatabaseTimeoutError,
)

from src.core.config import settings
from src.database.session import engine, SessionLocal
from src.database.models import Base, User, AdminSetting
from src.core.security import hash_password
from src.ml.inference import predictor

# Import modul rute (termasuk user_routes)
from src.api.routes import detection_routes, auth_routes, feedback_routes, admin_routes, user_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIDIX-API")


def seed_default_accounts():
    """Memastikan akun Admin dan User demo selalu tersedia saat inisialisasi awal."""
    db = SessionLocal()
    try:
        admin_email = "admin.veridix@gmail.com"
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

        user_email = "amoskurniawan@gmail.com"
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


def sync_initial_threshold():
    """Sinkronisasi threshold dari database ke in-memory predictor saat startup."""
    db = SessionLocal()
    try:
        setting = db.query(AdminSetting).filter(AdminSetting.setting_key == "classification_threshold").first()
        if setting:
            val = float(setting.setting_value)
            if hasattr(predictor, "set_threshold"):
                predictor.set_threshold(val)
            elif hasattr(predictor, "threshold"):
                predictor.threshold = val
            logger.info(f"Threshold AI berhasil dimuat dari DB: {val}")
    except Exception as e:
        logger.warning(f"Gagal memuat threshold awal: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Memeriksa skema database...")
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
    
    if settings.AUTO_SEED_DEMO:
        seed_default_accounts()
        
    sync_initial_threshold()
    yield
    logger.info("Mematikan server API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def database_error_response(request: Request, exc: SQLAlchemyError):
    # Handler khusus dijalankan di dalam CORS. Jangan log SQL/parameter:
    # parameter dapat berisi naskah pengguna, hash sandi, atau token reset.
    logger.error(
        "Database gagal: method=%s path=%s error=%s sqlstate=%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        getattr(getattr(exc, "orig", None), "sqlstate", None),
    )
    unavailable = isinstance(exc, (OperationalError, DatabaseTimeoutError, DisconnectionError))
    return JSONResponse(
        status_code=503 if unavailable else 500,
        content={
            "detail": (
                "Layanan database sementara tidak tersedia. Silakan coba lagi."
                if unavailable
                else "Terjadi kesalahan pada penyimpanan data. Silakan hubungi pengelola sistem."
            )
        },
        headers={"Retry-After": "5"} if unavailable else None,
    )


# Pendaftaran Seluruh Router
app.include_router(auth_routes.router, prefix=settings.API_V1_STR)
app.include_router(user_routes.router, prefix=settings.API_V1_STR)
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
