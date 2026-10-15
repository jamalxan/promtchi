"""IndexNow — qidiruv tizimlariga URL o'zgarganini DARHOL bildirish.

Nega kerak: Google sitemap'ni o'zi qayta o'qib turadi, lekin Bing va Yandex
(O'zbekistonda muhim) yangi/o'zgargan sahifani haftalab topmasligi mumkin —
2026-09 tekshiruvida Bing'da faqat bosh sahifa indekslangan edi. IndexNow
(https://www.indexnow.org) bitta POST bilan Bing, Yandex, Seznam, Naver va
Yep'ga URL ro'yxatini yuboradi — ular o'zaro ulashadi, shuning uchun bitta
endpoint (api.indexnow.org) yetarli. Google IndexNow'ni QO'LLAMAYDI —
u uchun sitemap + Search Console qoladi.

Ishlash tartibi:
- Kalit `settings.INDEXNOW_KEY` (.env); u `https://host/{key}.txt` manzilida
  ochiq turishi SHART — qidiruv tizimi egalikni shu fayl orqali tekshiradi
  (app/pages.py `indexnow_key_file`).
- Admin biror kontentni saqlasa/o'chirsa `notify([...yo'llar])` chaqiriladi:
  yo'llar to'planadi va bir necha soniyadan keyin BITTA so'rov bilan
  yuboriladi (tahrirlash paytida har tugma bosilganda alohida so'rov
  ketmasin). O'chirilgan URL ham yuboriladi — IndexNow uni "qayta tekshir"
  deb tushunadi va 404/410 ko'rib indeksdan chiqaradi.
- `full_submit()` — sitemap'dagi BARCHA URL'larni yuboradi; dastlabki
  yoqishda va har 7 kunda bir (lifespan) — ko'proq emas, IndexNow bir xil
  URL'ni takror yuborishni spam deb hisoblashi mumkin.
- Hech qachon exception ko'tarmaydi: IndexNow ishlamasa sayt ishlashi
  to'xtamasligi kerak; natija faqat logga yoziladi.
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx

from .config import settings

log = logging.getLogger("promtchi.indexnow")

ENDPOINT = "https://api.indexnow.org/IndexNow"
# IndexNow protokoli: bitta so'rovda eng ko'pi 10 000 URL
MAX_PER_REQUEST = 10_000
# Admin tahriri paytida yig'ilgan yo'llar shuncha soniyadan keyin yuboriladi
DEBOUNCE_SECONDS = 5.0
# To'liq (sitemap) yuborish oralig'i — Setting jadvalida `indexnow_full_at`
FULL_SUBMIT_INTERVAL_SECONDS = 7 * 24 * 3600

# main.lifespan beradi (umumiy httpx klient); testlarda monkeypatch qilinadi
client: httpx.AsyncClient | None = None

_pending: set[str] = set()
_flush_task: asyncio.Task | None = None
# Oxirgi natija — admin panel/diagnostika uchun
last_result: dict = {"at": None, "status": None, "count": 0, "ok": None}

_REJECT_REASON = {
    400: "format",
    403: "kalit fayli topilmadi/mos emas",
    422: "URL host'ga mos emas",
    429: "juda ko'p so'rov",
}


def key() -> str:
    return settings.INDEXNOW_KEY


def enabled() -> bool:
    return bool(key()) and client is not None


def key_location() -> str:
    return f"{settings.SITE_URL}/{key()}.txt"


def _abs(path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return settings.SITE_URL.rstrip("/") + "/" + path_or_url.lstrip("/")


async def submit(urls) -> bool:
    """URL ro'yxatini yuboradi. 200/202 — qabul qilindi. Hech qachon ko'tarmaydi."""
    urls = sorted({_abs(u) for u in urls if u})
    if not urls:
        return True
    if not enabled():
        log.debug("IndexNow o'chiq (kalit yo'q yoki klient yo'q) — %d URL yuborilmadi", len(urls))
        return False
    host = settings.CANONICAL_HOST
    ok = True
    for i in range(0, len(urls), MAX_PER_REQUEST):
        chunk = urls[i:i + MAX_PER_REQUEST]
        body = {"host": host, "key": key(), "keyLocation": key_location(), "urlList": chunk}
        status: int | None = None
        try:
            r = await client.post(ENDPOINT, json=body,
                                  headers={"Content-Type": "application/json; charset=utf-8"})
            status = r.status_code
        except Exception as e:  # noqa: BLE001 — tarmoq xatosi saytni to'xtatmasin
            log.warning("IndexNow so'rov xatosi: %s", e)
        accepted = status in (200, 202)
        ok = ok and accepted
        last_result.update(at=time.time(), status=status, count=len(chunk), ok=accepted)
        if accepted:
            log.info("IndexNow: %d URL qabul qilindi (HTTP %s)", len(chunk), status)
        else:
            log.warning("IndexNow rad etdi: HTTP %s (%d URL) — %s", status, len(chunk),
                        _REJECT_REASON.get(status, ""))
    return ok


async def _flush_later() -> None:
    try:
        await asyncio.sleep(DEBOUNCE_SECONDS)
    except asyncio.CancelledError:
        return
    batch = set(_pending)
    _pending.clear()
    await submit(batch)


def notify(paths) -> None:
    """Kontent o'zgarganda chaqiriladi (fire-and-forget, debounced).

    Kalit sozlanmagan bo'lsa hech narsa qilmaydi — dev/test muhitida
    tasodifan localhost URL'lari yuborilmasin."""
    global _flush_task
    if not enabled():
        return
    for p in paths:
        if p:
            _pending.add(_abs(p))
    if not _pending:
        return
    if _flush_task is not None and not _flush_task.done():
        _flush_task.cancel()
    try:
        _flush_task = asyncio.get_running_loop().create_task(_flush_later())
    except RuntimeError:
        # event loop yo'q (sinxron kontekst) — keyingi notify/flush_now'da ketadi
        _flush_task = None


async def flush_now() -> bool:
    """Testlar/diagnostika uchun: kutmasdan yig'ilganlarni yuboradi."""
    global _flush_task
    if _flush_task is not None and not _flush_task.done():
        _flush_task.cancel()
    _flush_task = None
    batch = set(_pending)
    _pending.clear()
    return await submit(batch)


async def full_submit() -> tuple[bool, int]:
    """Sitemap'dagi barcha indekslanadigan URL'larni yuboradi. (ok, soni)."""
    from . import pages  # ciklik importdan qochish — pages indexnow'ni bilmaydi

    urls = await pages.all_indexable_urls()
    return await submit(urls), len(urls)


async def full_submit_if_due() -> None:
    """Lifespan'da: oxirgi to'liq yuborish 7 kundan eski (yoki hech bo'lmagan)
    bo'lsa — yuboradi va vaqtni Setting'ga yozadi. Xato bo'lsa jim o'tadi."""
    if not enabled():
        return
    from .db import SessionLocal, Setting

    try:
        async with SessionLocal() as s:
            row = await s.get(Setting, "indexnow_full_at")
            last = float(row.value) if row and row.value else 0.0
            if time.time() - last < FULL_SUBMIT_INTERVAL_SECONDS:
                return
            ok, n = await full_submit()
            if ok:
                if row is None:
                    s.add(Setting(key="indexnow_full_at", value=str(time.time())))
                else:
                    row.value = str(time.time())
                await s.commit()
                log.info("IndexNow: to'liq sitemap yuborildi (%d URL)", n)
    except Exception as e:  # noqa: BLE001
        log.warning("IndexNow to'liq yuborish o'tkazib yuborildi: %s", e)
