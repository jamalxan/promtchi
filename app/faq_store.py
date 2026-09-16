"""To'liq FAQ (/{lang}/faq/) — admin-tahrirlanadigan DB CRUD (TZ 19-bo'lim).

Ilgari app/content/faq.py ichida qattiq yozilgan 24 ta (savol, javob) juftligi
edi; endi DB (FaqItem, app/db.py) yagona manba — app/services_store.py bilan
bir xil naqsh (bir martalik seed_if_empty, xotira keshi, invalidate() admin
CRUD'da chaqiriladi).

Bosh sahifadagi qisqa "Savol-javob" bo'limi (Content.data.faq, 3 ta) bundan
ALOHIDA qoladi — TZ 4.8: "Savol-javoblar homepage'da qisqa ko'rinishi va
/faq/ sahifasida to'liq ko'rinishi mumkin" — ikkalasi ham to'g'ri, faqat
maqsadi farqli (teaser vs to'liq ro'yxat).
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .content.faq import FAQ as SEED_FAQ
from .db import FaqItem, SessionLocal

# Har savolning qaysi xizmatga tegishli ekani — mavjud savol matnining o'zidan
# ko'rinib turibdi (yangi fakt emas, faqat mavjud kontentni tasniflash,
# TZ 14-bo'lim: "Category yoki service bilan bog'lash"). Ro'yxatga kiritilmagan
# indekslar — umumiy (kompaniya darajasidagi) savollar, service_key="".
_SEED_SERVICE_KEY = {
    4: "web", 5: "web", 7: "web", 8: "web",
    6: "mobile",
    9: "ai", 10: "ai", 11: "ai", 12: "ai",
    13: "telegram-bot",
    14: "crm", 16: "crm",
    15: "erp",
}
_SEED_CATEGORY = {
    "web": "Web", "mobile": "Mobil ilova", "ai": "AI",
    "telegram-bot": "Telegram bot", "crm": "CRM", "erp": "ERP",
}
# Bosh sahifadagi qisqa "Savol-javob" bo'limida ilgari alohida Content.data.faq
# (3 ta) sifatida saqlanardi — endi shu 3 tasi shu yerda show_on_home=True
# bilan belgilanadi (TZ 14: "Home'da ko'rsatish/ko'rsatmaslik"), ikkinchi
# parallel manba yo'q.
_SEED_SHOW_ON_HOME = {19, 21, 22}


class _Cache:
    __slots__ = ("items",)

    def __init__(self):
        self.items: list[dict] | None = None


_cache = _Cache()


def invalidate() -> None:
    _cache.items = None


async def seed_if_empty(session: AsyncSession) -> None:
    """Jadval bo'sh bo'lsa app/content/faq.py'dagi haqiqiy, tasdiqlangan
    24 ta savol-javobdan bir martalik to'ldiradi."""
    n = await session.scalar(select(func.count()).select_from(FaqItem))
    if n:
        return
    uz, ru, en = SEED_FAQ["uz"], SEED_FAQ["ru"], SEED_FAQ["en"]
    for i in range(len(uz)):
        service_key = _SEED_SERVICE_KEY.get(i, "")
        session.add(FaqItem(
            key=f"q{i + 1:02d}", order=i, published=True,
            category=_SEED_CATEGORY.get(service_key, "Umumiy"),
            service_key=service_key,
            show_on_home=i in _SEED_SHOW_ON_HOME,
            question_uz=uz[i][0], answer_uz=uz[i][1],
            question_ru=ru[i][0], answer_ru=ru[i][1],
            question_en=en[i][0], answer_en=en[i][1],
        ))
    await session.commit()


async def get_items(lang: str, published_only: bool = True, home_only: bool = False,
                     service_key: str | None = None) -> list[dict]:
    if _cache.items is None:
        async with SessionLocal() as session:
            res = await session.execute(select(FaqItem).order_by(FaqItem.order, FaqItem.id))
            _cache.items = [f.as_dict() for f in res.scalars().all()]
    items = _cache.items
    if published_only:
        items = [f for f in items if f["published"]]
    if home_only:
        items = [f for f in items if f["show_on_home"]]
    if service_key is not None:
        items = [f for f in items if f["service_key"] == service_key]
    return [f[lang] for f in items]


async def get_all() -> list[dict]:
    if _cache.items is None:
        async with SessionLocal() as session:
            res = await session.execute(select(FaqItem).order_by(FaqItem.order, FaqItem.id))
            _cache.items = [f.as_dict() for f in res.scalars().all()]
    return list(_cache.items)
