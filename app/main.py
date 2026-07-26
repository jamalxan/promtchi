"""promtchi® backend — FastAPI.

Endpointlar:
  GET  /api/health              — holat
  GET  /api/content             — sayt kontenti (public, keshlangan + ETag)
  POST /api/auth/login          — {password} -> {token}
  PUT  /api/admin/content       — to'liq kontentni saqlash (Bearer)
  POST /api/admin/content/reset — boshlang'ich kontentga qaytarish (Bearer)
  POST /api/leads               — aloqa formasi arizasi (public, rate-limit)
  GET  /api/admin/leads         — arizalar ro'yxati (Bearer, ?limit=&offset=)
  DELETE /api/admin/leads/{id}  — arizani o'chirish (Bearer)
  GET  /                        — sayt (static/index.html)
Hujjatlar: /docs (faqat ENABLE_DOCS=true bo'lganda)
"""
import asyncio
import gzip
import hashlib
import html
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import check_password, create_token, require_admin
from .config import settings
from .db import Base, Content, Lead, SessionLocal, engine, get_session
from .schemas import DEFAULT_CONTENT, ContentDoc, LeadIn, LoginIn
from .security import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
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

    def set(self, data: dict, version: int) -> None:
        self.body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        self.etag = '"%s"' % hashlib.sha256(self.body).hexdigest()[:32]
        self.version = version

    @property
    def ready(self) -> bool:
        return bool(self.body)


content_cache = _ContentCache()


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

# Telegram xabarnomalari uchun navbat — burst paytida 1000 ta parallel
# HTTP so'rov ochilmasligi uchun.
tg_queue: asyncio.Queue | None = None
http_client: httpx.AsyncClient | None = None
_bg_tasks: set[asyncio.Task] = set()


async def _tg_worker(worker_id: int) -> None:
    assert tg_queue is not None
    while True:
        payload = await tg_queue.get()
        try:
            if http_client is not None:
                url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                await http_client.post(url, json=payload)
        except Exception as e:  # xabarnoma yiqilsa ham ariza saqlangan
            log.warning("Telegram xabarnoma yuborilmadi (worker %s): %s", worker_id, e)
        finally:
            tg_queue.task_done()
        # Telegram sekundiga ~30 xabar qabul qiladi
        await asyncio.sleep(1 / 15)


def _queue_telegram(lead: Lead) -> None:
    """Navbatga qo'yamiz. Navbat to'lgan bo'lsa jim tashlab yuboramiz."""
    if tg_queue is None or not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        return
    e = html.escape  # lead matni HTML parse_mode ichiga tushadi — escape shart
    text = (
        "🔥 <b>Yangi ariza — promtchi.uz</b>\n\n"
        f"👤 <b>Ism:</b> {e(lead.name)}\n"
        f"📞 <b>Aloqa:</b> {e(lead.phone or '—')}\n"
        f"📦 <b>Loyiha:</b> {e(lead.project_type or '—')}\n"
        f"💬 <b>Xabar:</b> {e(lead.message or '—')}"
    )
    try:
        tg_queue.put_nowait(
            {"chat_id": settings.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
        )
    except asyncio.QueueFull:
        log.warning("Telegram navbati to'la — xabarnoma tashlandi (ariza saqlandi)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tg_queue, http_client

    settings.validate()

    # Jadval yaratish + birinchi ishga tushishda kontentni urug'lash
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
    tg_queue = asyncio.Queue(maxsize=settings.TELEGRAM_QUEUE_SIZE)
    for i in range(max(1, settings.TELEGRAM_WORKERS)):
        t = asyncio.create_task(_tg_worker(i))
        _bg_tasks.add(t)
        t.add_done_callback(_bg_tasks.discard)

    log.info(
        "promtchi API tayyor — env=%s db=%s pool=%s+%s trust_proxy=%s",
        settings.ENV, "sqlite" if settings.is_sqlite else "postgres",
        settings.DB_POOL_SIZE, settings.DB_MAX_OVERFLOW, settings.TRUST_PROXY,
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

@app.get("/api/health")
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


@app.post("/api/leads", status_code=201)
async def create_lead(
    payload: LeadIn, request: Request, session: AsyncSession = Depends(get_session)
):
    # Rate-limit RateLimitMiddleware'da, DB ulanishi olinishidan oldin tekshirilgan.
    ip = getattr(request.state, "client_ip", "") or ""
    lead = Lead(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        project_type=payload.project_type.strip(),
        message=payload.message.strip(),
        ip=ip[:64],
    )
    session.add(lead)
    await session.commit()
    _queue_telegram(lead)
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


@app.delete("/api/admin/leads/{lead_id}")
async def delete_lead(
    lead_id: int,
    _: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(Lead).where(Lead.id == lead_id))
    await session.commit()
    return {"ok": True}


# ══════════ STATIC SAYT ══════════

_PAGE_CACHE = f"public, max-age={settings.STATIC_CACHE_SECONDS}, must-revalidate"


@app.get("/", include_in_schema=False)
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
