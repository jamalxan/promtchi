"""Telegram bot — arizalarni yetkazish va ular bilan ishlash.

Ikki yo'nalish:
  • Chiquvchi — yangi ariza kelganda guruhga va obuna bo'lgan adminlarga
    inline tugmali xabar yuboriladi ("✅ Javob berildi" / "↩️ Yangi").
  • Kiruvchi — long polling (getUpdates): tugma bosilishi, /start, /arizalar.

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

import httpx
from sqlalchemy import select, update

from .db import Lead, SessionLocal, Setting

log = logging.getLogger("promtchi.tg")

API = "https://api.telegram.org/bot{token}/{method}"
SUBS_KEY = "tg_subscribers"  # JSON massiv: [chat_id, ...]


class TelegramBot:
    """Bot holati va operatsiyalari. Bitta global nusxa ishlatiladi."""

    def __init__(self):
        self.token: str = ""
        self.group_chat_id: str = ""      # admin panelda ko'rsatilgan asosiy guruh
        self.subscribers: set[int] = set()  # /start bosgan yoki qo'shilgan chatlar
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
        """Ixtiyoriy matnli xabarni navbatga qo'yadi (tugmasiz)."""
        if self.queue is None or not self.ready:
            return
        try:
            self.queue.put_nowait({"lead_id": None, "text": text, "keyboard": None})
        except asyncio.QueueFull:
            log.warning("Telegram navbati to'la — xabar tashlandi")

    async def worker(self, worker_id: int) -> None:
        """Navbatdagi xabarlarni barcha chatlarga yuboradi."""
        assert self.queue is not None
        while True:
            item = await self.queue.get()
            try:
                delivered = False
                for chat in self.targets:
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
                Setting.key.in_(["tg_bot_token", "tg_chat_id", SUBS_KEY])
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


bot = TelegramBot()
