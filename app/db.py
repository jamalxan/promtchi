"""Async SQLAlchemy: engine, session, modellar.

Konkurentlik uchun muhim:
  • SQLite  — WAL rejimi + busy_timeout, aks holda 1000 bir vaqtdagi yozuvda
              "database is locked" xatosi chiqadi.
  • Pool    — default 5+10 ulanish 1000 konkurent so'rovda tugab qoladi
              (QueuePool TimeoutError). Sozlamalar config.py da.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric,
    String, Text, event, func, select, text, update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from . import crm_constants as crm
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
    """Aloqa formasi arizalari — CRM Kanban voronkasining asosiy jadvali.

    stage — 8 bosqichli voronka (app/crm_constants.py STAGE_SLUGS), Kanban
    ustunlari va Telegram inline tugmalari shu tartibga qat'iy amal qiladi.

    Eski `status` ("new"/"replied") va `tg_sent` ustunlari CRM Kanban bilan
    to'liq ALMASHTIRILDI (endi hech qayerda o'qilmaydi/yozilmaydi) — lekin
    ustunlarning o'zi bazadan REMOVE qilinmadi: ishlab turgan production
    bazasida DROP COLUMN xavfli va keraksiz (SQLite eski versiyalarida
    umuman ishlamasligi mumkin), shuning uchun ular shunchaki "orphan"
    holida qoladi. Bir martalik ma'lumot ko'chirish (`status='replied'`
    bo'lgan eski arizalarni `stage='in_work'`ga o'tkazish) `run_data_fixups()`
    da bajariladi.

    `contact`/`full_name` kabi promptdagi nomlar ATAYLAB ishlatilmadi —
    mavjud `name`/`phone` ustunlari (va ularga tayangan barcha eski kod:
    LeadIn, admin.html, telegram.py) o'zgarishsiz qoladi, faqat YANGI
    maydonlar (`contact_normalized`, `contact_type`) qo'shildi.
    """

    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_stage_position", "stage", "position"),
        Index("ix_leads_contact_normalized", "contact_normalized"),
        Index("ix_leads_assigned_to", "assigned_to"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(120), default="")
    contact_normalized: Mapped[str] = mapped_column(String(80), default="")
    contact_type: Mapped[str] = mapped_column(String(16), default="other")
    project_type: Mapped[str] = mapped_column(String(60), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")

    # Eski (endi ishlatilmaydigan) maydonlar — pastdagi izohga qarang.
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    tg_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    stage: Mapped[str] = mapped_column(String(20), default=crm.DEFAULT_STAGE, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(
        String(200), ForeignKey("admin_accounts.email", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(20), default=crm.DEFAULT_SOURCE, nullable=False)
    budget: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tg_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tg_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tg_sync_state: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    tg_last_error: Mapped[str] = mapped_column(Text, default="")

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    stage_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "contact_normalized": self.contact_normalized,
            "contact_type": self.contact_type,
            "project_type": self.project_type,
            "message": self.message,
            # status/tg_sent — CRM stage-tizimi bilan ALMASHTIRILDI (endi
            # yozilmaydi), lekin hozircha as_dict()da qoladi: eski Arizalar
            # sahifasi (static/admin.html) va Telegramning eski 2-holatli
            # tugmasi CRM Backend API/Kanban UI bosqichlarida almashtirilmaguncha
            # shu maydonlarga tayanadi — ular olib tashlanguncha sinmasin.
            "status": self.status or "new",
            "tg_sent": bool(self.tg_sent),
            "stage": self.stage or crm.DEFAULT_STAGE,
            "position": self.position,
            "assigned_to": self.assigned_to,
            "source": self.source or crm.DEFAULT_SOURCE,
            "budget": float(self.budget) if self.budget is not None else None,
            "next_action_at": self.next_action_at.isoformat() if self.next_action_at else None,
            "tg_message_id": self.tg_message_id,
            "tg_chat_id": self.tg_chat_id,
            "tg_sync_state": self.tg_sync_state,
            "tg_last_error": self.tg_last_error,
            "is_archived": bool(self.is_archived),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "stage_changed_at": self.stage_changed_at.isoformat() if self.stage_changed_at else None,
        }


class LeadStageHistory(Base):
    """Har bir bosqich o'tishi — Kanban'dagi "Tarix" timeline'i shu yerdan o'qiladi.

    changed_by=None — tizim (masalan avtomatik `new`ga qo'yilishi); aks holda
    o'zgartirgan admin emaili.
    """

    __tablename__ = "lead_stage_history"
    __table_args__ = (Index("ix_lsh_lead_id", "lead_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(20), default="")
    to_stage: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(
        String(200), ForeignKey("admin_accounts.email", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "duration_seconds": self.duration_seconds,
        }


class LeadNote(Base):
    """Menejer qo'ng'iroqdan keyin yozadigan qisqa izoh."""

    __tablename__ = "lead_notes"
    __table_args__ = (Index("ix_lead_notes_lead_id", "lead_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    author: Mapped[str] = mapped_column(String(200), ForeignKey("admin_accounts.email", ondelete="SET NULL"), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "author": self.author,
            "text": self.text,
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

    purpose — "reset_password" | "add_email" | "remove_email" | "set_primary".
    payload — reset_password/remove_email/set_primary uchun tegishli admin email
              (oddiy matn); add_email uchun JSON: {"email","password","password_hash"}
              (yangi hisob ASOSIY admin tasdiqlagan zahoti tayyor parol bilan
              yaratilishi uchun — parol matni faqat Telegram admin(lar)ga
              xabar yuborish uchun vaqtincha saqlanadi, token bir martalik).
    """

    __tablename__ = "admin_tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AdminAccount(Base):
    """Admin panelga kira oladigan hisob — har birining o'z paroli bor.

    Ko'pi bilan auth.MAX_ADMIN_ACCOUNTS ta hisob (ilova darajasida cheklanadi). Aynan bittasi
    is_primary=True — yangi email qo'shish/o'chirishni FAQAT shu hisob
    tasdiqlay oladi (tasdiqlash havolasi doim uning emailiga yuboriladi).
    password_hash bo'sh bo'lsa — hisob hali faollashtirilmagan (yangi
    qo'shilgan, egasi hali "parolni tiklash" orqali o'z parolini
    o'rnatmagan); bunday holda kirish rad etiladi.

    role — CRM ruxsatlar matritsasi uchun ("superadmin" | "admin" | "manager",
    app/crm_constants.py ADMIN_ROLES). is_primary=True bo'lgan hisob HAR DOIM
    role="superadmin" (ikkalasi sinxron saqlanadi — is_primary sайт-darajasidagi
    eski "Super Admin" ruxsatlarini, role esa CRM ruxsatlar matritsasini
    boshqaradi; ular bir xil odam uchun bir xil ma'noni bildiradi).
    """

    __tablename__ = "admin_accounts"

    email: Mapped[str] = mapped_column(String(200), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(200), default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=crm.DEFAULT_ADMIN_ROLE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def as_dict(self) -> dict:
        return {
            "email": self.email,
            "is_primary": bool(self.is_primary),
            "role": "superadmin" if self.is_primary else self.role,
            "activated": bool(self.password_hash),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TelegramSettings(Base):
    """CRM Kanban'ning Telegram integratsiyasi sozlamalari — bitta qator (id=1).

    Bu — mavjud (app/telegram.py, umumiy `settings` jadvalidagi tg_bot_token/
    tg_chat_id) ariza-botining SOZLAMALARI shu jadvalga ko'chiriladi (bitta
    bot, bitta token — ikkinchi mustaqil bot ISHGA TUSHIRILMAYDI: bir xil
    tokenda ikkita getUpdates pollerini parallel ishlatish Telegram
    tomonidan 409 Conflict bilan taqiqlangan). `run_data_fixups()` eski
    qiymatlarni shifrlab shu yerga bir martalik ko'chiradi.

    bot_token_enc — app/crypto.py (Fernet) bilan shifrlangan holda saqlanadi;
    hech qachon ochiq matnda qaytarilmaydi (faqat maskalangan holda UI ga).
    """

    __tablename__ = "crm_telegram_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    bot_token_enc: Mapped[str] = mapped_column(Text, default="")
    leads_chat_id: Mapped[str] = mapped_column(String(64), default="")
    topic_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notify_chat_id: Mapped[str] = mapped_column(String(64), default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    send_on_create: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    edit_on_update: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_status: Mapped[str] = mapped_column(Text, default="")


# Eski bazalarga yangi ustunlarni qo'shish (create_all mavjud jadvalni o'zgartirmaydi)
_MIGRATIONS = [
    "ALTER TABLE leads ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'new'",
    "ALTER TABLE leads ADD COLUMN tg_sent BOOLEAN NOT NULL DEFAULT 0",
    "ALTER TABLE posts ADD COLUMN video VARCHAR(1000) DEFAULT ''",
    # ── CRM Kanban (Lead) ────────────────────────────────────────────────────
    "ALTER TABLE leads ADD COLUMN contact_normalized VARCHAR(80) DEFAULT ''",
    "ALTER TABLE leads ADD COLUMN contact_type VARCHAR(16) DEFAULT 'other'",
    "ALTER TABLE leads ADD COLUMN stage VARCHAR(20) NOT NULL DEFAULT 'new'",
    "ALTER TABLE leads ADD COLUMN position INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE leads ADD COLUMN assigned_to VARCHAR(200)",
    "ALTER TABLE leads ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'website'",
    "ALTER TABLE leads ADD COLUMN budget NUMERIC(12, 2)",
    "ALTER TABLE leads ADD COLUMN next_action_at DATETIME",
    "ALTER TABLE leads ADD COLUMN tg_message_id BIGINT",
    "ALTER TABLE leads ADD COLUMN tg_chat_id VARCHAR(64)",
    "ALTER TABLE leads ADD COLUMN tg_sync_state VARCHAR(16) NOT NULL DEFAULT 'pending'",
    "ALTER TABLE leads ADD COLUMN tg_last_error TEXT DEFAULT ''",
    "ALTER TABLE leads ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0",
    # NOT NULL + CURRENT_TIMESTAMP birga ADD COLUMN'da SQLite tomonidan taqiqlangan
    # ("Cannot add a NOT NULL column with default value NULL/CURRENT_TIMESTAMP") —
    # shu sabab bu ikkitasi bu yerda nullable qo'shiladi, keyin
    # run_data_fixups() ularni created_at bilan to'ldiradi.
    "ALTER TABLE leads ADD COLUMN updated_at DATETIME",
    "ALTER TABLE leads ADD COLUMN stage_changed_at DATETIME",
    # ── CRM rollar (AdminAccount) ────────────────────────────────────────────
    "ALTER TABLE admin_accounts ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'manager'",
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


async def run_data_fixups(session: AsyncSession) -> None:
    """Sxema o'zgarishidan keyingi BIR MARTALIK ma'lumot ko'chirishlar.

    Idempotent — har startup'da xavfsiz qayta ishga tushadi (WHERE shartlari
    ikkinchi marta hech narsani topmaydi):
      1. Eski `status='replied'` arizalar -> `stage='in_work'` (5-savolga
         "to'liq almashtirish" javobi: eski 2-holatli tizimdan CRM
         voronkasiga bir martalik ko'chirish).
      2. `is_primary=True` hisob HAR DOIM `role='superadmin'` bo'lishi kerak
         (ikkalasi sinxron — AdminAccount docstring'iga qarang).
      3. Eski umumiy `settings` jadvalidagi tg_bot_token/tg_chat_id ->
         yangi `crm_telegram_settings` (shifrlab) — FAQAT birinchi marta,
         `crm_telegram_settings` jadvali hali bo'sh bo'lsagina.
    """
    from . import crypto  # shu yerda import — db.py crypto.py'ni har doim kerak qilmaydi

    # updated_at/stage_changed_at ALTER orqali NULL holida qo'shilgan edi
    # (SQLite NOT NULL+CURRENT_TIMESTAMP'ni ADD COLUMN'da taqiqlaydi) —
    # created_at bilan to'ldiramiz (eng mantiqiy tarixiy qiymat).
    await session.execute(
        update(Lead).where(Lead.updated_at.is_(None)).values(updated_at=Lead.created_at)
    )
    await session.execute(
        update(Lead).where(Lead.stage_changed_at.is_(None)).values(stage_changed_at=Lead.created_at)
    )
    await session.execute(
        update(Lead).where(Lead.status == "replied", Lead.stage == "new").values(stage="in_work")
    )
    await session.execute(
        update(AdminAccount).where(AdminAccount.is_primary.is_(True), AdminAccount.role != "superadmin")
        .values(role="superadmin")
    )

    existing = await session.scalar(select(TelegramSettings).where(TelegramSettings.id == 1))
    if existing is None:
        res = await session.execute(
            select(Setting.key, Setting.value).where(Setting.key.in_(["tg_bot_token", "tg_chat_id"]))
        )
        stored = dict(res.all())
        old_token = (stored.get("tg_bot_token") or "").strip()
        old_chat = (stored.get("tg_chat_id") or "").strip()
        session.add(TelegramSettings(
            id=1,
            bot_token_enc=crypto.encrypt(old_token),
            leads_chat_id=old_chat,
            is_enabled=bool(old_token),
        ))

    await session.commit()


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
