"""promtchi® backend — FastAPI.

Endpointlar:
  GET  /api/health              — holat
  GET  /api/content             — sayt kontenti (public, keshlangan + ETag)
  GET  /api/posts               — e'lon qilingan postlar (public, keshlangan)
  POST /api/auth/login          — {email,password} -> HttpOnly session cookie + {token}
                                   (Telegram xabarnoma). Sessiya: refresh/yangi tab/orqaga-
                                   oldinga tugmasi qayta so'ramaydi (cookie tirik); 30 daq
                                   harakatsizlik, 12 soat mutlaq muddat yoki logout — so'raydi.
  POST /api/auth/logout         — sessiya cookie'sini tozalaydi (Bearer)
  POST /api/auth/forgot-password       — {email} -> tiklash havolasi emailga yuboriladi
  POST /api/auth/reset-password        — {token,new_password,confirm_password}
  POST /api/auth/confirm-token         — {token} -> email qo'shish/o'chirishni yakunlaydi
  GET  /api/admin/account                        — joriy email; super admin uchun barcha
                                                     hisoblar, oddiy admin uchun faqat o'zi (Bearer)
  POST /api/admin/account/request-password-reset — o'z emailiga havola (Bearer)
  POST /api/admin/account/emails/request-add      — {new_email,password,confirm_password},
                                                     FAQAT super admin, tasdiq o'ziga, tasdiqlangach
                                                     hisob DARHOL shu parol bilan faollashadi (Bearer)
  POST /api/admin/account/emails/request-remove   — {email}, FAQAT super admin, tasdiq o'ziga (Bearer)
  POST /api/admin/account/emails/request-set-primary — {email}, FAQAT super admin, tasdiq o'ziga (Bearer)
  POST /api/admin/account/emails/{email}/resend-activation — eski (parolsiz) hisobga
                                                     qayta faollashtirish havolasi, faqat super admin (Bearer)
  PUT  /api/admin/content       — to'liq kontentni saqlash (Bearer)
  POST /api/admin/content/reset — boshlang'ich kontentga qaytarish (Bearer)
  POST /api/leads               — aloqa formasi arizasi (public, rate-limit)
  GET  /api/admin/leads         — arizalar ro'yxati (Bearer, ?limit=&offset=)
  PATCH /api/admin/leads/{id}   — ariza holati: new/replied (Bearer)
  DELETE /api/admin/leads/{id}  — arizani o'chirish (Bearer)
  GET/POST/PUT/DELETE /api/admin/posts[/{id}] — postlar CRUD (Bearer)
  GET/PUT /api/admin/telegram   — bot holati/boshqaruvi — BUTUNLAY faqat super admin (Bearer)
  POST /api/admin/telegram/test — test xabar yuborish (faqat super admin)
  GET/POST/DELETE /api/admin/telegram/admins[/{chat_id}] — Telegram admin(lar) ro'yxati
                                                     — BUTUNLAY faqat super admin (Bearer)
  POST /api/auth/tg-super/confirm-old — {token} -> Telegram /super oqimidagi eski super
                                                     admin tasdig'ini yakunlaydi (public, token-gated)
  GET  /                        — sayt (static/index.html)
Hujjatlar: /docs (faqat ENABLE_DOCS=true bo'lganda)
"""
import asyncio
import gzip
import hashlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import httpx
from fastapi import (
    Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import (
    MAX_ADMIN_ACCOUNTS, add_admin_account, add_admin_account_with_password,
    check_login, clear_admin_cookie, consume_admin_token, create_admin_token,
    create_token, get_account, get_primary_account, hash_password,
    list_admin_accounts, recent_token_exists, remove_admin_account,
    require_admin, require_primary_admin, seed_admin_account,
    set_account_password, set_admin_cookie, set_primary_account,
)
from .config import settings
from .db import (
    Base, Content, Lead, Post, Review, ReviewCode, SessionLocal, Setting,
    engine, get_session, run_data_fixups, run_migrations,
)
from .email import (
    account_ready_email, confirm_email_email, new_account_email,
    reset_password_email, send_email, set_primary_email,
)
from .schemas import (
    DEFAULT_CONTENT, AddEmailRequestIn, ConfirmTokenIn, ContentDoc,
    ForgotPasswordIn, LeadIn, LeadStatusIn, LoginIn, PostIn,
    RemoveEmailRequestIn, ResetPasswordIn, ReviewCodeIn, ReviewIn,
    SetPrimaryRequestIn, TelegramAdminIn, TelegramSettingsIn,
)
from . import crm_api, crm_service, crypto
from .telegram import bot
from .security import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    check_lead_limits,
    check_pwreset_limit,
    check_review_limits,
    login_limiter,
)

log = logging.getLogger("promtchi")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# ══════════ KONTENT KESHI ══════════
# /api/content eng ko'p chaqiriladigan endpoint. Har so'rovda DB'ga borish
# 10k+ request'da pulni tugatadi — shuning uchun xotirada saqlaymiz va
# faqat admin o'zgartirganda yangilaymiz.
class _ContentCache:
    __slots__ = ("body", "etag", "version")

    def __init__(self):
        self.body: bytes = b""
        self.etag: str = ""
        self.version: int = 0

    def set(self, data, version: int) -> None:
        self.body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        self.etag = '"%s"' % hashlib.sha256(self.body).hexdigest()[:32]
        self.version = version

    def clear(self) -> None:
        self.body = b""

    @property
    def ready(self) -> bool:
        return bool(self.body)


content_cache = _ContentCache()
# Postlar va fikrlar keshi — CRUD'da clear() qilinadi, keyingi GET'da DB'dan
# qayta yuklanadi. Public o'qishlar shu tufayli DB'ga umuman tegmaydi.
posts_cache = _ContentCache()
reviews_cache = _ContentCache()


