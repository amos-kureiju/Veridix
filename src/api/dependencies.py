"""
src/api/dependencies.py — Dependency injection untuk autentikasi dan otorisasi API.
Mengintegrasikan validator sesi pengguna (get_current_user) dan hak akses administrator (get_current_admin).
"""
from fastapi import Depends
from src.database.models import User
from src.core.auth_deps import get_current_user, require_admin

# Alias get_current_admin agar selaras dengan kebutuhan rute & standar FastAPI
get_current_admin = require_admin

__all__ = ["get_current_user", "get_current_admin", "require_admin"]
