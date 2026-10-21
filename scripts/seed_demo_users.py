from datetime import datetime
from src.database.session import SessionLocal, engine
from src.database.models import Base, User
from src.core.security import hash_password

def init_db_and_seed():
    print("--> [DB Init] Membuat struktur tabel di PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Cek apakah akun demo sudah ada
        admin = db.query(User).filter(User.email == "admin@veridix.id").first()
        if not admin:
            admin_user = User(
                email="admin@veridix.id",
                password_hash=hash_password("admin123"),
                full_name="Administrator VERIDIX",
                role="ADMIN",
                is_active=True
            )
            db.add(admin_user)
            print("✅ Akun Admin berhasil dibuat (admin@veridix.id / admin123)")

        user = db.query(User).filter(User.email == "amos@veridix.id").first()
        if not user:
            regular_user = User(
                email="amos@veridix.id",
                password_hash=hash_password("password123"),
                full_name="Amos Manurung",
                role="USER",
                is_active=True
            )
            db.add(regular_user)
            print("✅ Akun User berhasil dibuat (amos@veridix.id / password123)")

        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    init_db_and_seed()