# ══════════ SAHIFA KESHI ══════════
# index.html eng ko'p so'raladigan resurs. Har so'rovda diskdan o'qish +
# GZip middleware'ning har safar qayta siqishi 10k+ RPS'da CPU'ni yeydi.
# Bir marta o'qib, bir marta siqib xotirada saqlaymiz; fayl o'zgarsa
# (mtime bo'yicha) avtomatik yangilanadi.
#
# canonical/OG teglar doim haqiqiy domenga (CANONICAL_HOST) ishora qiladi —
# lekin sayt IP orqali yoki boshqa host bilan ochilsa, qidiruv tizimlari
# uni domendan alohida sahifa deb indekslamasligi uchun <meta robots noindex>
# qo'shilgan ikkinchi variant ham oldindan tayyorlab qo'yiladi (har so'rovda
# HTML qayta ishlanmasin — faqat Host header bo'yicha tayyor bayt tanlanadi).
class _PageCache:
    __slots__ = (
        "path", "mtime", "raw", "gz", "etag",
        "raw_noindex", "gz_noindex", "etag_noindex",
    )

    def __init__(self, path: Path):
        self.path = path
        self.mtime: int = -1
        self.raw: bytes = b""
        self.gz: bytes = b""
        self.etag: str = ""
        self.raw_noindex: bytes = b""
        self.gz_noindex: bytes = b""
        self.etag_noindex: str = ""

    def load(self) -> bool:
        """Fayl mavjud bo'lsa keshni yangilaydi (o'zgargan bo'lsa) va True qaytaradi."""
        try:
            st = self.path.stat()
        except OSError:
            return False
        if st.st_mtime_ns != self.mtime:
            data = self.path.read_bytes()
            self.raw = data
            self.gz = gzip.compress(data, compresslevel=8)
            self.etag = '"%s"' % hashlib.sha256(data).hexdigest()[:32]

            noindex = data.replace(
                b"</head>",
                b'<meta name="robots" content="noindex,nofollow">\n</head>',
                1,
            )
            self.raw_noindex = noindex
            self.gz_noindex = gzip.compress(noindex, compresslevel=8)
            self.etag_noindex = '"%s"' % hashlib.sha256(noindex).hexdigest()[:32]

            self.mtime = st.st_mtime_ns
        return True


index_cache = _PageCache(STATIC_DIR / "index.html")

# ══════════ TELEGRAM ══════════
# Bot mantiqi app/telegram.py da. Sozlamalar DB'da (settings jadvali) saqlanadi
# va admin paneldan boshqariladi; .env qiymatlari boshlang'ich default.
# Bot guruhga qo'shilganda yoki /start bosilganda chatni o'zi ro'yxatga oladi.
http_client: httpx.AsyncClient | None = None
_bg_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client

    settings.validate()

    # Jadval yaratish + eski bazaga yangi ustunlar + kontentni urug'lash
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await run_migrations(engine)

    async with SessionLocal() as s:
        await seed_admin_account(s)
    async with SessionLocal() as s:
        await run_data_fixups(s)

    async with engine.begin() as conn:
        res = await conn.execute(select(Content.data, Content.version).where(Content.id == 1))
        row = res.first()
        if row is None:
            await conn.execute(
                Content.__table__.insert().values(id=1, data=DEFAULT_CONTENT, version=1)
            )
            content_cache.set(DEFAULT_CONTENT, 1)
        else:
            content_cache.set(row[0], row[1])

    index_cache.load()  # birinchi so'rov gzip narxini to'lamasin

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )

    # ── Telegram bot (BITTA — umumiy bildirishnoma va CRM birga ishlatadi) ──
    bot.token = settings.TELEGRAM_BOT_TOKEN.strip()
    bot.group_chat_id = settings.TELEGRAM_CHAT_ID.strip()
    async with SessionLocal() as s:
        await bot.load_settings(s)  # DB qiymatlari .env ustidan yozadi
        if not bot.token:
            # Zaxira: eski `Setting` bo'sh bo'lsa ham, CRM sozlamalarida
            # (TelegramSettings, shifrlangan) token bo'lishi mumkin.
            tg = await crm_service.get_telegram_settings(s)
            decrypted = crypto.decrypt(tg.bot_token_enc)
            if decrypted:
                bot.token = decrypted
    bot.client = http_client
    bot.polling_enabled = settings.TELEGRAM_POLLING
    bot.queue = asyncio.Queue(maxsize=settings.TELEGRAM_QUEUE_SIZE)
    for i in range(max(1, settings.TELEGRAM_WORKERS)):
        t = asyncio.create_task(bot.worker(i))
        _bg_tasks.add(t)
        t.add_done_callback(_bg_tasks.discard)
    if settings.TELEGRAM_POLLING:
        t = asyncio.create_task(bot.poll_loop())
        _bg_tasks.add(t)
        t.add_done_callback(_bg_tasks.discard)

    log.info(
        "promtchi API tayyor — env=%s db=%s pool=%s+%s trust_proxy=%s tg=%s(%s chat)",
        settings.ENV, "sqlite" if settings.is_sqlite else "postgres",
        settings.DB_POOL_SIZE, settings.DB_MAX_OVERFLOW, settings.TRUST_PROXY,
        "on" if bot.token else "off", len(bot.targets),
    )
    yield

    for t in list(_bg_tasks):
        t.cancel()
    if http_client is not None:
        await http_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="promtchi® API",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

# Middleware: OXIRGI qo'shilgan ENG TASHQARIDA ishlaydi.
# Kerakli tartib: SecurityHeaders → CORS → BodyLimit → RateLimit → GZip → app
app.add_middleware(GZipMiddleware, minimum_size=800, compresslevel=6)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(crm_api.router)


# ══════════ PUBLIC ══════════

@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok", "service": "promtchi-api", "version": app.version}


