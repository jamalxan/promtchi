"""CRM Kanban — HTTP API. Mantiq app/crm_service.py'da; bu yer faqat
so'rov/javob va ruxsatlar qatlami."""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import crm_constants as crm
from . import crm_service
from . import crypto
from .auth import get_account, list_admin_accounts, require_admin, require_primary_admin
from .db import AdminAccount, Lead, LeadNote, LeadStageHistory, Setting, get_session
from .schemas import (
    CrmTelegramSettingsIn, LeadAssignIn, LeadCreateIn, LeadNoteCreateIn,
    LeadStageChangeIn, LeadUpdateIn, SetAdminRoleIn,
)
from .telegram import bot

router = APIRouter(prefix="/api/admin/crm", tags=["crm"])


async def _get_lead_or_404(session: AsyncSession, lead_id: int) -> Lead:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Mijoz topilmadi")
    return lead


def _check_access(role: str, email: str, lead: Lead) -> None:
    if not crm_service.can_access_lead(role, email, lead):
        raise HTTPException(403, "Sizda bu mijozga ruxsat yo'q")


@router.get("/meta")
async def crm_meta(_: str = Depends(require_admin)):
    """8 bosqich, loyiha turlari, manbalar — frontend shu yerdan chizadi
    (qiymatlar app/crm_constants.py'dan, ikki joyda takrorlanmaydi)."""
    return {"stages": crm.STAGES, "project_types": crm.PROJECT_TYPES, "sources": crm.SOURCES}


@router.get("/stats")
async def crm_stats(
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    """9.1-bo'lim: voronka soni, konversiya, o'rtacha bitim davri, menejerlar
    kesimi. Manager FAQAT o'z arizalari bo'yicha ko'radi."""
    role = await crm_service.get_role(session, email)
    base = select(Lead).where(Lead.is_archived.is_(False))
    if role == "manager":
        base = base.where(Lead.assigned_to == email)
    res = await session.execute(base)
    leads = res.scalars().all()

    funnel = {s["slug"]: 0 for s in crm.STAGES}
    for l in leads:
        if l.stage in funnel:
            funnel[l.stage] += 1

    total = len(leads)
    won = funnel.get("won", 0)
    lost = funnel.get("lost", 0)
    decided = won + lost
    conversion = round(won / decided * 100, 1) if decided else 0.0

    won_leads = [l for l in leads if l.stage == "won" and l.stage_changed_at and l.created_at]
    durations = []
    for l in won_leads:
        created = l.created_at
        changed = l.stage_changed_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if changed.tzinfo is None:
            changed = changed.replace(tzinfo=timezone.utc)
        durations.append((changed - created).total_seconds())
    avg_deal_days = round(sum(durations) / len(durations) / 86400, 1) if durations else None

    by_manager: dict[str, dict] = {}
    if role != "manager":
        for l in leads:
            key = l.assigned_to or "—"
            m = by_manager.setdefault(key, {"total": 0, "won": 0, "lost": 0})
            m["total"] += 1
            if l.stage == "won":
                m["won"] += 1
            elif l.stage == "lost":
                m["lost"] += 1
        for m in by_manager.values():
            decided_m = m["won"] + m["lost"]
            m["conversion"] = round(m["won"] / decided_m * 100, 1) if decided_m else 0.0

    by_source: dict[str, int] = {}
    for l in leads:
        by_source[l.source or "—"] = by_source.get(l.source or "—", 0) + 1

    return {
        "total": total,
        "funnel": funnel,
        "conversion_pct": conversion,
        "avg_deal_days": avg_deal_days,
        "by_manager": by_manager,
        "by_source": by_source,
    }


@router.get("/leads/export.csv")
async def export_leads_csv(
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    """6-bo'lim: eksport — manager qila olmaydi."""
    role = await crm_service.get_role(session, email)
    if role == "manager":
        raise HTTPException(403, "Ruxsat yo'q")
    res = await session.execute(
        select(Lead).where(Lead.is_archived.is_(False)).order_by(Lead.created_at.desc())
    )
    leads = res.scalars().all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "id", "name", "phone", "project_type", "stage", "source", "assigned_to",
        "budget", "message", "created_at", "stage_changed_at",
    ])
    for l in leads:
        w.writerow([
            l.id, l.name, l.phone, l.project_type, l.stage, l.source, l.assigned_to or "",
            l.budget if l.budget is not None else "", (l.message or "").replace("\n", " "),
            l.created_at.isoformat() if l.created_at else "",
            l.stage_changed_at.isoformat() if l.stage_changed_at else "",
        ])
    csv_bytes = ("﻿" + buf.getvalue()).encode("utf-8")  # BOM — Excel o'zbekcha harflarni to'g'ri ko'rsatsin
    return Response(
        content=csv_bytes, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=promtchi-crm-leads.csv"},
    )


