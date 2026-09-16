"""4-bosqich (production SEO/GEO/performance audit fix) regressiyalari:
- www -> apex 301 redirect
- ichki SEO sahifalar (pages.py)da Cache-Control, admin/API'da yo'q
- /static/* uchun uzoq muddatli kesh
- bosh sahifa (static/index*.html) admin kontentini JONLI aks ettirishi
  (PRODUCTION_SEO_AUDIT.md bo'lim 1 root cause fix)
- eski/yangi kontakt ma'lumotlari va blog cannibalization migratsiyasi
"""
import asyncio
import datetime

from sqlalchemy import select

from app.db import Content, Post, Setting, SessionLocal, SlugRedirect, run_data_fixups
from app.pages import _slugify


def test_www_redirects_to_apex_https(client):
    r = client.get("/uz/xizmatlar/crm/", headers={"host": "www.promtchi.uz"}, follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "https://promtchi.uz/uz/xizmatlar/crm/"


def test_www_redirect_preserves_query_string(client):
    r = client.get("/uz/blog/?page=2", headers={"host": "www.promtchi.uz"}, follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "https://promtchi.uz/uz/blog/?page=2"


def test_non_www_host_not_redirected(client):
    r = client.get("/uz/xizmatlar/crm/", headers={"host": "promtchi.uz"})
    assert r.status_code == 200


def test_public_page_gets_cache_control(client):
    r = client.get("/uz/xizmatlar/crm/")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "public" in cc and "max-age=" in cc


def test_faq_page_gets_cache_control(client):
    r = client.get("/uz/faq/")
    assert r.status_code == 200
    assert "public" in r.headers.get("cache-control", "")


def test_admin_api_not_publicly_cached(client):
    r = client.get("/api/admin/leads")  # auth yo'q -> 401, lekin no-store bo'lishi kerak
    assert r.headers.get("cache-control") == "no-store"


def test_admin_html_not_publicly_cached(client):
    r = client.get("/admin")
    assert r.headers.get("cache-control") == "no-store"


def test_static_css_gets_long_cache(client):
    r = client.get("/static/site.css")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "public" in cc and "max-age=86400" in cc


def test_homepage_reflects_live_admin_contacts(admin_client):
    """Root cause fix: static/index.html endi content_cache'dagi (DB) qiymatni
    aks ettirishi kerak — admin kontaktni o'zgartirsa, bosh sahifa (JS ishga
    tushmasdan oldingi SSR HTML) ham darhol yangilanadi."""
    doc = admin_client.get("/api/admin/content").json()
    doc["contacts"] = [
        {"label": "Telegram", "value": "@qatest", "url": "https://t.me/qatest", "icon": "telegram"},
        {"label": "Email", "value": "hello@promtchi.uz", "url": "mailto:hello@promtchi.uz", "icon": "email"},
        {"label": "Telefon", "value": "+998 77 777 77 77", "url": "tel:+998777777777", "icon": "phone"},
    ]
    doc["socials"] = [{"name": "Telegram", "url": "https://t.me/qatest", "icon": "telegram"}]
    r = admin_client.put("/api/admin/content", json=doc)
    assert r.status_code == 200, r.text

    try:
        html = admin_client.get("/uz/").text
        assert "@qatest" in html
        assert "+998 77 777 77 77" in html
        assert "t.me/qatest" in html
        # Organization JSON-LD ham yangilangan bo'lishi kerak
        assert '"telephone":"+998777777777"' in html
        assert '"sameAs":["https://t.me/qatest"]' in html
    finally:
        # boshqa testlarga ta'sir qilmasin — asl (to'g'ri) qiymatga qaytaramiz
        doc["contacts"] = [
            {"label": "Telegram", "value": "@promtchiadmin", "url": "https://t.me/promtchiadmin", "icon": "telegram"},
            {"label": "Email", "value": "hello@promtchi.uz", "url": "mailto:hello@promtchi.uz", "icon": "email"},
            {"label": "Telefon", "value": "+998 93 160 67 06", "url": "tel:+998931606706", "icon": "phone"},
        ]
        doc["socials"] = [{"name": "Telegram", "url": "https://t.me/promtchiadmin", "icon": "telegram"}]
        admin_client.put("/api/admin/content", json=doc)


def test_default_content_seed_has_correct_contacts(client):
    """schemas.DEFAULT_CONTENT (fresh DB seed / reset endpoint manbai) eski
    placeholder telefon/Telegram qaytarib qo'ymasligi kerak."""
    from app.schemas import DEFAULT_CONTENT

    contacts = {c["icon"]: c for c in DEFAULT_CONTENT["contacts"]}
    assert contacts["phone"]["url"] == "tel:+998931606706"
    assert contacts["telegram"]["url"] == "https://t.me/promtchiadmin"


def test_contact_accuracy_fixup_corrects_stale_db_value(client):
    """Production'da Content.contacts eski qiymatda qolib ketgan bo'lsa,
    run_data_fixups uni to'g'irlashi kerak (marker qayta ishlatish uchun
    tozalanadi, DB qiymati ataylab eskisiga qaytariladi)."""

    async def _run():
        async with SessionLocal() as s:
            row = await s.get(Content, 1)
            row.data["contacts"] = [
                {"label": "Telegram", "value": "@promtchiuz", "url": "https://t.me/promtchiuz", "icon": "telegram"},
                {"label": "Telefon", "value": "+998 90 000 00 00", "url": "tel:+998900000000", "icon": "phone"},
            ]
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(row, "data")
            marker = await s.get(Setting, "contact_accuracy_fix_v1_done")
            if marker is not None:
                await s.delete(marker)
            await s.commit()

        async with SessionLocal() as s:
            await run_data_fixups(s)

        async with SessionLocal() as s:
            row = await s.get(Content, 1)
            contacts = {c["icon"]: c for c in row.data["contacts"]}
            assert contacts["telegram"]["url"] == "https://t.me/promtchiadmin"
            assert contacts["phone"]["url"] == "tel:+998931606706"

    asyncio.run(_run())


def test_blog_cannibalization_fixup_redirects_old_to_new():
    """`_OLD_TO_NEW_POST_ID` xaritasi (app/db.py::run_data_fixups) production
    post ID'lariga (1..8 -> 9..15) qattiq bog'langan — shu sabab id=1/id=12
    juftligini to'g'ridan-to'g'ri ishlatib mexanizmni tekshiramiz (id=1
    boshqa blog_seed migratsiyasi tomonidan allaqachon yaratilgan bo'lishi
    mumkin — mavjud bo'lsa qayta yaratilmaydi): id=1 unpublish qilinib,
    SlugRedirect orqali id=12'ga 301 yo'naltirilishi kerak."""

    async def _run():
        now = datetime.datetime.now(datetime.timezone.utc)
        async with SessionLocal() as s:
            marker = await s.get(Setting, "blog_cannibalization_fix_v1_done")
            if marker is not None:
                await s.delete(marker)
            if await s.get(Post, 1) is None:
                s.add(Post(id=1, title="Sinov maqolasi 1", body="x", lang="uz", published=True, created_at=now))
            if await s.get(Post, 12) is None:
                s.add(Post(id=12, title="Sinov maqolasi 12", body="x" * 50, lang="uz", published=True, created_at=now))
            await s.commit()

        async with SessionLocal() as s:
            await run_data_fixups(s)

        async with SessionLocal() as s:
            old1 = await s.get(Post, 1)
            new12 = await s.get(Post, 12)
            assert old1.published is False
            assert new12.published is True
            old_path = f"/uz/blog/{_slugify(old1.title, old1.id)}/"
            new_path = f"/uz/blog/{_slugify(new12.title, new12.id)}/"
            redirect = await s.scalar(select(SlugRedirect).where(SlugRedirect.old_path == old_path))
            assert redirect is not None
            assert redirect.new_path == new_path

    asyncio.run(_run())
