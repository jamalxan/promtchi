"""promtchi® backend — FastAPI.

Endpointlar:
  GET  /api/health              — holat
  GET  /api/content             — sayt kontenti (public, keshlangan + ETag)
  GET  /api/posts               — e'lon qilingan postlar (public, keshlangan)
  POST /api/auth/login          — {password} -> {token}
  PUT  /api/admin/content       — to'liq kontentni saqlash (Bearer)
  POST /api/admin/content/reset — boshlang'ich kontentga qaytarish (Bearer)
  POST /api/leads               — aloqa formasi arizasi (public, rate-limit)
  GET  /api/admin/leads         — arizalar ro'yxati (Bearer, ?limit=&offset=)
  PATCH /api/admin/leads/{id}   — ariza holati: new/replied (Bearer)
  DELETE /api/admin/leads/{id}  — arizani o'chirish (Bearer)
  GET/POST/PUT/DELETE /api/admin/posts[/{id}] — postlar CRUD (Bearer)
  GET/PUT /api/admin/telegram   — bot token/chat ID boshqaruvi (Bearer)
  POST /api/admin/telegram/test — test xabar yuborish (Bearer)
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

from .auth import check_password, create_token, require_admin
from .config import settings
from .db import (
    Base, Content, Lead, Post, Review, ReviewCode, SessionLocal, Setting, engine,
    get_session, run_migrations,
)
from .schemas import (
    DEFAULT_CONTENT, ContentDoc, LeadIn, LeadStatusIn, LoginIn, PostIn,
    ReviewCodeIn, ReviewIn, TelegramSettingsIn,
)
from .telegram import bot
from .security import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    check_lead_limits,
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
class _PageCache:
    __slots__ = ("path", "mtime", "raw", "gz", "etag")

    def __init__(self, path: Path):
        self.path = path
        self.mtime: int = -1
        self.raw: bytes = b""
        self.gz: bytes = b""
        self.etag: str = ""

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

    # ── Telegram bot ──
    bot.token = settings.TELEGRAM_BOT_TOKEN.strip()
    bot.group_chat_id = settings.TELEGRAM_CHAT_ID.strip()
    async with SessionLocal() as s:
        await bot.load_settings(s)  # DB qiymatlari .env ustidan yozadi
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
async def login(payload: LoginIn, request: Request):
    if not check_password(payload.password):
        # Token faqat XATO urinishda yeyiladi -> brute-force sekinlashadi,
        # to'g'ri parol bilan kirish esa hech qachon bloklanmaydi.
        ip = getattr(request.state, "client_ip", "") or "unknown"
        login_limiter.hit(ip)
        log.warning("Admin login muvaffaqiyatsiz — ip=%s", ip)
        raise HTTPException(401, "Parol noto'g'ri")
    return {"token": create_token(), "expires_hours": settings.JWT_EXPIRE_HOURS}


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
        "targets": len(bot.targets),
        "polling": bot.polling_enabled,
        "active": bot.ready,
        "last_error": bot.last_error,
    }


@app.get("/api/admin/telegram")
async def get_telegram(_: str = Depends(require_admin)):
    return await _tg_state()


@app.put("/api/admin/telegram")
async def put_telegram(
    payload: TelegramSettingsIn,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Saqlash/o'zgartirish/o'chirish.

    bot_token=None — token o'zgartirilmaydi; "" — o'chiriladi.
    """
    if payload.bot_token is not None:
        bot.token = payload.bot_token.strip()
        bot.last_error = ""
        bot.polling_enabled = settings.TELEGRAM_POLLING  # yangi token -> qayta urinamiz
        await session.merge(Setting(key="tg_bot_token", value=bot.token))
        await bot.ensure_no_webhook()
    bot.group_chat_id = payload.chat_id.strip()
    await session.merge(Setting(key="tg_chat_id", value=bot.group_chat_id))
    await session.commit()
    return await _tg_state()


@app.delete("/api/admin/telegram/subscribers/{chat_id}")
async def remove_subscriber(chat_id: int, _: str = Depends(require_admin)):
    """Obunachini ro'yxatdan chiqarish (chat endi xabarnoma olmaydi)."""
    await bot.remove_subscriber(chat_id)
    return await _tg_state()


@app.post("/api/admin/telegram/test")
async def test_telegram(_: str = Depends(require_admin)):
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

    headers = {
        "ETag": index_cache.etag,
        "Cache-Control": _PAGE_CACHE,
        "Vary": "Accept-Encoding",
    }
    if request.headers.get("if-none-match") == index_cache.etag:
        return Response(status_code=304, headers=headers)
    if request.method == "HEAD":  # HEAD'da body yuborilmaydi (monitoring uchun)
        return Response(status_code=200, media_type="text/html", headers=headers)

    if "gzip" in request.headers.get("accept-encoding", ""):
        headers["Content-Encoding"] = "gzip"
        return Response(index_cache.gz, media_type="text/html", headers=headers)
    return Response(index_cache.raw, media_type="text/html", headers=headers)


@app.get("/admin", include_in_schema=False)
async def admin_page():
    f = STATIC_DIR / "admin.html"
    if f.exists():
        return FileResponse(f, headers={"Cache-Control": "no-store"})
    raise HTTPException(404, "static/admin.html topilmadi")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
