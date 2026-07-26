"""Async SQLAlchemy: engine, session, modellar.

Konkurentlik uchun muhim:
  • SQLite  — WAL rejimi + busy_timeout, aks holda 1000 bir vaqtdagi yozuvda
              "database is locked" xatosi chiqadi.
  • Pool    — default 5+10 ulanish 1000 konkurent so'rovda tugab qoladi
              (QueuePool TimeoutError). Sozlamalar config.py da.
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, event, func
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
    """Aloqa formasi arizalari."""

    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(120), default="")
    project_type: Mapped[str] = mapped_column(String(60), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
