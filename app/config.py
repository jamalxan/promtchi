"""promtchi backend — sozlamalar (.env orqali boshqariladi)."""
import os
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# .env faylini oddiy o'qish (python-dotenv'siz ham ishlaydi)
_env = BASE_DIR / ".env"
if _env.exists():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# Default (xavfli) qiymatlar — ishlab chiqarishda ishlatilsa ishga tushmaymiz
DEFAULT_JWT_SECRET = "o'zgartiring-maxfiy-kalit"
DEFAULT_ADMIN_PASSWORD = "promtchi2026"


class Settings:
    # production / development
    ENV: str = os.getenv("ENV", "development").strip().lower()

    # Ma'lumotlar bazasi: default SQLite; Postgres uchun (1000+ konkurent uchun tavsiya):
    #   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/promtchi
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'promtchi.db'}"
    )

    # Ulanishlar puli — 1000+ bir vaqtdagi so'rov uchun asosiy parametr
    DB_POOL_SIZE: int = _int("DB_POOL_SIZE", 20)
    DB_MAX_OVERFLOW: int = _int("DB_MAX_OVERFLOW", 80)
    DB_POOL_TIMEOUT: int = _int("DB_POOL_TIMEOUT", 15)
    DB_POOL_RECYCLE: int = _int("DB_POOL_RECYCLE", 1800)
    # SQLite yozuv qulfi uchun kutish vaqti (ms)
    SQLITE_BUSY_TIMEOUT_MS: int = _int("SQLITE_BUSY_TIMEOUT_MS", 15000)

    # Admin paneli paroli — ADMIN_PASSWORD_HASH bo'lsa u ustunlik qiladi (bcrypt hash,
    # `python -m app.config hash "parol"` bilan yaratiladi). ADMIN_PASSWORD faqat eski
    # (hash qilinmagan) sozlash uchun qoldirilgan — production'da tavsiya etilmaydi.
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    ADMIN_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "")

    # JWT — admin sessiyasi
    JWT_SECRET: str = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    JWT_ALG: str = "HS256"
    # Mutlaq muddat — login qilingan paytdan boshlab (iat'dan), yangilanmaydi.
    JWT_EXPIRE_HOURS: int = _int("JWT_EXPIRE_HOURS", 12)
    # Harakatsizlik muddati — har so'rovda "siljiydi" (sliding window). Ikkalasi
    # ham HttpOnly session cookie orqali ishlaydi (Max-Age YO'Q — brauzer butunlay
    # yopilganda cookie o'zi o'chadi; refresh/yangi tab/back-forward'da o'chmaydi).
    ADMIN_IDLE_TIMEOUT_MINUTES: int = _int("ADMIN_IDLE_TIMEOUT_MINUTES", 30)

    # Login brute-force himoyasi
    LOGIN_MAX_ATTEMPTS: int = _int("LOGIN_MAX_ATTEMPTS", 5)
    LOGIN_LOCKOUT_SECONDS: int = _int("LOGIN_LOCKOUT_SECONDS", 900)

    # Telegram xabarnoma (ixtiyoriy)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Bazada saqlanadigan maxfiy qiymatlarni (masalan CRM Telegram bot tokeni)
    # shifrlash uchun Fernet kaliti. `python -m app.config genkey` bilan yaratiladi.
    # Bo'sh qoldirilsa — JWT_SECRET'dan barqaror kalit hosil qilinadi (faqat dev
    # uchun qulaylik; production'da ALBATTA o'z ENCRYPTION_KEY'ingizni qo'ying —
    # aks holda JWT_SECRET almashsa shifrlangan tokenlar ham o'qib bo'lmay qoladi).
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    # Xabarnoma navbati — burst paytida serverni bo'g'ib qo'ymasligi uchun
    TELEGRAM_QUEUE_SIZE: int = _int("TELEGRAM_QUEUE_SIZE", 5000)
    TELEGRAM_WORKERS: int = _int("TELEGRAM_WORKERS", 2)
    # Bot buyruqlari/tugmalarini tinglash (long polling). Bir necha uvicorn
    # worker ishlatilsa FAQAT bittasida yoqilgan bo'lsin — Telegram bir vaqtda
    # bitta getUpdates'ga ruxsat beradi (aks holda 409 Conflict).
    TELEGRAM_POLLING: bool = _bool("TELEGRAM_POLLING", True)

    # CORS (vergul bilan ajratilgan originlar yoki *)
    CORS_ORIGINS: list = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
    ]

    # Google Analytics 4 (GA4) o'lchov ID'si (masalan G-XXXXXXXXXX). Bo'sh bo'lsa
    # gtag/analytics.js hech qaysi sahifaga qo'shilmaydi — hodisalar kuzatilmaydi.
    GA_MEASUREMENT_ID: str = os.getenv("GA_MEASUREMENT_ID", "").strip()
    # Google Search Console tasdiqlash tokeni (meta tag usuli). Bo'sh bo'lsa
    # meta umuman chiqmaydi — token TAXMIN QILINMAYDI, uni GSC beradi.
    SEARCH_CONSOLE_VERIFICATION: str = os.getenv("SEARCH_CONSOLE_VERIFICATION", "").strip()

    # Saytning haqiqiy domeni (canonical/OG teglarda ishlatiladi). Shu domendan
    # boshqa Host bilan (masalan to'g'ridan-to'g'ri IP orqali) kirilsa, bosh
    # sahifa <meta name="robots" content="noindex"> bilan qaytariladi.
    CANONICAL_HOST: str = os.getenv("CANONICAL_HOST", "promtchi.uz")

    # ── Admin email + parol tiklash ─────────────────────────────────────────
    # Bu email'ga parol tiklash/tasdiqlash havolalari yuboriladi. Admin panel
    # orqali o'zgartirilsa, Setting jadvalidagi qiymat ustunlik qiladi.
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    SITE_URL: str = os.getenv("SITE_URL", "").strip() or f"https://{os.getenv('CANONICAL_HOST', 'promtchi.uz')}"

    # ── SMTP (Gmail va h.k.) ─────────────────────────────────────────────────
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = _int("SMTP_PORT", 587)
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "") or os.getenv("SMTP_USER", "")

    # ── Rate-limit ───────────────────────────────────────────────────────────
    # Bitta IP N daqiqada nechta ariza topshira oladi (burst'ga ruxsat beriladi,
    # shuning uchun bitta ofis/uyali tarmoqdagi bir necha odam bloklanmaydi).
    LEAD_RATE_LIMIT: int = _int("LEAD_RATE_LIMIT", 5)
    LEAD_RATE_WINDOW_SECONDS: int = _int("LEAD_RATE_WINDOW_SECONDS", 600)
    # Eski nom bilan moslik: agar faqat LEAD_COOLDOWN_SECONDS berilgan bo'lsa,
    # uni minimal interval sifatida ishlatamiz (0 = o'chirilgan).
    LEAD_MIN_INTERVAL_SECONDS: int = _int("LEAD_MIN_INTERVAL_SECONDS", 3)
    # Umumiy API rate-limit (IP bo'yicha, DDoS'ga qarshi birinchi qalqon)
    API_RATE_LIMIT: int = _int("API_RATE_LIMIT", 600)
    API_RATE_WINDOW_SECONDS: int = _int("API_RATE_WINDOW_SECONDS", 60)
    RATE_LIMIT_MAX_KEYS: int = _int("RATE_LIMIT_MAX_KEYS", 50_000)

    # ── Proxy ────────────────────────────────────────────────────────────────
    # Nginx/Caddy/Cloudflare ortida ishlaganda ALBATTA yoqing — aks holda
    # barcha foydalanuvchilar bitta IP (proxy) sifatida ko'rinadi va rate-limit
    # butun saytni bloklaydi.
    TRUST_PROXY: bool = _bool("TRUST_PROXY", False)
    # X-Forwarded-For zanjirining o'ngdan nechinchi elementi haqiqiy mijoz
    PROXY_HOPS: int = _int("PROXY_HOPS", 1)

    # ── Xavfsizlik ───────────────────────────────────────────────────────────
    ENABLE_DOCS: bool = _bool("ENABLE_DOCS", ENV != "production")
    MAX_BODY_BYTES: int = _int("MAX_BODY_BYTES", 256 * 1024)
    # Fayl yuklash (rasm/video) — alohida, kattaroq limit
    MAX_UPLOAD_BYTES: int = _int("MAX_UPLOAD_BYTES", 30 * 1024 * 1024)
    HSTS_SECONDS: int = _int("HSTS_SECONDS", 31536000)

    # ── Biznes manzili (TZ 22/23: LocalBusiness faqat TASDIQLANGAN ma'lumot
    # bilan) ────────────────────────────────────────────────────────────────
    # Ko'cha manzili VA ish vaqti berilgan bo'lsagina Organization tuguni
    # `ProfessionalService` (LocalBusiness turi) sifatida ham e'lon qilinadi.
    # Bo'sh bo'lsa hech narsa o'ylab topilmaydi — schema o'zgarishsiz qoladi.
    BUSINESS_STREET_ADDRESS: str = os.getenv("BUSINESS_STREET_ADDRESS", "").strip()
    BUSINESS_POSTAL_CODE: str = os.getenv("BUSINESS_POSTAL_CODE", "").strip()
    # schema.org formati, masalan: "Mo-Fr 09:00-18:00"
    BUSINESS_OPENING_HOURS: str = os.getenv("BUSINESS_OPENING_HOURS", "").strip()
    # "41.311081,69.240562" (ixtiyoriy)
    BUSINESS_GEO: str = os.getenv("BUSINESS_GEO", "").strip()
    BUSINESS_PRICE_RANGE: str = os.getenv("BUSINESS_PRICE_RANGE", "").strip()

    # ── Zaxira (TZ 20-bo'lim) ───────────────────────────────────────────────
    # SQLite bazasi `VACUUM INTO` orqali davriy zaxiralanadi (app/backup.py).
    # Postgres'da bu o'chirilgan bo'lishi kerak — u yerda zaxira server
    # darajasida (pg_dump / managed snapshot) olinadi.
    BACKUP_ENABLED: bool = _bool("BACKUP_ENABLED", True)
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "").strip() or str(BASE_DIR / "backups")
    BACKUP_INTERVAL_HOURS: int = _int("BACKUP_INTERVAL_HOURS", 24)
    BACKUP_KEEP: int = _int("BACKUP_KEEP", 7)

    # ── Kesh ─────────────────────────────────────────────────────────────────
    STATIC_CACHE_SECONDS: int = _int("STATIC_CACHE_SECONDS", 3600)

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    def advisories(self) -> list[str]:
        """Tavsiyalar — chop etiladi, lekin ishga tushirishni TO'XTATMAYDI.

        Bu yerda xavfsizlik teshigi emas, masshtab/konfiguratsiya maslahati
        turadi. Ilgari SQLite haqidagi maslahat ham `problems()` ichida edi va
        production'da ishga tushirishni bloklardi — natijada SQLite ishlatgan
        server `ENV=production` ni umuman yoqa olmas, HSTS, `Secure` cookie va
        `/docs` yopilishi kabi HIMOYALAR ham ishlamay qolar edi. Maslahat
        himoyani o'chirib qo'ymasligi kerak.
        """
        a: list[str] = []
        if self.is_production and self.is_sqlite:
            a.append(
                "Production'da SQLite ishlatilmoqda — 1000+ bir vaqtdagi yozuv uchun "
                "PostgreSQL tavsiya etiladi (DATABASE_URL=postgresql+asyncpg://...)."
            )
        if not self.is_production and self.CANONICAL_HOST not in ("localhost", "127.0.0.1"):
            a.append(
                f"ENV={self.ENV}, lekin CANONICAL_HOST={self.CANONICAL_HOST} — haqiqiy "
                "domenda production rejimisiz ishlayapsiz: /docs ochiq, HSTS yo'q, "
                "admin cookie Secure emas. Server env'ida ENV=production qo'ying."
            )
        return a

    def problems(self) -> list[str]:
        """Xavfsizlik muammolari ro'yxati (production'da ishga tushishni to'xtatadi)."""
        p: list[str] = []
        if self.JWT_SECRET == DEFAULT_JWT_SECRET:
            p.append(
                "JWT_SECRET default qiymatda — istalgan odam admin tokeni yasay oladi. "
                "Yangilang:  python -c \"import secrets;print(secrets.token_hex(32))\""
            )
        elif len(self.JWT_SECRET) < 32:
            p.append("JWT_SECRET juda qisqa (32+ belgi bo'lsin).")
        if not self.ADMIN_PASSWORD_HASH:
            if self.ADMIN_PASSWORD == DEFAULT_ADMIN_PASSWORD:
                p.append(
                    "ADMIN_PASSWORD_HASH sozlanmagan va ADMIN_PASSWORD default qiymatda — "
                    "o'zgartiring:  python -m app.config hash \"yangi-parol\""
                )
            elif len(self.ADMIN_PASSWORD) < 12:
                p.append("ADMIN_PASSWORD 12 belgidan qisqa — brute-force'ga zaif.")
            if self.is_production:
                p.append(
                    "ADMIN_PASSWORD hash qilinmagan holda ishlatilmoqda — production'da "
                    "ADMIN_PASSWORD_HASH ishlating:  python -m app.config hash \"parolingiz\""
                )
        if self.is_production and "*" in self.CORS_ORIGINS:
            p.append("CORS_ORIGINS='*' — production'da aniq domen yozing.")
        if self.is_production and not self.ENCRYPTION_KEY:
            p.append(
                "ENCRYPTION_KEY sozlanmagan — CRM Telegram bot tokeni JWT_SECRET'dan "
                "hosil qilingan vaqtinchalik kalit bilan shifrlanadi. Yarating: "
                "python -m app.config genkey"
            )
        return p

    def validate(self) -> None:
        for note in self.advisories():
            print(f"  [eslatma] {note}", file=sys.stderr)
        probs = self.problems()
        if not probs:
            return
        head = "XAVFSIZLIK OGOHLANTIRISHI" if not self.is_production else "XAVFSIZLIK XATOSI"
        msg = f"\n{'=' * 66}\n  {head}\n{'=' * 66}\n" + "".join(
            f"  • {x}\n" for x in probs
        ) + "=" * 66
        print(msg, file=sys.stderr)
        if self.is_production:
            raise SystemExit(
                "Production'da ishga tushirish to'xtatildi. Yuqoridagi muammolarni tuzating "
                "yoki ENV=development qo'ying."
            )


settings = Settings()


def generate_secret() -> str:
    return secrets.token_hex(32)


def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


if __name__ == "__main__":
    # python -m app.config hash "yangi-parol"  -> .env ga qo'yiladigan ADMIN_PASSWORD_HASH
    # python -m app.config genkey                -> .env ga qo'yiladigan ENCRYPTION_KEY
    if len(sys.argv) == 3 and sys.argv[1] == "hash":
        print(f"ADMIN_PASSWORD_HASH={hash_password(sys.argv[2])}")
    elif len(sys.argv) == 2 and sys.argv[1] == "genkey":
        from cryptography.fernet import Fernet

        print(f"ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    else:
        print('Foydalanish: python -m app.config hash "parolingiz"  |  python -m app.config genkey')
