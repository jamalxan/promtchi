"""promtchi backend — sozlamalar (.env orqali boshqariladi)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# .env faylini oddiy o'qish (python-dotenv'siz ham ishlaydi)
_env = BASE_DIR / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


class Settings:
    # Ma'lumotlar bazasi: default SQLite; Postgres uchun:
    #   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/promtchi
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'promtchi.db'}"
    )

    # Admin paneli paroli (frontenddagi ⚙ panel shu parol bilan kiradi)
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "promtchi2026")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "o'zgartiring-maxfiy-kalit")
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "12"))

    # Telegram xabarnoma (ixtiyoriy): yangi lead kelganda guruh/kanalga yuboriladi
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # CORS (vergul bilan ajratilgan originlar yoki *)
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # Lead rate-limit: bitta IP dan N soniyada 1 ta ariza
    LEAD_COOLDOWN_SECONDS: int = int(os.getenv("LEAD_COOLDOWN_SECONDS", "30"))


settings = Settings()
