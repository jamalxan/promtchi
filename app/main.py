"""promtchi® backend — FastAPI.

Endpointlar:
  GET  /api/health              — holat
  GET  /api/content             — sayt kontenti (public)
  POST /api/auth/login          — {password} -> {token}
  PUT  /api/admin/content       — to'liq kontentni saqlash (Bearer)
  POST /api/admin/content/reset — boshlang'ich kontentga qaytarish (Bearer)
  POST /api/leads               — aloqa formasi arizasi (public, rate-limit)
  GET  /api/admin/leads         — arizalar ro'yxati (Bearer)
  DELETE /api/admin/leads/{id}  — arizani o'chirish (Bearer)
  GET  /                        — sayt (static/index.html)
Hujjatlar: /docs (Swagger)
"""
import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import check_password, create_token, require_admin
from .config import settings
from .db import Base, Content, Lead, engine, get_session
from .schemas import DEFAULT_CONTENT, ContentDoc, LeadIn, LoginIn

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Jadval yaratish + birinchi ishga tushishda kontentni urug'lash
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        res = await conn.execute(select(Content).where(Content.id == 1))
        if res.first() is None:
            await conn.execute(
                Content.__table__.insert().values(id=1, data=DEFAULT_CONTENT, version=1)
            )
            await conn.commit()
    yield
    await engine.dispose()


app = FastAPI(title="promtchi® API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── oddiy in-memory rate-limit (leads uchun) ─────────────────────────────────
_last_lead: dict[str, float] = {}


def _rate_ok(ip: str) -> bool:
    now = time.time()
    last = _last_lead.get(ip, 0)
    if now - last < settings.LEAD_COOLDOWN_SECONDS:
        return False
    _last_lead[ip] = now
    # xotira o'smasin
    if len(_last_lead) > 5000:
        cutoff = now - settings.LEAD_COOLDOWN_SECONDS
        for k in [k for k, v in _last_lead.items() if v < cutoff]:
            _last_lead.pop(k, None)
    return True


async def _notify_telegram(lead: Lead) -> None:
    """Yangi lead haqida Telegramga xabar (sozlanmagan bo'lsa jim o'tadi)."""
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        return
    text = (
        "🔥 <b>Yangi ariza — promtchi.uz</b>\n\n"
        f"👤 <b>Ism:</b> {lead.name}\n"
        f"📞 <b>Aloqa:</b> {lead.phone or '—'}\n"
        f"📦 <b>Loyiha:</b> {lead.project_type or '—'}\n"
        f"💬 <b>Xabar:</b> {lead.message or '—'}"
    )
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(
                url,
                json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
    except Exception:
        pass  # xabarnoma yiqilsa ham ariza saqlanadi


# ══════════ PUBLIC ══════════

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "promtchi-api"}


@app.get("/api/content")
async def get_content(session: AsyncSession = Depends(get_session)):
    row = await session.get(Content, 1)
    if row is None:
        return DEFAULT_CONTENT
    return row.data


@app.post("/api/leads", status_code=201)
async def create_lead(
    payload: LeadIn, request: Request, session: AsyncSession = Depends(get_session)
):
    ip = request.client.host if request.client else ""
    if not _rate_ok(ip):
        raise HTTPException(429, "Juda tez-tez — birozdan so'ng qayta urining")
    lead = Lead(
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        project_type=payload.project_type.strip(),
        message=payload.message.strip(),
        ip=ip,
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    asyncio.create_task(_notify_telegram(lead))
    return {"ok": True, "id": lead.id}


# ══════════ AUTH ══════════

@app.post("/api/auth/login")
async def login(payload: LoginIn):
    if not check_password(payload.password):
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
    return {"ok": True, "version": row.version}


@app.get("/api/admin/leads")
async def list_leads(
    _: str = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    res = await session.execute(select(Lead).order_by(Lead.created_at.desc()))
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

@app.get("/", include_in_schema=False)
async def index():
    f = STATIC_DIR / "index.html"
    if f.exists():
        return FileResponse(f)
    raise HTTPException(404, "static/index.html topilmadi")


@app.get("/admin", include_in_schema=False)
async def admin_page():
    f = STATIC_DIR / "admin.html"
    if f.exists():
        return FileResponse(f)
    raise HTTPException(404, "static/admin.html topilmadi")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