@app.get("/api/content")
async def get_content(request: Request):
    # DB sessiyasi Depends orqali OLINMAYDI — kesh tayyor bo'lsa (99.9% holat)
    # so'rov umuman DB qatlamiga tegmaydi.
    if not content_cache.ready:  # kesh bo'sh bo'lsa (kutilmagan holat) — DB'dan
        async with SessionLocal() as session:
            row = await session.get(Content, 1)
        if row is None:
            content_cache.set(DEFAULT_CONTENT, 0)
        else:
            content_cache.set(row.data, row.version)

    headers = {
        "ETag": content_cache.etag,
        "X-Content-Version": str(content_cache.version),
        "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
    }
    if request.headers.get("if-none-match") == content_cache.etag:
        return Response(status_code=304, headers=headers)

    return Response(
        content=content_cache.body, media_type="application/json", headers=headers
    )


@app.get("/api/posts")
async def list_posts_public(request: Request):
    """E'lon qilingan postlar — xotira keshidan (kontent kabi)."""
    if not posts_cache.ready:
        async with SessionLocal() as session:
            res = await session.execute(
                select(Post).where(Post.published == True)  # noqa: E712
                .order_by(Post.created_at.desc(), Post.id.desc()).limit(50)
            )
            posts_cache.set([p.as_dict() for p in res.scalars().all()], 0)

    headers = {
        "ETag": posts_cache.etag,
        "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
    }
    if request.headers.get("if-none-match") == posts_cache.etag:
        return Response(status_code=304, headers=headers)
    return Response(
        content=posts_cache.body, media_type="application/json", headers=headers
    )


@app.post("/api/leads", status_code=201)
async def create_lead(
    payload: LeadIn, request: Request, session: AsyncSession = Depends(get_session)
):
    ip = getattr(request.state, "client_ip", "") or ""
    # Lead limitlari validatsiyadan KEYIN — xato forma (422) limit yemaydi.
    # DB'ga hali tegilmagan (sessiya birinchi so'rovgacha ulanish olmaydi).
    ok, retry, msg = check_lead_limits(ip or "unknown")
    if not ok:
        raise HTTPException(429, msg, headers={"Retry-After": str(retry)})
    lead = Lead(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        project_type=payload.project_type.strip(),
        message=payload.message.strip(),
        ip=ip[:64],
    )
    session.add(lead)
    await session.commit()
    bot.queue_lead(lead)  # guruh + obuna bo'lgan adminlarga (navbat orqali)
    return {"ok": True, "id": lead.id}


# ══════════ AUTH ══════════

@app.post("/api/auth/login")
async def login(
    payload: LoginIn, request: Request, response: Response,
    session: AsyncSession = Depends(get_session),
):
    ip = getattr(request.state, "client_ip", "") or "unknown"
    ua = (request.headers.get("user-agent") or "?")[:180]
    email = payload.email.strip().lower()
    acc = await check_login(session, email, payload.password)
    if acc is None:
        # Token faqat XATO urinishda yeyiladi -> brute-force sekinlashadi,
        # to'g'ri email/parol bilan kirish esa hech qachon bloklanmaydi.
        login_limiter.hit(ip)
        log.warning("Admin login muvaffaqiyatsiz — email=%s ip=%s ua=%s", email, ip, ua)
        bot.queue_text_admins(
            f"❌ <b>Muvaffaqiyatsiz kirish urinishi</b>\nEmail: {escape(email)}\nIP: {escape(ip)}\nUA: {escape(ua)}"
        )
        raise HTTPException(401, "Email yoki parol noto'g'ri")
    log.info("Admin login muvaffaqiyatli — email=%s ip=%s ua=%s", acc.email, ip, ua)
    bot.queue_text_admins(
        f"✅ <b>Admin panelga kirildi</b>\nEmail: {escape(acc.email)}\nIP: {escape(ip)}\nUA: {escape(ua)}"
    )
    token = create_token(acc.email)
    set_admin_cookie(response, token)
    # JSON'dagi `token` — faqat skript/test uchun qulaylik; admin.html HttpOnly
    # cookie'ga tayanadi (JS undan tokenni o'qiy olmaydi — XSS himoyasi).
    return {"token": token, "expires_hours": settings.JWT_EXPIRE_HOURS}


@app.post("/api/auth/logout")
async def logout(response: Response):
    """Cookie'ni serverda tozalaydi — HttpOnly bo'lgani uchun buni faqat
    backend qila oladi (JS to'g'ridan-to'g'ri o'chira olmaydi).

    ATAYLAB require_admin'ga bog'liq EMAS: token eskirgan/yaroqsiz bo'lsa ham
    "chiqish" ishlashi kerak, va require_admin'ning o'z siljitish effekti
    shu yerda ikkita ziddiyatli Set-Cookie yubormasligi uchun chetlab o'tiladi.
    """
    clear_admin_cookie(response)
    return {"ok": True}


_GENERIC_RESET_MSG = {
    "ok": True,
    "message": "Agar bu email ro'yxatdan o'tgan bo'lsa, tiklash havolasi yuborildi.",
}


@app.post("/api/auth/forgot-password")
async def forgot_password(
    payload: ForgotPasswordIn, request: Request, session: AsyncSession = Depends(get_session)
):
    """Parolni unutgan admin uchun — email mos kelsa-kelmasa bir xil javob qaytadi
    (email enumeration'ning oldini olish uchun)."""
    ip = getattr(request.state, "client_ip", "") or "unknown"
    ok, retry = check_pwreset_limit(ip)
    if not ok:
        raise HTTPException(
            429, "Juda ko'p urinish — birozdan so'ng qayta urining",
            headers={"Retry-After": str(retry)},
        )
    email = payload.email.strip().lower()
    acc = await get_account(session, email)
    if acc is None:
        return _GENERIC_RESET_MSG
    if await recent_token_exists(session, "reset_password"):
        return _GENERIC_RESET_MSG
    token = await create_admin_token(session, "reset_password", payload=acc.email)
    url = f"{settings.SITE_URL}/reset-password.html?token={token}"
    await send_email(acc.email, "promtchi — parolni tiklash", reset_password_email(url))
    return _GENERIC_RESET_MSG


