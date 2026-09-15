"""Xizmatlar va Portfolio — admin-tahrirlanadigan DB CRUD (TZ 4/19-bo'lim).

Ilgari app/content/services.py va portfolio.py ichida qattiq yozilgan
Python dict edi; endi DB (Service/PortfolioCase, app/db.py) yagona manba.
Bu ikki fayl faqat BIR MARTALIK urug'lash (seed_if_empty) uchun import
qilinadi — jadval bo'sh bo'lgandagina o'qiladi, keyin boshqa hech qachon.

Xotiradagi kesh (_Cache) — /api/content'dagi content_cache bilan bir xil
sabab: xizmat/portfolio sahifalari har so'rovda DB'ga bormasin. Admin CRUD
yozgandan keyin invalidate() chaqiriladi (main.py).
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .content.portfolio import CASE_KEYS as SEED_CASE_KEYS, CASES as SEED_CASES, SLUGS as SEED_CASE_SLUGS
from .content.services import SERVICES as SEED_SERVICES, SERVICE_KEYS as SEED_SERVICE_KEYS, SLUGS as SEED_SERVICE_SLUGS
from .db import PortfolioCase, Service, SessionLocal, SlugRedirect


class _Cache:
    __slots__ = ("services", "cases")

    def __init__(self):
        self.services: list[dict] | None = None
        self.cases: list[dict] | None = None

    def clear(self) -> None:
        self.services = None
        self.cases = None


_cache = _Cache()


def invalidate() -> None:
    _cache.clear()


async def seed_if_empty(session: AsyncSession) -> None:
    """Jadval bo'sh bo'lsa app/content/services.py va portfolio.py'dagi
    haqiqiy, tasdiqlangan kontentdan bir martalik to'ldiradi."""
    n_services = await session.scalar(select(func.count()).select_from(Service))
    if not n_services:
        for i, key in enumerate(SEED_SERVICE_KEYS):
            langs = SEED_SERVICES[key]
            slugs = SEED_SERVICE_SLUGS[key]
            session.add(Service(
                key=key, order=i, published=True,
                slug_uz=slugs["uz"], slug_ru=slugs["ru"], slug_en=slugs["en"],
                data_uz=dict(langs["uz"]), data_ru=dict(langs["ru"]), data_en=dict(langs["en"]),
            ))
    n_cases = await session.scalar(select(func.count()).select_from(PortfolioCase))
    if not n_cases:
        for i, key in enumerate(SEED_CASE_KEYS):
            langs = SEED_CASES[key]
            slugs = SEED_CASE_SLUGS[key]
            session.add(PortfolioCase(
                key=key, order=i, published=True, image="",
                slug_uz=slugs["uz"], slug_ru=slugs["ru"], slug_en=slugs["en"],
                data_uz=dict(langs["uz"]), data_ru=dict(langs["ru"]), data_en=dict(langs["en"]),
            ))
    if not n_services or not n_cases:
        await session.commit()


async def get_services(published_only: bool = True) -> list[dict]:
    if _cache.services is None:
        async with SessionLocal() as session:
            res = await session.execute(select(Service).order_by(Service.order, Service.id))
            _cache.services = [s.as_dict() for s in res.scalars().all()]
    if published_only:
        return [s for s in _cache.services if s["published"]]
    return list(_cache.services)


async def get_cases(published_only: bool = True) -> list[dict]:
    if _cache.cases is None:
        async with SessionLocal() as session:
            res = await session.execute(select(PortfolioCase).order_by(PortfolioCase.order, PortfolioCase.id))
            _cache.cases = [c.as_dict() for c in res.scalars().all()]
    if published_only:
        return [c for c in _cache.cases if c["published"]]
    return list(_cache.cases)


async def find_redirect(old_path: str) -> str | None:
    async with SessionLocal() as session:
        row = await session.scalar(select(SlugRedirect.new_path).where(SlugRedirect.old_path == old_path))
    return row