@router.get("/accounts")
async def list_crm_accounts(
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    """Mas'ul biriktirish dropdown'i uchun — faollashtirilgan hisoblar ro'yxati.
    Manager biriktira olmaydi (assign_lead 403 qaytaradi), shuning uchun bu
    ro'yxat unga ko'rsatilmaydi."""
    role = await crm_service.get_role(session, email)
    if role == "manager":
        raise HTTPException(403, "Ruxsat yo'q")
    accounts = await list_admin_accounts(session)
    return [
        {"email": a.email, "role": "superadmin" if a.is_primary else a.role}
        for a in accounts if a.password_hash
    ]


@router.patch("/accounts/{email}/role")
async def set_account_role(
    email: str, payload: SetAdminRoleIn,
    _: str = Depends(require_primary_admin), session: AsyncSession = Depends(get_session),
):
    """Admin <-> manager rolini o'zgartirish — FAQAT super admin. Super
    adminning o'z roli is_primary bilan sinxron (bu yerdan o'zgarmaydi)."""
    acc = await get_account(session, email.strip().lower())
    if acc is None:
        raise HTTPException(404, "Bunday email topilmadi")
    if acc.is_primary:
        raise HTTPException(400, "Super adminning roli bu yerdan o'zgartirilmaydi")
    if not acc.password_hash:
        raise HTTPException(400, "Hisob hali faollashtirilmagan")
    acc.role = payload.role
    await session.commit()
    return {"email": acc.email, "role": acc.role}


@router.get("/leads")
async def list_leads(
    stage: str | None = None,
    assigned_to: str | None = None,
    project_type: str | None = None,
    source: str | None = None,
    q: str | None = None,
    archived: bool = False,
    email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """6-bo'lim: manager FAQAT o'ziga biriktirilganlarni ko'radi."""
    role = await crm_service.get_role(session, email)
    query = select(Lead).where(Lead.is_archived == archived)
    if role == "manager":
        query = query.where(Lead.assigned_to == email)
    elif assigned_to:
        query = query.where(Lead.assigned_to == assigned_to)
    if stage:
        query = query.where(Lead.stage == stage)
    if project_type:
        query = query.where(Lead.project_type == project_type)
    if source:
        query = query.where(Lead.source == source)
    if q:
        like = f"%{q.strip()}%"
        query = query.where((Lead.name.ilike(like)) | (Lead.phone.ilike(like)) | (Lead.message.ilike(like)))
    res = await session.execute(query.order_by(Lead.stage_changed_at.desc()).limit(500))
    leads = res.scalars().all()

    # Izohlar soni — bitta qo'shimcha so'rovda (N+1 emas)
    lead_ids = [l.id for l in leads]
    note_counts: dict[int, int] = {}
    if lead_ids:
        cres = await session.execute(
            select(LeadNote.lead_id, func.count()).where(LeadNote.lead_id.in_(lead_ids)).group_by(LeadNote.lead_id)
        )
        note_counts = dict(cres.all())

    out = []
    for l in leads:
        d = l.as_dict()
        d["notes_count"] = note_counts.get(l.id, 0)
        out.append(d)
    return out


@router.post("/leads", status_code=201)
async def create_lead_manual(
    payload: LeadCreateIn,
    email: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Qo'lda mijoz qo'shish — barcha rollar qo'sha oladi (6-bo'lim)."""
    contact_normalized, contact_type = crm_service.normalize_contact(payload.phone)
    lead = Lead(
        name=payload.name,
        phone=payload.phone.strip(),
        contact_normalized=contact_normalized,
        contact_type=contact_type,
        project_type=payload.project_type,
        message=payload.message.strip(),
        source=payload.source,
        assigned_to=payload.assigned_to.strip().lower() if payload.assigned_to else email,
        budget=payload.budget,
        stage=crm.DEFAULT_STAGE,
    )
    session.add(lead)
    await session.commit()
    session.add(LeadStageHistory(lead_id=lead.id, from_stage="", to_stage=lead.stage, changed_by=email))
    await session.commit()
    crm_service.queue_telegram_sync(bot, lead.id)
    return lead.as_dict()


@router.get("/leads/{lead_id}")
async def get_lead_detail(
    lead_id: int, email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    role = await crm_service.get_role(session, email)
    lead = await _get_lead_or_404(session, lead_id)
    _check_access(role, email, lead)
    notes_res = await session.execute(
        select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())
    )
    history_res = await session.execute(
        select(LeadStageHistory).where(LeadStageHistory.lead_id == lead_id).order_by(LeadStageHistory.changed_at.desc())
    )
    d = lead.as_dict()
    d["notes"] = [n.as_dict() for n in notes_res.scalars().all()]
    d["history"] = [h.as_dict() for h in history_res.scalars().all()]
    return d


@router.patch("/leads/{lead_id}")
async def update_lead(
    lead_id: int, payload: LeadUpdateIn,
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    role = await crm_service.get_role(session, email)
    lead = await _get_lead_or_404(session, lead_id)
    _check_access(role, email, lead)
    changed = False
    if payload.name is not None and payload.name.strip():
        lead.name = payload.name.strip()
        changed = True
    if payload.phone is not None:
        lead.phone = payload.phone.strip()
        lead.contact_normalized, lead.contact_type = crm_service.normalize_contact(lead.phone)
        changed = True
    if payload.project_type is not None:
        lead.project_type = payload.project_type
        changed = True
    if payload.message is not None:
        lead.message = payload.message.strip()
        changed = True
    if payload.budget is not None:
        lead.budget = payload.budget
        changed = True
    if payload.next_action_at is not None:
        lead.next_action_at = datetime.fromisoformat(payload.next_action_at) if payload.next_action_at else None
        changed = True
    if changed:
        await session.commit()
        crm_service.queue_telegram_sync(bot, lead.id)
    return lead.as_dict()


@router.patch("/leads/{lead_id}/stage")
async def change_lead_stage(
    lead_id: int, payload: LeadStageChangeIn,
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    role = await crm_service.get_role(session, email)
    lead = await _get_lead_or_404(session, lead_id)
    _check_access(role, email, lead)
    await crm_service.change_stage(session, lead, payload.stage, email)
    crm_service.queue_telegram_sync(bot, lead.id)
    return lead.as_dict()


@router.patch("/leads/{lead_id}/assign")
async def assign_lead(
    lead_id: int, payload: LeadAssignIn,
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    """6-bo'lim: mas'ul biriktirish FAQAT super admin/admin."""
    role = await crm_service.get_role(session, email)
    if role == "manager":
        raise HTTPException(403, "Faqat admin/super admin mas'ul biriktira oladi")
    lead = await _get_lead_or_404(session, lead_id)
    if payload.assigned_to:
        target = await session.get(AdminAccount, payload.assigned_to.strip().lower())
        if target is None:
            raise HTTPException(404, "Bunday admin topilmadi")
        lead.assigned_to = target.email
    else:
        lead.assigned_to = None
    await session.commit()
    crm_service.queue_telegram_sync(bot, lead.id)
    return lead.as_dict()


@router.delete("/leads/{lead_id}")
async def archive_lead(
    lead_id: int, email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    """6-bo'lim: arxivlash/o'chirish FAQAT super admin."""
    role = await crm_service.get_role(session, email)
    if role != "superadmin":
        raise HTTPException(403, "Faqat super admin arxivlay oladi")
    lead = await _get_lead_or_404(session, lead_id)
    lead.is_archived = True
    await session.commit()
    return {"ok": True}


@router.get("/leads/{lead_id}/notes")
async def list_lead_notes(
    lead_id: int, email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    role = await crm_service.get_role(session, email)
    lead = await _get_lead_or_404(session, lead_id)
    _check_access(role, email, lead)
    res = await session.execute(
        select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())
    )
    return [n.as_dict() for n in res.scalars().all()]


@router.post("/leads/{lead_id}/notes", status_code=201)
async def add_lead_note(
    lead_id: int, payload: LeadNoteCreateIn,
    email: str = Depends(require_admin), session: AsyncSession = Depends(get_session),
):
    role = await crm_service.get_role(session, email)
    lead = await _get_lead_or_404(session, lead_id)
    _check_access(role, email, lead)
    note = LeadNote(lead_id=lead_id, author=email, text=payload.text)
    session.add(note)
    await session.commit()
    return note.as_dict()


# ══════════ Telegram sozlamalari (faqat super admin — 6-bo'lim) ══════════

async def _crm_telegram_state(session: AsyncSession) -> dict:
    tg = await crm_service.get_telegram_settings(session)
    username = ""
    if bot.token:
        me = await bot.call("getMe")
        if me.get("ok"):
            username = me["result"].get("username", "")
    return {
        "has_token": bool(bot.token),
        "bot_token_masked": bot.masked_token(),
        "bot_username": username,
        "leads_chat_id": tg.leads_chat_id,
        "topic_thread_id": tg.topic_thread_id,
        "notify_chat_id": tg.notify_chat_id,
        "is_enabled": tg.is_enabled,
        "send_on_create": tg.send_on_create,
        "edit_on_update": tg.edit_on_update,
        "last_health_check": tg.last_health_check.isoformat() if tg.last_health_check else None,
        "last_health_status": tg.last_health_status,
    }


@router.get("/telegram")
async def get_crm_telegram(
    _: str = Depends(require_primary_admin), session: AsyncSession = Depends(get_session),
):
    return await _crm_telegram_state(session)


@router.put("/telegram")
async def put_crm_telegram(
    payload: CrmTelegramSettingsIn,
    _: str = Depends(require_primary_admin), session: AsyncSession = Depends(get_session),
):
    tg = await crm_service.get_telegram_settings(session)
    if payload.bot_token is not None:
        token = payload.bot_token.strip()
        tg.bot_token_enc = crypto.encrypt(token)
        # BITTA bot — token o'zgarsa jonli `bot` ham yangilanadi. Ikkinchi
        # mustaqil poller ISHGA TUSHIRILMAYDI (bir tokenda ikkita getUpdates
        # Telegram tomonidan 409 Conflict bilan taqiqlangan).
        bot.token = token
        bot.last_error = ""
        bot.polling_enabled = True
        await session.merge(Setting(key="tg_bot_token", value=token))
        await bot.ensure_no_webhook()
    tg.leads_chat_id = payload.leads_chat_id.strip()
    tg.topic_thread_id = payload.topic_thread_id
    tg.notify_chat_id = payload.notify_chat_id.strip()
    tg.is_enabled = payload.is_enabled
    tg.send_on_create = payload.send_on_create
    tg.edit_on_update = payload.edit_on_update
    await session.commit()
    return await _crm_telegram_state(session)


@router.post("/telegram/test")
async def test_crm_telegram(
    _: str = Depends(require_primary_admin), session: AsyncSession = Depends(get_session),
):
    """7-bo'lim: namuna xabar yuboradi, odam tiliga tarjima qilingan xato bilan."""
    tg = await crm_service.get_telegram_settings(session)
    if not bot.token:
        raise HTTPException(400, "Bot token kiritilmagan.")
    me = await bot.call("getMe")
    if not me.get("ok"):
        raise HTTPException(400, _humanize_tg_error(str(me.get("description", ""))))
    if not tg.leads_chat_id:
        raise HTTPException(400, "Mijozlar guruhi ID kiritilmagan.")
    body = {
        "chat_id": tg.leads_chat_id,
        "text": "✅ <b>promtchi CRM</b> — test xabar. Sozlamalar to'g'ri!",
        "parse_mode": "HTML",
    }
    if tg.topic_thread_id:
        body["message_thread_id"] = tg.topic_thread_id
    data = await bot.call("sendMessage", body)
    tg.last_health_check = datetime.now(timezone.utc)
    if data.get("ok"):
        tg.last_health_status = "ok"
        await session.commit()
        return {"ok": True}
    tg.last_health_status = str(data.get("description", ""))[:300]
    await session.commit()
    raise HTTPException(400, _humanize_tg_error(str(data.get("description", ""))))


def _humanize_tg_error(desc: str) -> str:
    d = desc.lower()
    if "chat not found" in d:
        return "Guruh topilmadi. ID ni tekshiring yoki botni guruhga qo'shing."
    if "kicked" in d or "bot was kicked" in d:
        return "Bot guruhdan chiqarilgan. Qayta qo'shib, admin qiling."
    if "not enough rights" in d or "have no rights" in d:
        return "Botga guruhda xabar yuborish/tahrirlash huquqi berilmagan."
    if "unauthorized" in d:
        return "Bot token noto'g'ri."
    return desc or "Noma'lum xato."