@app.post("/api/auth/reset-password")
async def reset_password(payload: ResetPasswordIn, session: AsyncSession = Depends(get_session)):
    row = await consume_admin_token(session, payload.token, "reset_password")
    if row is None:
        raise HTTPException(400, "Havola noto'g'ri yoki muddati tugagan")
    ok = await set_account_password(session, row.payload, payload.new_password)
    if not ok:
        raise HTTPException(400, "Hisob topilmadi")
    bot.queue_text_admins(f"🔑 <b>Parol o'zgartirildi</b>\nEmail: {escape(row.payload)}")
    return {"ok": True}


@app.post("/api/auth/confirm-token")
async def confirm_token(payload: ConfirmTokenIn, session: AsyncSession = Depends(get_session)):
    """Email qo'shish/o'chirish tasdiqlash havolasi — token o'zi maqsadini bildiradi."""
    row = await consume_admin_token(session, payload.token, "add_email")
    if row is not None:
        # Yangi format: JSON {"email","password","password_hash"} — parol taklif
        # qilinganda kiritilgan, hisob tasdiqlangan zahoti shu parol bilan faollashadi.
        # Eski (bu o'zgarishdan oldin yuborilgan) tokenlar payload'da faqat email
        # matnini saqlaydi — moslik uchun qo'llab-quvvatlanadi (parolsiz, keyin
        # "qayta faollashtirish havolasi" bilan o'rnatiladi).
        plain_password = ""
        try:
            data = json.loads(row.payload)
            new_email, pw_hash, plain_password = data["email"], data["password_hash"], data.get("password", "")
        except (json.JSONDecodeError, KeyError, TypeError):
            new_email, pw_hash = row.payload, ""

        if pw_hash:
            acc = await add_admin_account_with_password(session, new_email, pw_hash)
        else:
            acc = await add_admin_account(session, new_email)
        if acc is None:
            raise HTTPException(400, f"Hisoblar soni chegarasiga yetgan (ko'pi bilan {MAX_ADMIN_ACCOUNTS} ta)")

        if pw_hash:
            login_url = f"{settings.SITE_URL}/admin"
            await send_email(acc.email, "promtchi — hisobingiz tayyor", account_ready_email(login_url, acc.email))
            bot.queue_text_admins(
                "🔐 <b>Yangi admin qo'shildi — login ma'lumotlari</b>\n"
                f"Email: <code>{escape(acc.email)}</code>\nParol: <code>{escape(plain_password)}</code>"
            )
        else:
            reset_token = await create_admin_token(session, "reset_password", payload=acc.email)
            reset_url = f"{settings.SITE_URL}/reset-password.html?token={reset_token}"
            await send_email(acc.email, "promtchi — hisobingiz yaratildi", new_account_email(reset_url))
            bot.queue_text_admins(f"➕ <b>Yangi admin email qo'shildi</b>\nEmail: {escape(acc.email)}")
        return {"ok": True, "action": "add_email", "email": acc.email}

    row = await consume_admin_token(session, payload.token, "remove_email")
    if row is not None:
        ok = await remove_admin_account(session, row.payload)
        if not ok:
            raise HTTPException(400, "Bu emailni o'chirib bo'lmaydi")
        bot.queue_text_admins(f"➖ <b>Admin email o'chirildi</b>\nEmail: {escape(row.payload)}")
        return {"ok": True, "action": "remove_email", "email": row.payload}

    row = await consume_admin_token(session, payload.token, "set_primary")
    if row is not None:
        old_primary = await get_primary_account(session)
        ok = await set_primary_account(session, row.payload)
        if not ok:
            raise HTTPException(400, "Bu hisobni super admin qilib bo'lmaydi")
        old_email = old_primary.email if old_primary else "?"
        bot.queue_text_admins(
            "👑 <b>Super admin almashtirildi</b>\n"
            f"Eski: {escape(old_email)}\nYangi: {escape(row.payload)}"
        )
        return {"ok": True, "action": "set_primary", "email": row.payload}

    raise HTTPException(400, "Havola noto'g'ri yoki muddati tugagan")


@app.post("/api/auth/tg-super/confirm-old")
async def tg_super_confirm_old(payload: ConfirmTokenIn, session: AsyncSession = Depends(get_session)):
    """Telegram botdagi /super oqimi — hozirgi super admin shu havolani bosgach
    chaqiriladi. Bot chatida jarayonni keyingi bosqichga (yangi email so'rash)
    o'tkazadi. Public (token o'zi bir martalik va 10 daqiqa amal qiladi)."""
    row = await consume_admin_token(session, payload.token, "tg_super_old")
    if row is None:
        raise HTTPException(400, "Havola noto'g'ri yoki muddati tugagan")
    chat_id = int(row.payload)
    ok = await bot.advance_super_flow_after_old_confirm(chat_id)
    if not ok:
        raise HTTPException(400, "Jarayon topilmadi — vaqti tugagan yoki bekor qilingan bo'lishi mumkin. Botga qaytadan /super yozing.")
    return {"ok": True}


# ══════════ ADMIN: HISOB (email/parol) ══════════

