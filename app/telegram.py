"""Telegram bot — arizalarni yetkazish va ular bilan ishlash.

Ikki yo'nalish:
  • Chiquvchi — yangi ariza kelganda guruhga va obuna bo'lgan adminlarga
    inline tugmali xabar yuboriladi ("✅ Javob berildi" / "↩️ Yangi").
  • Kiruvchi — long polling (getUpdates): tugma bosilishi, /start, /arizalar,
    /super (super adminni almashtirish — faqat ro'yxatdagi Telegram admin uchun).

Obunachilar DB'dagi `settings` jadvalida saqlanadi, shuning uchun bot guruhga
qo'shilishi bilan qo'lda chat ID kiritmasdan ishlay boshlaydi.

Eslatma: getUpdates'ni bir vaqtda faqat BITTA jarayon chaqira oladi (Telegram
409 Conflict qaytaradi). Bir necha uvicorn worker ishlatilsa TELEGRAM_POLLING
faqat bittasida yoqilgan bo'lsin.
"""
import asyncio
import html
import json
import logging
import re
import secrets
import time

import httpx
from sqlalchemy import func, select, update

from .auth import MAX_ADMIN_ACCOUNTS, create_admin_token, hash_password
from .config import settings
from . import crm_constants as crm
from . import crm_service
from .db import AdminAccount, Lead, SessionLocal, Setting
from .email import send_email, tg_super_code_email, tg_super_old_confirm_email

log = logging.getLogger("promtchi.tg")

API = "https://api.telegram.org/bot{token}/{method}"
SUBS_KEY = "tg_subscribers"  # JSON massiv: [chat_id, ...]
ADMINS_KEY = "tg_admin_ids"  # JSON massiv: [{"chat_id": int, "label": str}, ...]

