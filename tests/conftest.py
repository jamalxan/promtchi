"""Test muhitini sozlaydi — app.* import qilinishidan OLDIN ishga tushishi shart
(config.py .env o'qishdan oldin os.environ.setdefault chaqiradi)."""
import os
from pathlib import Path

os.environ["ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./_test_promtchi.db"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-0123456789abcdef"
os.environ["ADMIN_EMAIL"] = "test@promtchi.local"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_POLLING"] = "false"
os.environ["LOGIN_MAX_ATTEMPTS"] = "5"
os.environ["LOGIN_LOCKOUT_SECONDS"] = "900"
os.environ["ADMIN_IDLE_TIMEOUT_MINUTES"] = "30"
os.environ["JWT_EXPIRE_HOURS"] = "12"
# Lead rate-limit testlarga xalaqit bermasin (ketma-ket POST /api/leads)
os.environ["LEAD_MIN_INTERVAL_SECONDS"] = "0"
os.environ["LEAD_RATE_LIMIT"] = "1000"
os.environ["LEAD_RATE_WINDOW_SECONDS"] = "600"

import bcrypt  # noqa: E402

TEST_PASSWORD = "TestPass123!"
os.environ["ADMIN_PASSWORD_HASH"] = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_DB_FILE = Path("./_test_promtchi.db")


def _remove_db_files():
    for suffix in ("", "-wal", "-shm"):
        p = Path(f"./_test_promtchi.db{suffix}")
        if p.exists():
            p.unlink()


@pytest.fixture(scope="session", autouse=True)
def _clean_db():
    _remove_db_files()
    yield
    _remove_db_files()


@pytest.fixture(scope="session")
def client(_clean_db):
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def test_password():
    return TEST_PASSWORD


@pytest.fixture()
def admin_client(client, test_password):
    """Asosiy (super admin) hisob bilan login qilingan holatda beradi;
    test tugagach chiqib, cookie tozalanadi (keyingi testga ta'sir qilmasin)."""
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": "test@promtchi.local", "password": test_password})
    assert r.status_code == 200, r.text
    yield client
    client.post("/api/auth/logout")
    client.cookies.clear()


@pytest.fixture(scope="session")
def make_account(client):
    """email/parol/rol bilan yangi (faollashtirilgan) AdminAccount yaratadi —
    email tasdiqlash oqimini aylanib o'tib, to'g'ridan-to'g'ri bazaga yozadi."""
    import asyncio

    from app.auth import hash_password
    from app.db import AdminAccount, SessionLocal

    async def _make(email: str, password: str, role: str = "manager"):
        async with SessionLocal() as s:
            existing = await s.get(AdminAccount, email)
            if existing is not None:
                return email
            s.add(AdminAccount(email=email, password_hash=hash_password(password), is_primary=False, role=role))
            await s.commit()
        return email

    def _sync(email: str, password: str, role: str = "manager"):
        return asyncio.run(_make(email, password, role))

    return _sync


@pytest.fixture()
def login_as(client):
    """(email, password) bilan login qiladi, keyin chiqadi — turli rollarni
    ketma-ket sinash uchun qulay."""
    def _login(email: str, password: str):
        client.cookies.clear()
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return client

    yield _login
    client.post("/api/auth/logout")
    client.cookies.clear()
