"""CRM Kanban — Lead yaratish/bosqich almashtirish va Telegram sinxronizatsiya.

Bitta manba, ikki kirish nuqtasi: HTTP API (app/crm_api.py, admin panel) va
Telegram inline tugmalari (app/telegram.py callback handler) ikkalasi ham
shu yerdagi funksiyalarni chaqiradi — mantiq ikki joyda takrorlanmaydi.

Sinxronizatsiya tamoyili (5-bo'lim): bitta mijoz = guruhdagi bitta xabar.
Yangi Lead -> sendMessage (bir marta). Har o'zgarish -> shu xabarning o'ziga
editMessageText (hech qachon yangi xabar emas, "message to'g'ri topilmadi"
holatidan tashqari — o'shanda qayta yuboriladi va tg_message_id yangilanadi).
"""
import asyncio
import hashlib
import html
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import crm_constants as crm
from .db import AdminAccount, Lead, LeadStageHistory, SessionLocal, TelegramSettings

log = logging.getLogger("promtchi.crm")

_TG_USERNAME_RE = re.compile(r"^@[A-Za-z0-9_]{5,32}$")
_RETRY_DELAYS = [0, 1, 5, 30]  # soniya — birinchisi kechikishsiz


# ══════════ ruxsatlar ══════════

async def get_role(session: AsyncSession, email: str) -> str:
    """superadmin | admin | manager. Hisob topilmasa eng past huquq (manager)."""
    acc = await session.get(AdminAccount, email)
    if acc is None:
        return "manager"
    return "superadmin" if acc.is_primary else (acc.role or crm.DEFAULT_ADMIN_ROLE)


def can_access_lead(role: str, email: str, lead: Lead) -> bool:
    """6-bo'lim: manager FAQAT o'ziga biriktirilganlarni ko'radi/o'zgartiradi."""
    if role in ("superadmin", "admin"):
        return True
    return lead.assigned_to == email


# ══════════ aloqa normallashtirish (dublikat tekshirish uchun) ══════════

def normalize_contact(raw: str) -> tuple[str, str]:
    """(normalized, contact_type) qaytaradi. contact_type: phone|telegram|other."""
    v = (raw or "").strip()
    cleaned = re.sub(r"[\s\-()]", "", v)
    if _TG_USERNAME_RE.match(cleaned):
        return cleaned.lower(), "telegram"
    digits = re.sub(r"[^\d+]", "", cleaned)
    if digits:
        if not digits.startswith("+"):
            digits = "+" + digits
        return digits, "phone"
    return cleaned.lower(), "other"


# ══════════ Telegram xabar formati (5.2-bo'lim) ══════════

def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def lead_message_text(lead: Lead) -> str:
    stage_meta = crm.STAGE_BY_SLUG.get(lead.stage) or crm.STAGE_BY_SLUG[crm.DEFAULT_STAGE]
    e = html.escape
    pt_label = crm.PROJECT_TYPE_BY_SLUG.get(lead.project_type, {}).get("label") or (lead.project_type or "—")
    msg = lead.message or "—"
    if len(msg) > 400:
        msg = msg[:400] + "…"
    assigned = e(lead.assigned_to) if lead.assigned_to else "—"
    return (
        f"{stage_meta['emoji']} <b>MIJOZ #{lead.id}</b>\n\n"
        f"👤 <b>Ism Familiya:</b> {e(lead.name)}\n"
        f"📞 <b>Aloqa:</b> {e(lead.phone or '—')}\n"
        f"💼 <b>Loyiha:</b> {e(pt_label)}\n"
        f"💬 <b>Habar:</b> {e(msg)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Bosqich:</b> {stage_meta['emoji']} {e(stage_meta['label'])}\n"
        f"👨‍💼 <b>Mas'ul:</b> {assigned}\n"
        f"📅 <b>Kelgan:</b> {_fmt_dt(lead.created_at)}\n"
        f"♻️ <b>Yangilangan:</b> {_fmt_dt(lead.stage_changed_at)}"
    )


def lead_inline_keyboard(lead: Lead) -> dict:
    """Joriy bosqichdan boshqa barcha bosqichlarga o'tish tugmalari (5.3-bo'lim)."""
    buttons: list[list[dict]] = []
    row: list[dict] = []
    for s in crm.STAGES:
        if s["slug"] == lead.stage:
            continue
        row.append({"text": f"{s['emoji']} {s['label']}", "callback_data": f"crmstage:{lead.id}:{s['slug']}"})
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return {"inline_keyboard": buttons}


# ══════════ Telegram sinxronizatsiya ══════════

async def get_telegram_settings(session: AsyncSession) -> TelegramSettings:
    settings_row = await session.get(TelegramSettings, 1)
    if settings_row is None:
        settings_row = TelegramSettings(id=1)
        session.add(settings_row)
        await session.commit()
    return settings_row


