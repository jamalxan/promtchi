"""JWT autentifikatsiya — bitta admin, parol .env dan."""
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

bearer = HTTPBearer(auto_error=False)


def create_token() -> str:
    payload = {
        "sub": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def check_password(password: str) -> bool:
    # timing-safe taqqoslash
    return hmac.compare_digest(password.encode(), settings.ADMIN_PASSWORD.encode())


async def require_admin(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token yo'q")
    try:
        payload = jwt.decode(
            cred.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALG]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token muddati tugagan")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token noto'g'ri")
    return payload["sub"]