@app.get("/api/admin/account")
async def get_account_info(
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    """Oddiy admin FAQAT o'zini ko'radi — boshqa hisoblar va kim SUPER ADMIN
    ekani unga ko'rsatilmaydi (adminlar bir-biridan bexabar bo'lishi kerak).
    Super admin esa hammasini ko'radi va boshqaradi."""
    acc = await get_account(session, email)
    is_super = bool(acc and acc.is_primary)
    if not is_super:
        return {"email": email, "is_super_admin": False}
    accounts = await list_admin_accounts(session)
    return {
        "email": email,
        "is_super_admin": True,
        "accounts": [a.as_dict() for a in accounts],
        "max_accounts": MAX_ADMIN_ACCOUNTS,
    }


@app.post("/api/admin/account/request-password-reset")
async def request_password_reset(
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    """Admin panel ichidan — tiklash havolasi HOZIR LOGIN QILINGAN emailga yuboriladi."""
    if await recent_token_exists(session, "reset_password"):
        return {"ok": True}
    token = await create_admin_token(session, "reset_password", payload=email)
    url = f"{settings.SITE_URL}/reset-password.html?token={token}"
    await send_email(email, "promtchi — parolni tiklash", reset_password_email(url))
    return {"ok": True}


@app.post("/api/admin/account/emails/request-add")
async def request_add_email(
    payload: AddEmailRequestIn,
    _: str = Depends(require_primary_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin qo'shish FAQAT super admin ishi — oddiy admin bu endpointga
    kira olmaydi. Tasdiqlash havolasi baribir super adminning o'z emailiga
    boradi (JWT o'g'irlangan taqdirda ham himoya — 2FA kabi). Parol shu
    yerda kiritiladi — tasdiqlangach hisob darhol shu parol bilan faollashadi
    (ayni parol Telegram admin(lar)ga alohida yuboriladi)."""
    new_email = payload.new_email.strip().lower()
    if await get_account(session, new_email) is not None:
        raise HTTPException(400, "Bu email allaqachon ro'yxatda")
    accounts = await list_admin_accounts(session)
    if len(accounts) >= MAX_ADMIN_ACCOUNTS:
        raise HTTPException(400, f"Hisoblar soni chegarasiga yetgan (ko'pi bilan {MAX_ADMIN_ACCOUNTS} ta)")
    primary = await get_primary_account(session)
    if primary is None:
        raise HTTPException(400, "Super admin sozlanmagan")
    if await recent_token_exists(session, "add_email"):
        return {"ok": True}
    token_payload = json.dumps({
        "email": new_email,
        "password": payload.password,
        "password_hash": hash_password(payload.password),
    })
    token = await create_admin_token(session, "add_email", payload=token_payload)
    url = f"{settings.SITE_URL}/confirm-email.html?token={token}"
    await send_email(primary.email, "promtchi — yangi admin email tasdiqlash", confirm_email_email(url, new_email, "qo'shish"))
    return {"ok": True}


@app.post("/api/admin/account/emails/{email}/resend-activation")
async def resend_activation(
    email: str,
    _: str = Depends(require_primary_admin),
    session: AsyncSession = Depends(get_session),
):
    """Bu o'zgarishdan OLDIN qo'shilgan, hali parolsiz (faollashtirilmagan)
    hisoblar uchun — qayta parol o'rnatish havolasini yuboradi. Faqat super
    admin so'ray oladi."""
    acc = await get_account(session, email.strip().lower())
    if acc is None:
        raise HTTPException(404, "Bunday email topilmadi")
    if acc.password_hash:
        raise HTTPException(400, "Bu hisob allaqachon faollashtirilgan")
    if await recent_token_exists(session, "reset_password"):
        return {"ok": True}
    token = await create_admin_token(session, "reset_password", payload=acc.email)
    url = f"{settings.SITE_URL}/reset-password.html?token={token}"
    await send_email(acc.email, "promtchi — hisobingizni faollashtiring", new_account_email(url))
    return {"ok": True}


@app.post("/api/admin/account/emails/request-remove")
async def request_remove_email(
    payload: RemoveEmailRequestIn,
    _: str = Depends(require_primary_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin o'chirish FAQAT super admin ishi. Tasdiqlash havolasi super
    adminning o'z emailiga boradi. Super adminning o'zini bu yo'l bilan
    o'chirib bo'lmaydi."""
    target = payload.email.strip().lower()
    acc = await get_account(session, target)
    if acc is None:
        raise HTTPException(404, "Bunday email topilmadi")
    if acc.is_primary:
        raise HTTPException(400, "Super adminni o'chirib bo'lmaydi")
    primary = await get_primary_account(session)
    if primary is None:
        raise HTTPException(400, "Super admin sozlanmagan")
    if await recent_token_exists(session, "remove_email"):
        return {"ok": True}
    token = await create_admin_token(session, "remove_email", payload=target)
    url = f"{settings.SITE_URL}/confirm-email.html?token={token}"
    await send_email(primary.email, "promtchi — admin email o'chirishni tasdiqlash", confirm_email_email(url, target, "o'chirish"))
    return {"ok": True}


@app.post("/api/admin/account/emails/request-set-primary")
async def request_set_primary(
    payload: SetPrimaryRequestIn,
    email: str = Depends(require_primary_admin),
    session: AsyncSession = Depends(get_session),
):
    """Super admin huquqini boshqa hisobga o'tkazishni so'raydi — FAQAT
    hozirgi super admin so'ray oladi, tasdiqlash havolasi ham uning o'z
    emailiga boradi (o'z amalini qayta tasdiqlash — 2FA kabi)."""
    target = payload.email.strip().lower()
    target_acc = await get_account(session, target)
    if target_acc is None:
        raise HTTPException(404, "Bunday email topilmadi")
    if target_acc.is_primary:
        raise HTTPException(400, "Bu hisob allaqachon super admin")
    if not target_acc.password_hash:
        raise HTTPException(400, "Bu hisob hali faollashtirilmagan (parol o'rnatilmagan)")
    if await recent_token_exists(session, "set_primary"):
        return {"ok": True}
    token = await create_admin_token(session, "set_primary", payload=target)
    url = f"{settings.SITE_URL}/confirm-email.html?token={token}"
    await send_email(email, "promtchi — super adminni almashtirish", set_primary_email(url, target))
    return {"ok": True}


# ══════════ ADMIN ══════════

@app.put("/api/admin/content")
async def put_content(
    doc: ContentDoc,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(Content, 1)
    data = doc.model_dump()
    if row is None:
        row = Content(id=1, data=data, version=1)
        session.add(row)
    else:
        row.data = data
        row.version += 1
    await session.commit()
    content_cache.set(data, row.version)
    return {"ok": True, "version": row.version}


@app.post("/api/admin/content/reset")
async def reset_content(
    _: str = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    row = await session.get(Content, 1)
    if row is None:
        row = Content(id=1, data=DEFAULT_CONTENT, version=1)
        session.add(row)
    else:
        row.data = DEFAULT_CONTENT
        row.version += 1
    await session.commit()
    content_cache.set(DEFAULT_CONTENT, row.version)
    return {"ok": True, "version": row.version}


@app.get("/api/admin/leads")
async def list_leads(
    response: Response,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Arizalar. Moslik uchun massiv qaytaradi; umumiy soni X-Total-Count'da."""
    total = await session.scalar(select(func.count()).select_from(Lead))
    res = await session.execute(
        select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc())
        .limit(limit).offset(offset)
    )
    response.headers["X-Total-Count"] = str(total or 0)
    return [l.as_dict() for l in res.scalars().all()]


@app.patch("/api/admin/leads/{lead_id}")
async def set_lead_status(
    lead_id: int,
    payload: LeadStatusIn,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        update(Lead).where(Lead.id == lead_id).values(status=payload.status)
    )
    if res.rowcount == 0:
        raise HTTPException(404, "Ariza topilmadi")
    await session.commit()
    await bot.notify_lead_status(lead_id, payload.status)
    return {"ok": True, "status": payload.status}


@app.delete("/api/admin/leads/{lead_id}")
async def delete_lead(
    lead_id: int,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(Lead).where(Lead.id == lead_id))
    await session.commit()
    return {"ok": True}


# ══════════ ADMIN: POSTLAR ══════════

@app.get("/api/admin/posts")
async def list_posts_admin(
    _: str = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    res = await session.execute(
        select(Post).order_by(Post.created_at.desc(), Post.id.desc())
    )
    return [p.as_dict() for p in res.scalars().all()]


@app.post("/api/admin/posts", status_code=201)
async def create_post(
    payload: PostIn,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    post = Post(
        title=payload.title.strip(),
        body=payload.body.strip(),
        image=payload.image.strip(),
        video=payload.video.strip(),
        published=payload.published,
    )
    session.add(post)
    await session.commit()
    posts_cache.clear()
    return post.as_dict()


@app.put("/api/admin/posts/{post_id}")
async def update_post(
    post_id: int,
    payload: PostIn,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(404, "Post topilmadi")
    post.title = payload.title.strip()
    post.body = payload.body.strip()
    post.image = payload.image.strip()
    post.video = payload.video.strip()
    post.published = payload.published
    await session.commit()
    posts_cache.clear()
    return post.as_dict()


@app.delete("/api/admin/posts/{post_id}")
async def delete_post(
    post_id: int,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(Post).where(Post.id == post_id))
    await session.commit()
    posts_cache.clear()
    return {"ok": True}


# ══════════ ADMIN: TELEGRAM ══════════

async def _tg_state() -> dict:
    """Bot holati + bot username (havola yasash uchun)."""
    username = ""
    if bot.token:
        me = await bot.call("getMe")
        if me.get("ok"):
            username = me["result"].get("username", "")
    return {
        "has_token": bool(bot.token),
        "bot_token_masked": bot.masked_token(),
        "bot_username": username,
        "chat_id": bot.group_chat_id,
        "subscribers": sorted(bot.subscribers),
        "admins": bot.admins,
        "targets": len(bot.targets),
        "polling": bot.polling_enabled,
        "active": bot.ready,
        "last_error": bot.last_error,
    }


@app.get("/api/admin/telegram")
async def get_telegram(_: str = Depends(require_primary_admin)):
    """Butun Telegram bo'limi (holat ham, boshqaruv ham) FAQAT super adminga —
    oddiy admin bu haqda hech narsa bilmasligi kerak."""
    return await _tg_state()


@app.put("/api/admin/telegram")
async def put_telegram(
    payload: TelegramSettingsIn,
    _: str = Depends(require_primary_admin),
    session: AsyncSession = Depends(get_session),
):
    """Bot va guruh/kanal sozlamalari — FAQAT super admin boshqaradi.

    bot_token=None — token o'zgartirilmaydi; "" — o'chiriladi.

    BITTA bot CRM bilan ham baham ko'riladi — token bu yerdan o'zgartirilsa,
    CRM Telegram sozlamalaridagi shifrlangan nusxa (TelegramSettings) ham
    yangilanadi, aks holda ikkalasi bir-biridan uzoqlashib qoladi.
    """
    if payload.bot_token is not None:
        bot.token = payload.bot_token.strip()
        bot.last_error = ""
        bot.polling_enabled = settings.TELEGRAM_POLLING  # yangi token -> qayta urinamiz
        await session.merge(Setting(key="tg_bot_token", value=bot.token))
        tg = await crm_service.get_telegram_settings(session)
        tg.bot_token_enc = crypto.encrypt(bot.token)
        await bot.ensure_no_webhook()
    bot.group_chat_id = payload.chat_id.strip()
    await session.merge(Setting(key="tg_chat_id", value=bot.group_chat_id))
    await session.commit()
    return await _tg_state()


@app.delete("/api/admin/telegram/subscribers/{chat_id}")
async def remove_subscriber(chat_id: int, _: str = Depends(require_primary_admin)):
    """Obunachini ro'yxatdan chiqarish (chat endi xabarnoma olmaydi) — faqat super admin."""
    await bot.remove_subscriber(chat_id)
    return await _tg_state()


@app.get("/api/admin/telegram/admins")
async def list_telegram_admins(_: str = Depends(require_primary_admin)):
    """Telegram admin(lar) ro'yxati — sezgir xabarnomalar (parol, kirish urinishi
    va h.k.) shu chatlarga boradi, guruh/kanalga emas. Faqat super admin ko'ra oladi."""
    return {"admins": bot.admins}


@app.post("/api/admin/telegram/admins")
async def add_telegram_admin(payload: TelegramAdminIn, _: str = Depends(require_primary_admin)):
    """Yangi Telegram admin qo'shish — faqat super admin. chat_id botga /start
    yozgan foydalanuvchining Chat ID'si (bot javobida ko'rsatiladi)."""
    ok = await bot.add_admin(payload.chat_id, payload.label)
    if not ok:
        raise HTTPException(400, "Bu chat ID allaqachon admin sifatida qo'shilgan")
    return {"admins": bot.admins}


@app.delete("/api/admin/telegram/admins/{chat_id}")
async def remove_telegram_admin(chat_id: int, _: str = Depends(require_primary_admin)):
    """Telegram adminni ro'yxatdan chiqarish — faqat super admin."""
    ok = await bot.remove_admin(chat_id)
    if not ok:
        raise HTTPException(404, "Bunday Telegram admin topilmadi")
    return {"admins": bot.admins}


@app.post("/api/admin/telegram/test")
async def test_telegram(_: str = Depends(require_primary_admin)):
    """Jonli tekshirish — barcha ulangan chatlarga test xabar yuboradi."""
    if not bot.token:
        raise HTTPException(400, "Bot token kiritilmagan")
    me = await bot.call("getMe")
    if not me.get("ok"):
        raise HTTPException(400, f"Token noto'g'ri: {me.get('description', '')}")
    if not bot.targets:
        raise HTTPException(
            400,
            f"Hech qanday chat ulanmagan. Botni (@{me['result'].get('username','')}) "
            "guruhga qo'shing yoki unga /start yozing.",
        )
    sent, errors = 0, []
    for chat in bot.targets:
        data = await bot.call("sendMessage", {
            "chat_id": chat,
            "text": "✅ <b>promtchi</b> — test xabar. Bot to'g'ri sozlangan!",
            "parse_mode": "HTML",
        })
        if data.get("ok"):
            sent += 1
        else:
            errors.append(f"{chat}: {data.get('description')}")
    if not sent:
        raise HTTPException(400, "Yuborilmadi — " + "; ".join(errors))
    return {"ok": True, "sent": sent, "errors": errors}


# ══════════ FAYL YUKLASH (rasm / video) ══════════

UPLOAD_DIR = STATIC_DIR / "uploads"
_ALLOWED_UPLOADS = {
    # kengaytma -> (MIME, sehrli baytlar ro'yxati yoki None)
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
}


@app.post("/api/admin/upload")
async def upload_file(
    file: UploadFile = File(...),
    _: str = Depends(require_admin),
):
    """Rasm yoki video yuklash. Qaytaradi: {url, kind, size}."""
    name = (file.filename or "").strip()
    ext = Path(name).suffix.lower()
    if ext not in _ALLOWED_UPLOADS:
        raise HTTPException(
            400, f"Bu format qo'llab-quvvatlanmaydi ({ext or '?'}). "
                 "Ruxsat: jpg, png, webp, gif, svg, mp4, webm, mov"
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe = secrets.token_hex(8) + ext
    dest = UPLOAD_DIR / safe

    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(1 << 20):  # 1 MB bo'laklab
                size += len(chunk)
                if size > settings.MAX_UPLOAD_BYTES:
                    out.close()
                    dest.unlink(missing_ok=True)
                    mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
                    raise HTTPException(413, f"Fayl juda katta (maksimum {mb} MB)")
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(500, f"Fayl saqlanmadi: {e}")
    finally:
        await file.close()

    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Bo'sh fayl")

    kind = "video" if _ALLOWED_UPLOADS[ext].startswith("video") else "image"
    log.info("Fayl yuklandi: %s (%s, %.1f KB)", safe, kind, size / 1024)
    return {"url": f"/static/uploads/{safe}", "kind": kind, "size": size}


@app.delete("/api/admin/upload")
async def delete_upload(url: str = Query(...), _: str = Depends(require_admin)):
    """Yuklangan faylni o'chirish (faqat uploads papkasidan)."""
    fname = Path(url).name
    target = UPLOAD_DIR / fname
    # Papkadan chiqib ketishga urinishni bloklaymiz
    if target.parent.resolve() != UPLOAD_DIR.resolve():
        raise HTTPException(400, "Noto'g'ri yo'l")
    target.unlink(missing_ok=True)
    return {"ok": True}


# ══════════ FIKRLAR (mijozlar yozadi) ══════════

@app.get("/api/reviews")
async def list_reviews_public(request: Request):
    """Tasdiqlangan fikrlar — public, keshlangan."""
    if not reviews_cache.ready:
        async with SessionLocal() as session:
            res = await session.execute(
                select(Review).where(Review.approved == True)  # noqa: E712
                .order_by(Review.created_at.desc(), Review.id.desc()).limit(60)
            )
            reviews_cache.set([r.as_dict() for r in res.scalars().all()], 0)

    headers = {
        "ETag": reviews_cache.etag,
        "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
    }
    if request.headers.get("if-none-match") == reviews_cache.etag:
        return Response(status_code=304, headers=headers)
    return Response(
        content=reviews_cache.body, media_type="application/json", headers=headers
    )


@app.post("/api/reviews", status_code=201)
async def create_review(
    payload: ReviewIn, request: Request, session: AsyncSession = Depends(get_session)
):
    """Mijoz fikri. Faqat admin bergan bir martalik kod bilan yoziladi."""
    ip = getattr(request.state, "client_ip", "") or "unknown"
    ok, retry, msg = check_review_limits(ip)
    if not ok:
        raise HTTPException(429, msg, headers={"Retry-After": str(retry)})

    code = payload.code.strip().upper()
    rc = await session.get(ReviewCode, code)
    if rc is None:
        raise HTTPException(403, "Kod noto'g'ri. Fikr qoldirish uchun kod bizdan olinadi.")
    if rc.used_at is not None:
        raise HTTPException(409, "Bu koddan allaqachon foydalanilgan.")

    review = Review(
        name=payload.name.strip(),
        role=payload.role.strip(),
        text=payload.text.strip(),
        rating=payload.rating,
        approved=False,  # admin ko'rib chiqadi (matnni o'zgartira olmaydi)
        code=code,
        ip=ip[:64],
    )
    session.add(review)
    rc.used_at = datetime.now(timezone.utc)
    await session.commit()

    if bot.queue is not None and bot.ready:
        bot.queue_text(
            "⭐️ <b>Yangi fikr keldi</b>\n\n"
            f"👤 {escape(review.name)}"
            + (f" — {escape(review.role)}" if review.role else "")
            + f"\n{'⭐️' * review.rating}\n\n💬 {escape(review.text)}\n\n"
            "<i>Admin panelda tasdiqlang — shundan keyin saytda ko'rinadi.</i>"
        )
    return {"ok": True, "id": review.id, "pending": True}


@app.get("/api/admin/reviews")
async def list_reviews_admin(
    _: str = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    res = await session.execute(
        select(Review).order_by(Review.created_at.desc(), Review.id.desc())
    )
    return [r.as_dict(admin=True) for r in res.scalars().all()]


@app.post("/api/admin/reviews/{review_id}/approve")
async def approve_review(
    review_id: int,
    approved: bool = Query(True),
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Faqat ko'rinishni boshqaradi — fikr MATNI o'zgartirilmaydi."""
    r = await session.get(Review, review_id)
    if r is None:
        raise HTTPException(404, "Fikr topilmadi")
    r.approved = approved
    await session.commit()
    reviews_cache.clear()
    return r.as_dict(admin=True)


@app.delete("/api/admin/reviews/{review_id}")
async def delete_review(
    review_id: int,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(Review).where(Review.id == review_id))
    await session.commit()
    reviews_cache.clear()
    return {"ok": True}


@app.get("/api/admin/review-codes")
async def list_review_codes(
    _: str = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    res = await session.execute(
        select(ReviewCode).order_by(ReviewCode.created_at.desc())
    )
    return [c.as_dict() for c in res.scalars().all()]


@app.post("/api/admin/review-codes", status_code=201)
async def create_review_code(
    payload: ReviewCodeIn,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Mijozga beriladigan bir martalik kod yaratadi."""
    for _try in range(5):
        code = "PR-" + secrets.token_hex(3).upper()
        if await session.get(ReviewCode, code) is None:
            break
    else:
        raise HTTPException(500, "Kod yaratilmadi, qayta urining")
    rc = ReviewCode(code=code, client=payload.client.strip())
    session.add(rc)
    await session.commit()
    return rc.as_dict()


@app.delete("/api/admin/review-codes/{code}")
async def delete_review_code(
    code: str,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(ReviewCode).where(ReviewCode.code == code.upper()))
    await session.commit()
    return {"ok": True}


# ══════════ STATIC SAYT ══════════

_PAGE_CACHE = f"public, max-age={settings.STATIC_CACHE_SECONDS}, must-revalidate"


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def index(request: Request):
    """Bosh sahifa — xotiradan, oldindan gzip qilingan holda.

    Diskka faqat mtime tekshiruvi uchun murojaat qilinadi; GZip middleware ham
    ishga tushmaydi (Content-Encoding allaqachon qo'yilgan bo'ladi).
    """
    if not index_cache.load():
        raise HTTPException(404, "static/index.html topilmadi")

    # IP yoki boshqa host orqali kirilsa — noindex variant (canonical/OG teglar
    # baribir haqiqiy domenga ishora qiladi, faqat qidiruv tizimlari bu nusxani
    # alohida sahifa deb indekslamasin).
    host = (request.headers.get("host") or "").split(":")[0].lower()
    canonical = settings.CANONICAL_HOST.lower()
    is_canonical = not canonical or host in (canonical, f"www.{canonical}")

    etag = index_cache.etag if is_canonical else index_cache.etag_noindex
    headers = {
        "ETag": etag,
        "Cache-Control": _PAGE_CACHE,
        "Vary": "Accept-Encoding, Host",
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    if request.method == "HEAD":  # HEAD'da body yuborilmaydi (monitoring uchun)
        return Response(status_code=200, media_type="text/html", headers=headers)

    if "gzip" in request.headers.get("accept-encoding", ""):
        headers["Content-Encoding"] = "gzip"
        body = index_cache.gz if is_canonical else index_cache.gz_noindex
        return Response(body, media_type="text/html", headers=headers)
    body = index_cache.raw if is_canonical else index_cache.raw_noindex
    return Response(body, media_type="text/html", headers=headers)


@app.get("/admin", include_in_schema=False)
async def admin_page():
    f = STATIC_DIR / "admin.html"
    if f.exists():
        return FileResponse(f, headers={"Cache-Control": "no-store"})
    raise HTTPException(404, "static/admin.html topilmadi")


@app.get("/reset-password.html", include_in_schema=False)
async def reset_password_page():
    f = STATIC_DIR / "reset-password.html"
    if f.exists():
        return FileResponse(f, headers={"Cache-Control": "no-store"})
    raise HTTPException(404, "static/reset-password.html topilmadi")


@app.get("/confirm-email.html", include_in_schema=False)
async def confirm_email_page():
    f = STATIC_DIR / "confirm-email.html"
    if f.exists():
        return FileResponse(f, headers={"Cache-Control": "no-store"})
    raise HTTPException(404, "static/confirm-email.html topilmadi")


@app.get("/tg-super-confirm.html", include_in_schema=False)
async def tg_super_confirm_page():
    f = STATIC_DIR / "tg-super-confirm.html"
    if f.exists():
        return FileResponse(f, headers={"Cache-Control": "no-store"})
    raise HTTPException(404, "static/tg-super-confirm.html topilmadi")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