async def _sync_once(bot, session: AsyncSession, tg: TelegramSettings, lead: Lead) -> bool:
    """Bir urinish. True — muvaffaqiyatli (yoki sinxronlash shart emas)."""
    if not tg.is_enabled or not tg.leads_chat_id or not bot.token:
        return True  # o'chirilgan — bu xato emas, shunchaki o'tkazib yuborish

    text = lead_message_text(lead)
    keyboard = lead_inline_keyboard(lead)

    async def _send_new() -> bool:
        body = {
            "chat_id": tg.leads_chat_id, "text": text, "parse_mode": "HTML",
            "reply_markup": keyboard, "disable_web_page_preview": True,
        }
        if tg.topic_thread_id:
            body["message_thread_id"] = tg.topic_thread_id
        data = await bot.call("sendMessage", body)
        if data.get("ok"):
            lead.tg_message_id = data["result"]["message_id"]
            lead.tg_chat_id = tg.leads_chat_id
            lead.tg_sync_state = "synced"
            lead.tg_last_error = ""
            return True
        lead.tg_sync_state = "failed"
        lead.tg_last_error = str(data.get("description", ""))[:500]
        return False

    if not lead.tg_message_id:
        ok = await _send_new()
    else:
        data = await bot.call("editMessageText", {
            "chat_id": lead.tg_chat_id or tg.leads_chat_id,
            "message_id": lead.tg_message_id,
            "text": text, "parse_mode": "HTML", "reply_markup": keyboard,
        })
        if data.get("ok"):
            lead.tg_sync_state = "synced"
            lead.tg_last_error = ""
            ok = True
        else:
            desc = str(data.get("description", ""))
            if "message is not modified" in desc:
                # Kontent aslida o'zgarmagan (masalan mas'ul o'sha, matn bir xil) — xato emas.
                lead.tg_sync_state = "synced"
                lead.tg_last_error = ""
                ok = True
            elif "message to edit" in desc or "message_id_invalid" in desc.lower() or "message can't be edited" in desc:
                # 5.4.4: xabar o'chirilgan/topilmadi -> qayta yuboramiz, baza yetakchi manba.
                ok = await _send_new()
            else:
                lead.tg_sync_state = "failed"
                lead.tg_last_error = desc[:500]
                ok = False

    await session.commit()
    return ok


async def sync_lead_to_telegram(bot, lead_id: int) -> None:
    """Fon vazifasi sifatida chaqiriladi (HTTP javobini bloklamaydi).

    3 marta qayta urinadi (1s/5s/30s kechikish bilan) — 5.4.2-bo'lim.
    Har urinishda TelegramSettings qayta o'qiladi (shu oraliqda o'zgargan
    bo'lishi mumkin)."""
    for delay in _RETRY_DELAYS:
        if delay:
            await asyncio.sleep(delay)
        async with SessionLocal() as session:
            lead = await session.get(Lead, lead_id)
            if lead is None or lead.is_archived:
                return
            tg = await get_telegram_settings(session)
            try:
                ok = await _sync_once(bot, session, tg, lead)
            except Exception as e:
                log.warning("CRM Telegram sinxron xatosi (lead #%s): %s", lead_id, e)
                ok = False
            if ok:
                return
    log.warning("CRM Telegram sinxron 3 marta muvaffaqiyatsiz: lead #%s", lead_id)


def queue_telegram_sync(bot, lead_id: int) -> None:
    """asyncio.create_task — chaqiruvchi endpoint javobni kutmasdan qaytadi."""
    asyncio.create_task(sync_lead_to_telegram(bot, lead_id))


# ══════════ bosqich almashtirish (HTTP va Telegram callback ikkalasi ham shuni chaqiradi) ══════════

async def change_stage(
    session: AsyncSession, lead: Lead, new_stage: str, changed_by: str | None
) -> LeadStageHistory:
    old_stage = lead.stage
    now = datetime.now(timezone.utc)
    duration = None
    if lead.stage_changed_at:
        # SQLite tzinfo'ni saqlamaydi (naive qaytaradi) — biz doim UTC
        # yozganimiz uchun shu deb qabul qilamiz (db.py'dagi xuddi shu naqsh).
        prev = lead.stage_changed_at
        if prev.tzinfo is None:
            prev = prev.replace(tzinfo=timezone.utc)
        duration = int((now - prev).total_seconds())
    lead.stage = new_stage
    lead.stage_changed_at = now
    history = LeadStageHistory(
        lead_id=lead.id, from_stage=old_stage, to_stage=new_stage,
        changed_by=changed_by, changed_at=now, duration_seconds=duration,
    )
    session.add(history)
    await session.commit()
    return history


# ══════════ dublikat tekshirish (8.3-bo'lim) ══════════

DUPLICATE_WINDOW_DAYS = 30


async def find_recent_duplicate(session: AsyncSession, contact_normalized: str) -> Lead | None:
    if not contact_normalized:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=DUPLICATE_WINDOW_DAYS)
    return await session.scalar(
        select(Lead)
        .where(
            Lead.contact_normalized == contact_normalized,
            Lead.is_archived.is_(False),
            Lead.created_at > cutoff,
        )
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