SUPER_FLOW_TTL = 600  # soniya — /super jarayonining har bosqichi shuncha vaqt amal qiladi
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TelegramBot:
    """Bot holati va operatsiyalari. Bitta global nusxa ishlatiladi."""

    def __init__(self):
        self.token: str = ""
        self.group_chat_id: str = ""      # admin panelda ko'rsatilgan asosiy guruh
        self.subscribers: set[int] = set()  # /start bosgan yoki qo'shilgan chatlar
        self.admins: list[dict] = []      # [{"chat_id": int, "label": str}] — sezgir xabarlar shu yerga boradi
        self.super_flow: dict[int, dict] = {}  # chat_id -> /super jarayoni holati (vaqtinchalik, xotirada)
        self.admin_password: str = ""
        self.client: httpx.AsyncClient | None = None
        self.queue: asyncio.Queue | None = None
        self._poll_task: asyncio.Task | None = None
        self._offset: int = 0
        self.polling_enabled: bool = True
        self.last_error: str = ""

    # ── holat ────────────────────────────────────────────────────────────────
    @property
    def ready(self) -> bool:
        return bool(self.token and self.targets)

    @property
    def targets(self) -> list[str]:
        """Xabar yuboriladigan barcha chatlar (guruh + obunachilar)."""
        t: list[str] = []
        if self.group_chat_id:
            t.append(self.group_chat_id)
        for s in self.subscribers:
            if str(s) != self.group_chat_id:
                t.append(str(s))
        return t

    def masked_token(self) -> str:
        t = self.token
        if not t:
            return ""
        return t[:8] + "…" + t[-4:] if len(t) > 16 else "•" * len(t)

    # ── past darajali API ────────────────────────────────────────────────────
    async def call(self, method: str, payload: dict | None = None, timeout: float | None = None):
        if not self.token or self.client is None:
            return {"ok": False, "description": "Bot sozlanmagan"}
        try:
            r = await self.client.post(
                API.format(token=self.token, method=method),
                json=payload or {},
                timeout=timeout or 15.0,
            )
            data = r.json()
            if not data.get("ok"):
                self.last_error = str(data.get("description", ""))[:200]
            return data
        except Exception as e:
            self.last_error = str(e)[:200]
            return {"ok": False, "description": str(e)}

    # ── obunachilar ──────────────────────────────────────────────────────────
    async def _save_subscribers(self) -> None:
        async with SessionLocal() as s:
            await s.merge(Setting(key=SUBS_KEY, value=json.dumps(sorted(self.subscribers))))
            await s.commit()

    async def add_subscriber(self, chat_id: int) -> bool:
        if chat_id in self.subscribers:
            return False
        self.subscribers.add(chat_id)
        await self._save_subscribers()
        log.info("Telegram: yangi obunachi %s (jami %s)", chat_id, len(self.subscribers))
        return True

    async def remove_subscriber(self, chat_id: int) -> bool:
        if chat_id not in self.subscribers:
            return False
        self.subscribers.discard(chat_id)
        await self._save_subscribers()
        return True

    # ── Telegram adminlar (sezgir xabarnomalar — parol, kirish urinishi va h.k.) ──
    @property
    def admin_chat_ids(self) -> list[str]:
        return [str(a["chat_id"]) for a in self.admins]

    async def _save_admins(self) -> None:
        async with SessionLocal() as s:
            await s.merge(Setting(key=ADMINS_KEY, value=json.dumps(self.admins)))
            await s.commit()

    async def add_admin(self, chat_id: int, label: str = "") -> bool:
        if any(a["chat_id"] == chat_id for a in self.admins):
            return False
        self.admins.append({"chat_id": chat_id, "label": label.strip()})
        await self._save_admins()
        return True

    async def remove_admin(self, chat_id: int) -> bool:
        before = len(self.admins)
        self.admins = [a for a in self.admins if a["chat_id"] != chat_id]
        if len(self.admins) == before:
            return False
        await self._save_admins()
        return True

    # ── ariza xabari ─────────────────────────────────────────────────────────
    @staticmethod
    def lead_text(lead_id: int, name: str, phone: str, ptype: str, message: str, status: str) -> str:
        e = html.escape
        head = "🔥 <b>Yangi ariza — promtchi.uz</b>" if status != "replied" else "✅ <b>Ariza — javob berilgan</b>"
        return (
            f"{head}\n\n"
            f"🆔 <b>Ariza:</b> #{lead_id}\n"
            f"👤 <b>Ism:</b> {e(name)}\n"
            f"📞 <b>Aloqa:</b> {e(phone or '—')}\n"
            f"📦 <b>Loyiha:</b> {e(ptype or '—')}\n"
            f"💬 <b>Xabar:</b> {e(message or '—')}"
        )

    @staticmethod
    def lead_keyboard(lead_id: int, status: str) -> dict:
        if status == "replied":
            btn = {"text": "↩️ Yangi deb belgilash", "callback_data": f"lead:{lead_id}:new"}
        else:
            btn = {"text": "✅ Javob berildi", "callback_data": f"lead:{lead_id}:replied"}
        return {"inline_keyboard": [[btn]]}

    def queue_lead(self, lead: Lead) -> None:
        """Arizani navbatga qo'yadi (bloklamaydi)."""
        if self.queue is None or not self.ready:
            return
        payload = {
            "lead_id": lead.id,
            "text": self.lead_text(lead.id, lead.name, lead.phone, lead.project_type, lead.message, "new"),
            "keyboard": self.lead_keyboard(lead.id, "new"),
        }
        try:
            self.queue.put_nowait(payload)
        except asyncio.QueueFull:
            log.warning("Telegram navbati to'la — xabarnoma tashlandi (ariza saqlandi)")

    def queue_text(self, text: str) -> None:
        """Ixtiyoriy matnli xabarni navbatga qo'yadi (tugmasiz) — guruh + barcha
        obunachilarga (ommaviy)."""
        if self.queue is None or not self.ready:
            return
        try:
            self.queue.put_nowait({"lead_id": None, "text": text, "keyboard": None, "targets": None})
        except asyncio.QueueFull:
            log.warning("Telegram navbati to'la — xabar tashlandi")

    def queue_text_admins(self, text: str) -> None:
        """Sezgir xabarnoma (parol, kirish urinishi, hisob o'zgarishi) — FAQAT
        Telegram admin sifatida belgilangan chatlarga boradi (guruhga emas).
        Hali hech qanday Telegram admin sozlanmagan bo'lsa — eski xatti-harakat
        (barcha ulangan chatlarga) saqlanib qoladi, xabarnoma yo'qolib qolmasin."""
        if self.queue is None or not self.token:
            return
        targets = self.admin_chat_ids
        if not targets and not self.ready:
            return
        try:
            self.queue.put_nowait({"lead_id": None, "text": text, "keyboard": None, "targets": targets or None})
        except asyncio.QueueFull:
            log.warning("Telegram navbati to'la — admin xabari tashlandi")

    async def worker(self, worker_id: int) -> None:
        """Navbatdagi xabarlarni barcha chatlarga yuboradi."""
        assert self.queue is not None
        while True:
            item = await self.queue.get()
            try:
                delivered = False
                chats = item.get("targets") or self.targets
                for chat in chats:
                    body = {"chat_id": chat, "text": item["text"], "parse_mode": "HTML"}
                    if item.get("keyboard"):
                        body["reply_markup"] = item["keyboard"]
                    data = await self.call("sendMessage", body)
                    if data.get("ok"):
                        delivered = True
                    else:
                        log.warning(
                            "Telegram yuborilmadi (chat=%s): %s", chat, data.get("description")
                        )
                if delivered and item.get("lead_id"):
                    async with SessionLocal() as s:
                        await s.execute(
                            update(Lead).where(Lead.id == item["lead_id"]).values(tg_sent=True)
                        )
                        await s.commit()
            except Exception as e:
                log.warning("Telegram worker %s xatosi: %s", worker_id, e)
            finally:
                self.queue.task_done()
            await asyncio.sleep(1 / 15)  # Telegram ~30 xabar/sekund

    # ── kiruvchi (long polling) ──────────────────────────────────────────────
    async def ensure_no_webhook(self) -> None:
        """Webhook o'rnatilgan bo'lsa o'chiradi.

        Webhook faol bo'lsa getUpdates "Conflict" qaytaradi va bot tugmalari
        ishlamaydi — biz long polling ishlatamiz, shuning uchun webhook keraksiz.
        """
        if not self.token:
            return
        info = await self.call("getWebhookInfo")
        if info.get("ok") and info["result"].get("url"):
            url = info["result"]["url"]
            res = await self.call("deleteWebhook", {"drop_pending_updates": False})
            log.info("Telegram webhook o'chirildi (%s): ok=%s", url, res.get("ok"))

    async def poll_loop(self) -> None:
        backoff = 1
        await self.ensure_no_webhook()
        while True:
            if not self.token or not self.polling_enabled:
                await asyncio.sleep(5)
                continue
            try:
                data = await self.call(
                    "getUpdates",
                    {"offset": self._offset, "timeout": 25, "allowed_updates": ["message", "callback_query", "my_chat_member"]},
                    timeout=35.0,
                )
                if not data.get("ok"):
                    desc = str(data.get("description", ""))
                    if "webhook is active" in desc:
                        # Webhook qaytadan o'rnatilgan — o'chirib, davom etamiz
                        await self.ensure_no_webhook()
                        await asyncio.sleep(1)
                        continue
                    if "Conflict" in desc:
                        log.warning("Telegram polling to'xtatildi — boshqa jarayon getUpdates chaqiryapti")
                        self.polling_enabled = False
                        continue
                    if "Unauthorized" in desc:
                        log.warning("Telegram token noto'g'ri — polling pauza")
                        await asyncio.sleep(30)
                        continue
                    await asyncio.sleep(min(backoff, 30))
                    backoff = min(backoff * 2, 30)
                    continue
                backoff = 1
                for upd in data.get("result", []):
                    self._offset = upd["update_id"] + 1
                    try:
                        await self._handle_update(upd)
                    except Exception as e:
                        log.warning("Telegram update ishlanmadi: %s", e)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("Telegram polling xatosi: %s", e)
                await asyncio.sleep(min(backoff, 30))
                backoff = min(backoff * 2, 30)

    async def _handle_update(self, upd: dict) -> None:
        # 1) Tugma bosilishi
        if "callback_query" in upd:
            return await self._handle_callback(upd["callback_query"])

        # 2) Bot guruhga qo'shildi / chiqarildi
        if "my_chat_member" in upd:
            m = upd["my_chat_member"]
            status = m.get("new_chat_member", {}).get("status")
            chat = m["chat"]
            if status in ("member", "administrator"):
                if await self.add_subscriber(chat["id"]):
                    await self.call("sendMessage", {
                        "chat_id": chat["id"],
                        "text": ("✅ <b>promtchi bot ulandi!</b>\n\nEndi yangi arizalar shu yerga tushadi.\n"
                                 f"Chat ID: <code>{chat['id']}</code>"),
                        "parse_mode": "HTML",
                    })
            elif status in ("left", "kicked"):
                await self.remove_subscriber(chat["id"])
            return

        # 3) Matnli xabar
        msg = upd.get("message")
        if not msg:
            return
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        if text.startswith("/cancel"):
            if chat_id in self.super_flow:
                del self.super_flow[chat_id]
                await self.call("sendMessage", {"chat_id": chat_id, "text": "❌ Bekor qilindi."})
            return

        if text.startswith("/super") or text.startswith("/supper"):
            await self._super_start(chat_id)
            return

        # Faol /super jarayoni bo'lsa — matnni shu jarayonga yo'naltiramiz
        # (boshqa buyruqlardan OLDIN, chunki oddiy email/kod matni bo'ladi)
        if chat_id in self.super_flow:
            await self._super_handle_text(chat_id, text)
            return

        if text.startswith("/start"):
            await self.add_subscriber(chat_id)
            await self.call("sendMessage", {
                "chat_id": chat_id,
                "text": (
                    "👋 <b>promtchi® admin bot</b>\n\n"
                    "Bu chat ro'yxatga olindi — yangi arizalar shu yerga tushadi.\n\n"
                    f"🆔 Chat ID: <code>{chat_id}</code>\n\n"
                    "<b>Buyruqlar:</b>\n"
                    "/arizalar — oxirgi arizalar\n"
                    "/yangi — javob kutayotgan arizalar\n"
                    "/stop — xabarnomalarni o'chirish"
                ),
                "parse_mode": "HTML",
            })
            return

        if text.startswith("/stop"):
            await self.remove_subscriber(chat_id)
            await self.call("sendMessage", {
                "chat_id": chat_id, "text": "🔕 Xabarnomalar o'chirildi. Qayta yoqish: /start"})
            return

        if text.startswith("/arizalar") or text.startswith("/yangi"):
            only_new = text.startswith("/yangi")
            async with SessionLocal() as s:
                q = select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc()).limit(10)
                if only_new:
                    q = q.where(Lead.status == "new")
                res = await s.execute(q)
                leads = res.scalars().all()
            if not leads:
                await self.call("sendMessage", {
                    "chat_id": chat_id,
                    "text": "Javob kutayotgan ariza yo'q ✅" if only_new else "Hali arizalar yo'q."})
                return
            for l in leads[:10]:
                await self.call("sendMessage", {
                    "chat_id": chat_id,
                    "text": self.lead_text(l.id, l.name, l.phone, l.project_type, l.message, l.status),
                    "parse_mode": "HTML",
                    "reply_markup": self.lead_keyboard(l.id, l.status),
                })
                await asyncio.sleep(0.08)
            return

    async def _handle_callback(self, cq: dict) -> None:
        data = cq.get("data", "")
        cq_id = cq["id"]
        if data.startswith("super:"):
            return await self._handle_super_callback(cq)
        if data.startswith("crmstage:"):
            return await self._handle_crmstage_callback(cq)
        parts = data.split(":")
        if len(parts) != 3 or parts[0] != "lead":
            await self.call("answerCallbackQuery", {"callback_query_id": cq_id})
            return
        try:
            lead_id = int(parts[1])
        except ValueError:
            await self.call("answerCallbackQuery", {"callback_query_id": cq_id})
            return
        new_status = "replied" if parts[2] == "replied" else "new"

        async with SessionLocal() as s:
            lead = await s.get(Lead, lead_id)
            if lead is None:
                await self.call("answerCallbackQuery", {
                    "callback_query_id": cq_id, "text": "Ariza topilmadi (o'chirilgan)", "show_alert": True})
                return
            lead.status = new_status
            await s.commit()
            text = self.lead_text(lead.id, lead.name, lead.phone, lead.project_type, lead.message, new_status)

        who = cq.get("from", {})
        who_name = who.get("first_name") or who.get("username") or "admin"
        suffix = f"\n\n<i>{'✅ Javob berildi' if new_status == 'replied' else '↩️ Yangi deb belgilandi'} — {html.escape(who_name)}</i>"

        msg = cq.get("message") or {}
        if msg:
            await self.call("editMessageText", {
                "chat_id": msg["chat"]["id"],
                "message_id": msg["message_id"],
                "text": text + suffix,
                "parse_mode": "HTML",
                "reply_markup": self.lead_keyboard(lead_id, new_status),
            })
        await self.call("answerCallbackQuery", {
            "callback_query_id": cq_id,
            "text": "✅ Javob berildi deb belgilandi" if new_status == "replied" else "↩️ Yangi deb belgilandi",
        })

    async def _handle_crmstage_callback(self, cq: dict) -> None:
        """CRM Kanban inline tugmasi: crmstage:{lead_id}:{stage_slug}.

        Telegram -> sayt yo'nalishi (5.3-bo'lim): guruhda tugma bosilsa Kanban
        ham darhol yangilanadi. `changed_by=None` — Telegram bosuvchisi
        AdminAccount emailiga bog'lanmagan (faqat toast'da ismi ko'rsatiladi)."""
        cq_id = cq["id"]
        parts = cq.get("data", "").split(":")
        if len(parts) != 3:
            await self.call("answerCallbackQuery", {"callback_query_id": cq_id})
            return
        try:
            lead_id = int(parts[1])
        except ValueError:
            await self.call("answerCallbackQuery", {"callback_query_id": cq_id})
            return
        new_stage = parts[2]
        if new_stage not in crm.STAGE_SLUGS:
            await self.call("answerCallbackQuery", {
                "callback_query_id": cq_id, "text": "Noto'g'ri bosqich", "show_alert": True})
            return

        who = cq.get("from", {})
        who_name = who.get("first_name") or who.get("username") or "Telegram"

        async with SessionLocal() as s:
            lead = await s.get(Lead, lead_id)
            if lead is None:
                await self.call("answerCallbackQuery", {
                    "callback_query_id": cq_id,
                    "text": "Mijoz topilmadi (arxivlangan/o'chirilgan)", "show_alert": True,
                })
                return
            await crm_service.change_stage(s, lead, new_stage, changed_by=None)
            text = crm_service.lead_message_text(lead)
            keyboard = crm_service.lead_inline_keyboard(lead)

        msg = cq.get("message") or {}
        if msg:
            await self.call("editMessageText", {
                "chat_id": msg["chat"]["id"],
                "message_id": msg["message_id"],
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": keyboard,
            })
        stage_label = crm.STAGE_BY_SLUG[new_stage]["label"]
        await self.call("answerCallbackQuery", {
            "callback_query_id": cq_id,
            "text": f"✅ {stage_label} deb belgilandi — {who_name}",
        })

    # ── /super — Telegram orqali super adminni almashtirish ────────────────────
    # Faqat ro'yxatdagi Telegram admin(lar) uchun. Bosqichlar:
    #   1) /super yoki /supper -> hozirgi super admin emailini so'raydi
    #   2) email to'g'ri kelsa -> shu emailga tasdiqlash havolasi yuboriladi
    #   3) havola bosilgach (tg-super-confirm.html) -> yangi email so'raladi
    #   4) yangi emailga 6 xonali kod yuboriladi -> kod kiritiladi
    #   5) tugmalar orqali tanlanadi: mavjud hisobni Super qilish YOKI yangi
    #      Super Admin sifatida qo'shish (parol avtomatik yaratilib shu yerga yuboriladi)
    async def _super_start(self, chat_id: int) -> None:
        if chat_id not in [a["chat_id"] for a in self.admins]:
            await self.call("sendMessage", {
                "chat_id": chat_id,
                "text": "⛔ Bu buyruq faqat ro'yxatdan o'tgan Telegram admin uchun mavjud.",
            })
            return
        self.super_flow[chat_id] = {"step": "await_old_email", "expires": time.time() + SUPER_FLOW_TTL}
        await self.call("sendMessage", {
            "chat_id": chat_id,
            "text": (
                "🔐 <b>Super adminni almashtirish</b>\n\n"
                "Hozirgi SUPER ADMIN emailini kiriting (tasdiqlash uchun).\nBekor qilish: /cancel"
            ),
            "parse_mode": "HTML",
        })

    async def _super_handle_text(self, chat_id: int, text: str) -> None:
        flow = self.super_flow.get(chat_id)
        if flow is None:
            return
        if time.time() > flow["expires"]:
            del self.super_flow[chat_id]
            await self.call("sendMessage", {"chat_id": chat_id, "text": "⏱ Vaqt tugadi. Qaytadan boshlash uchun /super yozing."})
            return

        step = flow["step"]

        if step == "await_old_email":
            email = text.strip().lower()
            async with SessionLocal() as s:
                primary = await s.scalar(select(AdminAccount).where(AdminAccount.is_primary.is_(True)))
            if primary is None or primary.email != email:
                await self.call("sendMessage", {"chat_id": chat_id, "text": "❌ Email noto'g'ri. Qaytadan kiriting yoki /cancel."})
                return
            async with SessionLocal() as s:
                token = await create_admin_token(s, "tg_super_old", payload=str(chat_id))
            url = f"{settings.SITE_URL}/tg-super-confirm.html?token={token}"
            await send_email(email, "promtchi — Super adminni almashtirish", tg_super_old_confirm_email(url))
            flow["step"] = "await_old_confirm"
            flow["expires"] = time.time() + SUPER_FLOW_TTL
            await self.call("sendMessage", {
                "chat_id": chat_id,
                "text": "📧 Tasdiqlash havolasi hozirgi super adminning emailiga yuborildi. U tasdiqlagach shu yerga xabar keladi.",
            })
            return

        if step == "await_old_confirm":
            await self.call("sendMessage", {"chat_id": chat_id, "text": "⏳ Hali eski super admin tasdiqlamadi. Kuting yoki /cancel."})
            return

        if step == "await_new_email":
            new_email = text.strip().lower()
            if not _EMAIL_RE.match(new_email):
                await self.call("sendMessage", {"chat_id": chat_id, "text": "❌ Email formati noto'g'ri. Qaytadan kiriting."})
                return
            code = f"{secrets.randbelow(1_000_000):06d}"
            flow["new_email"] = new_email
            flow["code"] = code
            flow["step"] = "await_code"
            flow["expires"] = time.time() + SUPER_FLOW_TTL
            await send_email(new_email, "promtchi — tasdiqlash kodi", tg_super_code_email(code))
            await self.call("sendMessage", {
                "chat_id": chat_id,
                "text": f"📧 Tasdiqlash kodi {new_email} manziliga yuborildi. Kodni shu yerga kiriting:",
            })
            return

        if step == "await_code":
            if text.strip() != flow.get("code"):
                await self.call("sendMessage", {"chat_id": chat_id, "text": "❌ Kod noto'g'ri. Qaytadan kiriting yoki /cancel."})
                return
            new_email = flow["new_email"]
            async with SessionLocal() as s:
                existing = await s.get(AdminAccount, new_email)
            if existing is not None and existing.is_primary:
                await self.call("sendMessage", {"chat_id": chat_id, "text": "ℹ️ Bu hisob allaqachon super admin."})
                del self.super_flow[chat_id]
                return
            if existing is not None:
                buttons = [[{"text": "🔄 Mavjud hisobni Super qilish", "callback_data": "super:promote"}]]
            else:
                buttons = [[{"text": "➕ Yangi Super Admin sifatida qo'shish", "callback_data": "super:create"}]]
            flow["step"] = "await_choice"
            flow["expires"] = time.time() + SUPER_FLOW_TTL
            await self.call("sendMessage", {
                "chat_id": chat_id,
                "text": f"✅ Kod to'g'ri. <b>{html.escape(new_email)}</b> uchun amalni tanlang:",
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": buttons},
            })
            return

        if step == "await_choice":
            await self.call("sendMessage", {"chat_id": chat_id, "text": "Iltimos, yuqoridagi tugmalardan birini bosing yoki /cancel."})
            return

    async def advance_super_flow_after_old_confirm(self, chat_id: int) -> bool:
        """Eski super admin emaildagi havolani bosgach chaqiriladi (main.py'dan)."""
        flow = self.super_flow.get(chat_id)
        if flow is None or flow.get("step") != "await_old_confirm":
            return False
        flow["step"] = "await_new_email"
        flow["expires"] = time.time() + SUPER_FLOW_TTL
        await self.call("sendMessage", {
            "chat_id": chat_id,
            "text": "✅ Tasdiqlandi! Endi yangi SUPER ADMIN qilinadigan emailni kiriting:",
        })
        return True

    async def _handle_super_callback(self, cq: dict) -> None:
        cq_id = cq["id"]
        chat_id = cq["message"]["chat"]["id"]
        action = cq["data"].split(":", 1)[1]
        flow = self.super_flow.get(chat_id)
        if flow is None or flow.get("step") != "await_choice":
            await self.call("answerCallbackQuery", {
                "callback_query_id": cq_id, "text": "Jarayon topilmadi yoki eskirgan.", "show_alert": True})
            return
        new_email = flow["new_email"]
        result_msg = ""
        async with SessionLocal() as s:
            old_primary = await s.scalar(select(AdminAccount).where(AdminAccount.is_primary.is_(True)))
            if action == "promote":
                target = await s.get(AdminAccount, new_email)
                if target is None:
                    await self.call("answerCallbackQuery", {
                        "callback_query_id": cq_id, "text": "Hisob topilmadi", "show_alert": True})
                    return
                if old_primary:
                    old_primary.is_primary = False
                target.is_primary = True
                await s.commit()
                result_msg = f"👑 <b>Super Admin almashtirildi</b>\nYangi: {html.escape(new_email)}"
            elif action == "create":
                existing = await s.get(AdminAccount, new_email)
                if existing is not None:
                    await self.call("answerCallbackQuery", {
                        "callback_query_id": cq_id, "text": "Bu email allaqachon mavjud", "show_alert": True})
                    return
                count = await s.scalar(select(func.count()).select_from(AdminAccount))
                if count and count >= MAX_ADMIN_ACCOUNTS:
                    await self.call("answerCallbackQuery", {
                        "callback_query_id": cq_id, "text": "Hisoblar chegarasiga yetgan", "show_alert": True})
                    del self.super_flow[chat_id]
                    return
                password = secrets.token_urlsafe(9)
                if old_primary:
                    old_primary.is_primary = False
                s.add(AdminAccount(email=new_email, password_hash=hash_password(password), is_primary=True))
                await s.commit()
                result_msg = (
                    "👑 <b>Yangi Super Admin qo'shildi</b>\n"
                    f"Email: <code>{html.escape(new_email)}</code>\nParol: <code>{html.escape(password)}</code>"
                )
            else:
                await self.call("answerCallbackQuery", {"callback_query_id": cq_id})
                return
        del self.super_flow[chat_id]
        await self.call("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Bajarildi ✓"})
        await self.call("sendMessage", {"chat_id": chat_id, "text": result_msg, "parse_mode": "HTML"})

    # ── ishga tushirish / to'xtatish ─────────────────────────────────────────
    async def notify_lead_status(self, lead_id: int, status: str) -> None:
        """Admin panelda status o'zgarganda guruhga xabar beradi."""
        if not self.ready:
            return
        self.queue_text(
            f"{'✅' if status == 'replied' else '↩️'} Ariza <b>#{lead_id}</b> — "
            f"{'javob berilgan' if status == 'replied' else 'yangi'} deb belgilandi "
            "<i>(admin panel)</i>"
        )

    async def load_settings(self, conn) -> None:
        """DB'dan token, guruh va obunachilarni o'qiydi."""
        res = await conn.execute(
            select(Setting.key, Setting.value).where(
                Setting.key.in_(["tg_bot_token", "tg_chat_id", SUBS_KEY, ADMINS_KEY])
            )
        )
        stored = dict(res.all())
        if "tg_bot_token" in stored:
            self.token = stored["tg_bot_token"].strip()
        if "tg_chat_id" in stored:
            self.group_chat_id = stored["tg_chat_id"].strip()
        try:
            self.subscribers = set(json.loads(stored.get(SUBS_KEY, "[]")))
        except Exception:
            self.subscribers = set()
        try:
            self.admins = list(json.loads(stored.get(ADMINS_KEY, "[]")))
        except Exception:
            self.admins = []


bot = TelegramBot()
