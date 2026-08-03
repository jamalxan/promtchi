"""Admin panel parol gate — refresh muammosi tuzatilgani va sessiya
semantikasi to'g'riligini tekshiradi (asosiy talab manbai: gate refresh
prompti)."""
from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from app.config import settings
from app.security import login_limiter


def test_correct_login_sets_session_cookie_without_maxage(client, test_password):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": "test@promtchi.local", "password": test_password})
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "")
    assert "admin_session=" in set_cookie
    assert "max-age" not in set_cookie.lower()
    assert "expires" not in set_cookie.lower()
    assert "httponly" in set_cookie.lower()
    client.post("/api/auth/logout")
    client.cookies.clear()


def test_refresh_does_not_reprompt(admin_client):
    """F5/hard-reload/yangi tab — bir xil cookie bilan ketma-ket GET, hammasi 200."""
    for _ in range(3):
        r = admin_client.get("/api/admin/account")
        assert r.status_code == 200


def test_cache_control_no_store_on_admin_api(admin_client):
    r = admin_client.get("/api/admin/account")
    assert "no-store" in r.headers.get("cache-control", "")


def test_logout_reopens_gate(admin_client):
    r = admin_client.post("/api/auth/logout")
    assert r.status_code == 200
    r = admin_client.get("/api/admin/account")
    assert r.status_code == 401
    # keyingi testlar uchun qayta login qilib qo'yamiz (fixture logout'ni yana chaqiradi, zarari yo'q)
    admin_client.post("/api/auth/login", json={"email": "test@promtchi.local", "password": "TestPass123!"})


def test_no_cookie_unauthorized(client):
    client.cookies.clear()
    r = client.get("/api/admin/account")
    assert r.status_code == 401


def test_absolute_timeout_token_rejected(client):
    old_iat = datetime.now(timezone.utc) - timedelta(hours=13)
    payload = {"sub": "test@promtchi.local", "iat": old_iat, "exp": old_iat + timedelta(minutes=30)}
    token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    client.cookies.clear()
    client.cookies.set("admin_session", token)
    r = client.get("/api/admin/account")
    assert r.status_code == 401
    client.cookies.clear()


def test_idle_timeout_token_rejected(client):
    recent_iat = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {"sub": "test@promtchi.local", "iat": recent_iat, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}
    token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    client.cookies.clear()
    client.cookies.set("admin_session", token)
    r = client.get("/api/admin/account")
    assert r.status_code == 401
    client.cookies.clear()


def test_login_lockout_after_max_attempts(client):
    login_limiter._b.clear()
    client.cookies.clear()
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": "test@promtchi.local", "password": "wrong"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"email": "test@promtchi.local", "password": "wrong"})
    assert r.status_code == 429
    login_limiter._b.clear()  # keyingi testlarga ta'sir qilmasin
