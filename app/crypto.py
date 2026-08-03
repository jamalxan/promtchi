"""Bazada saqlanadigan maxfiy qiymatlarni (CRM Telegram bot tokeni) shifrlash.

Fernet (AES128-CBC + HMAC-SHA256) ishlatiladi — simmetrik, ochiq matn +
imzo, muddati tugashi ixtiyoriy (biz ishlatmaymiz, token amal qilish
muddatiga ega emas).

ENCRYPTION_KEY .env'da bo'lmasa, JWT_SECRET'dan barqaror 32-baytli kalit
hosil qilinadi — dev qulayligi uchun, lekin production'da bu holat
config.problems() orqali ogohlantiriladi (JWT_SECRET almashsa, oldingi
shifrlangan qiymatlar o'qib bo'lmay qoladi).
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


def _fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.strip()
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.JWT_SECRET.encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt(plain: str) -> str:
    """Bo'sh satrni bo'sh qaytaradi (shifrlanmagan "yo'q" holatini bildiradi)."""
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    """Noto'g'ri/kalit almashgan tokenlarda xato ko'tarmasdan bo'sh qaytaradi."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return ""
