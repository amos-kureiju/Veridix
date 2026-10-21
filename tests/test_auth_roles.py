"""Tes login dan pembatasan role; seluruh akun dan data berada di SQLite memori."""

import os
import unittest
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

with patch.dict(os.environ, {
    "DATABASE_URL": "sqlite://",
    "JWT_SECRET_KEY": "local-role-test-secret-at-least-32-characters",
}):
    from src.api.routes import admin_routes, auth_routes, user_routes
    from src.core.security import create_access_token, hash_password
    from src.database.models import Base, User
    from src.database.session import get_db


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, _compiler, **_kwargs):
    return "JSON"


class TestLoginRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "LoginTest123!"
        cls.password_hash = hash_password(cls.password)

    def setUp(self):
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.ids = {role: uuid4() for role in ("ADMIN", "USER")}
        with self.session_factory() as db:
            for role, user_id in self.ids.items():
                db.add(User(
                    id=user_id, email=role.lower() + "@example.com", full_name=role,
                    password_hash=self.password_hash, role=role, is_active=True,
                ))
            db.commit()

        def memory_db():
            with self.session_factory() as db:
                yield db

        app = FastAPI()
        for router in (auth_routes.router, user_routes.router, admin_routes.router):
            app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = memory_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def login(self, role):
        response = self.client.post("/api/v1/auth/login", json={
            "email": role.lower() + "@example.com", "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], role)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_admin_login_and_own_profile(self):
        response = self.client.get("/api/v1/auth/me", headers=self.login("ADMIN"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.ids["ADMIN"]))
        self.assertEqual(response.json()["role"], "ADMIN")

    def test_user_login_and_own_profile(self):
        headers = self.login("USER")
        response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.ids["USER"]))
        self.assertEqual(response.json()["role"], "USER")
        profile = self.client.get("/api/v1/users/profile", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["data"]["id"], str(self.ids["USER"]))

    def test_admin_can_access_admin_dashboard(self):
        response = self.client.get("/api/v1/admin/stats", headers=self.login("ADMIN"))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_access_admin_dashboard(self):
        response = self.client.get("/api/v1/admin/stats", headers=self.login("USER"))
        self.assertEqual(response.status_code, 403)

    def test_guest_cannot_access_profile_or_admin(self):
        for path in ("/api/v1/auth/me", "/api/v1/users/profile", "/api/v1/admin/stats"):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_wrong_password_cannot_login(self):
        for role in ("ADMIN", "USER"):
            response = self.client.post("/api/v1/auth/login", json={
                "email": role.lower() + "@example.com", "password": "wrong-password",
            })
            self.assertEqual(response.status_code, 401)

    def test_inactive_account_cannot_login_or_reuse_token(self):
        headers = self.login("USER")
        with self.session_factory() as db:
            db.get(User, self.ids["USER"]).is_active = False
            db.commit()
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).status_code, 401)
        response = self.client.post("/api/v1/auth/login", json={
            "email": "user@example.com", "password": self.password,
        })
        self.assertEqual(response.status_code, 403)

    def test_admin_claim_does_not_override_user_role_in_database(self):
        token = create_access_token({"sub": str(self.ids["USER"]), "role": "ADMIN"})
        response = self.client.get("/api/v1/admin/stats", headers={"Authorization": "Bearer " + token})
        self.assertEqual(response.status_code, 403)

    def test_expired_token_is_rejected(self):
        token = create_access_token({"sub": str(self.ids["USER"])}, timedelta(seconds=-1))
        response = self.client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
