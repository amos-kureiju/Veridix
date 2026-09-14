from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.database.session import engine, Base
from src.api.routes import detection_routes

# Buat tabel database secara otomatis jika belum ada
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" # Swagger UI interaktif
)

# Set CORS agar Next.js di localhost:3000 bisa memanggil API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan Route
app.include_router(detection_routes.router, prefix=settings.API_V1_STR)

@app.get("/")
def root_check():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)