import sys
import os

# Tambahkan root directory ke path agar module terbaca
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import SessionLocal, engine
from src.database.models import Base, User
from src.core.security import hash_password

def setup_super_admin():
    print("--> Memastikan tabel database terpasang...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Cek apakah sudah ada admin
        admin_email = "admin@veridix.id"
        existing_admin = db.query(User).filter(User.role == "ADMIN").first()

        if existing_admin:
            print(f"ℹ️ Admin utama sudah ada: {existing_admin.email} (Role: {existing_admin.role})")
            return

        # Buat 1 akun admin resmi
        admin = User(
            email=admin_email,
            password_hash=hash_password("AdminVeridix2026!"), # Ganti sandi sesuai keinginan Anda
            full_name="Super Administrator",
            role="ADMIN",
            is_active=True
        )
        db.add(admin)
        db.commit()
        print(f"✅ Akun Super Admin berhasil dibuat!")
        print(f"   Email    : {admin_email}")
        print(f"   Password : AdminVeridix2026!")
    finally:
        db.close()

if __name__ == "__main__":
    setup_super_admin()