"""Async SQLAlchemy: engine, session, modellar.

Konkurentlik uchun muhim:
  • SQLite  — WAL rejimi + busy_timeout, aks holda 1000 bir vaqtdagi yozuvda
              "database is locked" xatosi chiqadi.
  • Pool    — default 5+10 ulanish 1000 konkurent so'rovda tugab qoladi
              (QueuePool TimeoutError). Sozlamalar config.py da.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Index, Integer, String, Text, event, func, text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import settings

_kwargs: dict = {"echo": False, "pool_pre_ping": True}

if settings.is_sqlite:
    # SQLite'da yozuv baribir ketma-ket bo'ladi; pul asosan o'qish uchun.
    _kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        connect_args={"timeout": settings.SQLITE_BUSY_TIMEOUT_MS / 1000},
    )
else:
    _kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

engine = create_async_engine(settings.DATABASE_URL, **_kwargs)

if settings.is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _rec):
        """Har bir ulanishda WAL + busy_timeout — konkurent yozuv uchun shart."""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute(f"PRAGMA busy_timeout={settings.SQLITE_BUSY_TIMEOUT_MS}")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA cache_size=-16000")  # ~16 MB sahifa keshi
        cur.close()


SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Content(Base):
    """Sayt kontenti — bitta JSON hujjat (packages/team/testimonials/cases).

    Frontenddagi DATA tuzilmasi bilan birebir mos; admin panel butun
    hujjatni PUT qiladi — versiya har saqlashda +1 bo'ladi.
    """

    __tablename__ = "content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Lead(Base):
    """Aloqa formasi arizalari.

    status  — admin belgilaydi: "new" (yangi) / "replied" (javob berilgan)
    tg_sent — Telegram guruhiga xabarnoma muvaffaqiyatli yuborildimi
    """

    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(120), default="")
    project_type: Mapped[str] = mapped_column(String(60), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    tg_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "project_type": self.project_type,
            "message": self.message,
            "status": self.status or "new",
            "tg_sent": bool(self.tg_sent),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Post(Base):
    """Blog/yangilik postlari — landing'da alohida bo'limda chiqadi."""

    __tablename__ = "posts"
    __table_args__ = (Index("ix_posts_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str] = mapped_column(String(1000), default="")
    video: Mapped[str] = mapped_column(String(1000), default="")
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "image": self.image,
            "video": self.video,
            "published": bool(self.published),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Review(Base):
    """Mijoz fikri — FOYDALANUVCHI yozadi, admin tahrirlay OLMAYDI.

    Admin faqat moderatsiya qiladi: tasdiqlash (approved) yoki o'chirish.
    Matnni o'zgartirish imkoni ataylab yo'q — fikr mijozning o'z so'zi.
    Yozish uchun mijozga berilgan bir martalik kod (ReviewCode) talab qilinadi,
    shuning uchun faqat haqiqiy mijozlar fikr qoldira oladi.
    """

    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(120), default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    code: Mapped[str] = mapped_column(String(32), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def as_dict(self, admin: bool = False) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "text": self.text,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if admin:
            d["approved"] = bool(self.approved)
            d["code"] = self.code
        return d


class ReviewCode(Base):
    """Fikr yozish uchun bir martalik kod — admin mijozga beradi."""

    __tablename__ = "review_codes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    client: Mapped[str] = mapped_column(String(160), default="")
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "client": self.client,
            "used": self.used_at is not None,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Setting(Base):
    """Kalit-qiymat sozlamalar (masalan Telegram bot token/chat ID).

    .env dagi qiymatlar default bo'lib xizmat qiladi; admin panel orqali
    o'zgartirilganlari shu jadvalda saqlanadi va ustunlik qiladi.
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AdminToken(Base):
    """Parolni tiklash / email qo'shish-o'chirishni tasdiqlash uchun bir martalik token.

    purpose — "reset_password" | "add_email" | "remove_email".
    payload — reset_password uchun tegishli admin email (qaysi hisobning paroli
              tiklanayotgani); add_email/remove_email uchun tasdiqlanishi
              kutilayotgan email manzil.
    """

    __tablename__ = "admin_tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[str] = mapped_column(String(200), default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AdminAccount(Base):
    """Admin panelga kira oladigan hisob — har birining o'z paroli bor.

    Ko'pi bilan 3 ta hisob (ilova darajasida cheklanadi). Aynan bittasi
    is_primary=True — yangi email qo'shish/o'chirishni FAQAT shu hisob
    tasdiqlay oladi (tasdiqlash havolasi doim uning emailiga yuboriladi).
    password_hash bo'sh bo'lsa — hisob hali faollashtirilmagan (yangi
    qo'shilgan, egasi hali "parolni tiklash" orqali o'z parolini
    o'rnatmagan); bunday holda kirish rad etiladi.
    """

    __tablename__ = "admin_accounts"

    email: Mapped[str] = mapped_column(String(200), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(200), default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def as_dict(self) -> dict:
        return {
            "email": self.email,
            "is_primary": bool(self.is_primary),
            "activated": bool(self.password_hash),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Eski bazalarga yangi ustunlarni qo'shish (create_all mavjud jadvalni o'zgartirmaydi)
_MIGRATIONS = [
    "ALTER TABLE leads ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'new'",
    "ALTER TABLE leads ADD COLUMN tg_sent BOOLEAN NOT NULL DEFAULT 0",
    "ALTER TABLE posts ADD COLUMN video VARCHAR(1000) DEFAULT ''",
]


async def run_migrations(eng) -> None:
    """Yo'q ustunlarni qo'shadi; allaqachon mavjud bo'lsa jim o'tadi.

    Har bir stmt alohida tranzaksiyada — Postgres'da xato tranzaksiyani
    bekor qilsa ham keyingilariga ta'sir qilmaydi.
    """
    for stmt in _MIGRATIONS:
        try:
            async with eng.begin() as conn:
                await conn.execute(text(stmt))
        except Exception:
            pass  # ustun allaqachon bor


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
