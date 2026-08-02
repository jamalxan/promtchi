"""JWT autentifikatsiya — ko'p admin (har birining o'z emaili va paroli).

Ko'pi bilan MAX_ADMIN_ACCOUNTS ta admin hisobi (AdminAccount jadvali). Aynan bittasi
is_primary=True — yangi email qo'shish/o'chirishni FAQAT shu hisob
tasdiqlay oladi. JWT'ning "sub" maydonida haqiqiy login qilingan email
saqlanadi (xabarnoma va "o'z emailimga havola yubor" kabi funksiyalar
uchun kerak).
"""
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import AdminAccount, AdminToken, Setting, get_session

bearer = HTTPBearer(auto_error=False)

RESET_TTL_MINUTES = 30
MAX_ADMIN_ACCOUNTS = 10


def create_token(email: str) -> str:
    payload = {
        "sub": email.lower(),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


# ══════════ HISOBLAR ══════════

async def list_admin_accounts(session: AsyncSession) -> list[AdminAccount]:
    res = await session.execute(select(AdminAccount).order_by(AdminAccount.is_primary.desc(), AdminAccount.created_at))
    return list(res.scalars().all())


async def get_account(session: AsyncSession, email: str) -> AdminAccount | None:
    return await session.get(AdminAccount, email.strip().lower())


async def get_primary_account(session: AsyncSession) -> AdminAccount | None:
    return await session.scalar(select(AdminAccount).where(AdminAccount.is_primary.is_(True)))


async def seed_admin_account(session: AsyncSession) -> None:
    """Birinchi ishga tushirishda — eski (bitta hisobli) Setting qiymatlaridan
    yoki .env'dan bitta ASOSIY hisob yaratadi. AdminAccount jadvali bo'sh
    bo'lgandagina ishlaydi (jim o'tadi, agar allaqachon hisoblar bo'lsa)."""
    count = await session.scalar(select(func.count()).select_from(AdminAccount))
    if count:
        return
    email = (await session.scalar(select(Setting.value).where(Setting.key == "admin_email"))) or settings.ADMIN_EMAIL
    pw_hash = (
        await session.scalar(select(Setting.value).where(Setting.key == "admin_password_hash"))
    ) or settings.ADMIN_PASSWORD_HASH
    email = (email or "").strip().lower()
    if not email:
        return
    session.add(AdminAccount(email=email, password_hash=pw_hash or "", is_primary=True))
    await session.commit()


async def check_login(session: AsyncSession, email: str, password: str) -> AdminAccount | None:
    """To'g'ri bo'lsa hisobni qaytaradi, aks holda None."""
    acc = await get_account(session, email)
    if acc is None or not acc.password_hash:
        return None
    if not _checkpw(password, acc.password_hash):
        return None
    return acc


def _checkpw(password: str, pw_hash: str) -> bool:
    import bcrypt

    try:
        return bcrypt.checkpw(password.encode(), pw_hash.encode())
    except ValueError:
        return False  # noto'g'ri formatdagi hash


def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def set_account_password(session: AsyncSession, email: str, new_password: str) -> bool:
    acc = await get_account(session, email)
    if acc is None:
        return False
    acc.password_hash = hash_password(new_password)
    await session.commit()
    return True


async def add_admin_account(session: AsyncSession, email: str) -> AdminAccount | None:
    email = email.strip().lower()
    count = await session.scalar(select(func.count()).select_from(AdminAccount))
    if count and count >= MAX_ADMIN_ACCOUNTS:
        return None
    existing = await get_account(session, email)
    if existing is not None:
        return existing
    acc = AdminAccount(email=email, password_hash="", is_primary=False)
    session.add(acc)
    await session.commit()
    return acc


async def add_admin_account_with_password(
    session: AsyncSession, email: str, password_hash: str
) -> AdminAccount | None:
    """add_admin_account bilan bir xil, lekin hisob DARHOL faollashtirilgan holda
    yaratiladi (parol allaqachon o'rnatilgan — taklif qilinayotganda kiritilgan)."""
    email = email.strip().lower()
    count = await session.scalar(select(func.count()).select_from(AdminAccount))
    if count and count >= MAX_ADMIN_ACCOUNTS:
        return None
    existing = await get_account(session, email)
    if existing is not None:
        return existing
    acc = AdminAccount(email=email, password_hash=password_hash, is_primary=False)
    session.add(acc)
    await session.commit()
    return acc


async def remove_admin_account(session: AsyncSession, email: str) -> bool:
    acc = await get_account(session, email)
    if acc is None or acc.is_primary:
        return False  # asosiy hisobni bu yo'l bilan o'chirib bo'lmaydi
    await session.delete(acc)
    await session.commit()
    return True


async def set_primary_account(session: AsyncSession, email: str) -> bool:
    """Super admin huquqini boshqa (faollashtirilgan) hisobga o'tkazadi.

    Eskisi oddiy adminga aylanadi, yangisi super admin bo'ladi. Faollashtirilmagan
    (paroli hali o'rnatilmagan) hisobga o'tkazib bo'lmaydi.
    """
    new_primary = await get_account(session, email)
    if new_primary is None or not new_primary.password_hash:
        return False
    if new_primary.is_primary:
        return True
    old_primary = await get_primary_account(session)
    if old_primary is not None:
        old_primary.is_primary = False
    new_primary.is_primary = True
    await session.commit()
    return True


# ══════════ TOKEN (parol tiklash / email qo'shish-o'chirish) ══════════

async def create_admin_token(session: AsyncSession, purpose: str, payload: str = "") -> str:
    token = secrets.token_urlsafe(32)
    row = AdminToken(
        token=token,
        purpose=purpose,
        payload=payload,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_TTL_MINUTES),
    )
    session.add(row)
    await session.commit()
    return token


async def consume_admin_token(
    session: AsyncSession, token: str, purpose: str
) -> AdminToken | None:
    """Tokenni bir martalik ishlatadi — topilmasa/eskirgan/ishlatilgan bo'lsa None."""
    row = await session.get(AdminToken, token)
    if row is None or row.purpose != purpose or row.used_at is not None:
        return None
    # SQLite tzinfo'ni saqlamaydi (naive qaytaradi) — biz doim UTC yozganimiz
    # uchun shu deb qabul qilamiz; Postgres'da allaqachon aware bo'ladi.
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    row.used_at = datetime.now(timezone.utc)
    await session.commit()
    return row


async def recent_token_exists(session: AsyncSession, purpose: str, seconds: int = 60) -> bool:
    """Spam oldini olish — bir daqiqa ichida shu maqsadda token yaratilganmi."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    row = await session.scalar(
        select(AdminToken.token)
        .where(AdminToken.purpose == purpose, AdminToken.created_at > cutoff)
        .limit(1)
    )
    return row is not None


async def require_admin(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    """Qaytaradi: hozir login qilingan admin email (JWT "sub")."""
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


async def require_primary_admin(
    email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> str:
    """require_admin bilan bir xil, lekin FAQAT super admin o'tishiga ruxsat beradi
    (Telegram sozlamalari kabi butun jamoaga ta'sir qiladigan amallar uchun)."""
    acc = await get_account(session, email)
    if acc is None or not acc.is_primary:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Faqat super admin bu amalni bajara oladi")
    return email
