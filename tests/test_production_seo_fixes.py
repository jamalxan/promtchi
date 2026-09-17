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

from app.db import Content, FaqItem, Post, Setting, SessionLocal, SlugRedirect, run_data_fixups
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
        # Blog RU/EN lokalizatsiyasi qo'shilgach (app/db.py, 14-fixup) id=12
        # sinov bazasida RUSCHA postga to'g'ri kelishi mumkin. Migratsiya esa
        # ataylab TURLI TILDAGI juftlikni o'tkazib yuboradi — shu sabab
        # mexanizmni tekshirish uchun ikkala postni ham vaqtincha uz qilamiz
        # va test oxirida asl holatiga qaytaramiz.
        restore = {}
        async with SessionLocal() as s:
            marker = await s.get(Setting, "blog_cannibalization_fix_v1_done")
            if marker is not None:
                await s.delete(marker)
            for pid, body in ((1, "x"), (12, "x" * 50)):
                p = await s.get(Post, pid)
                if p is None:
                    s.add(Post(id=pid, title=f"Sinov maqolasi {pid}", body=body,
                               lang="uz", published=True, created_at=now))
                else:
                    restore[pid] = (p.lang, p.published)
                    p.lang, p.published = "uz", True
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

        async with SessionLocal() as s:  # boshqa testlar uchun holatni tiklaymiz
            for pid, (lang, published) in restore.items():
                p = await s.get(Post, pid)
                p.lang, p.published = lang, published
            await s.commit()

    asyncio.run(_run())


# ══════════ FAQ dublikat (faq_items.service_key, PART 12 to'ldirilishi) ══════════
# PRODUCTION_SEO_AUDIT.md bo'lim 2.2: CRM/AI xizmat sahifasida (uz/ru/en) bir xil
# ma'noli savol ikki marta chiqadi — biri Service.data_{lang}["faq"]'da, ikkinchisi
# `faq_items` jadvalida service_key="crm"/"ai" orqali bog'langan. Eski
# "service_faq_dedupe_v1" migratsiyasi (app/db.py) Service.data ichidan qidirgani
# uchun HAR DOIM no-op edi (matn haqiqatda faq_items'da). Bu bo'lim yangi
# "faq_items_linked_dup_unlink_v1" migratsiyasini va yangilangan seedni tekshiradi.

_AI_DUP_UZ = "AI chatbotni Telegram yoki saytga integratsiya qilasizmi?"
_AI_CANONICAL_UZ = "AI chatbotni Telegram yoki saytga ulash mumkinmi?"
_CRM_DUP_UZ = "Mavjud CRM yoki boshqa tizimlarga integratsiya qilasizmi?"
_CRM_CANONICAL_UZ = "Mavjud CRM (AmoCRM, Bitrix24)ga integratsiya qila olasizmi?"

_AI_DUP_RU = "Вы интегрируете AI-чат-бот с Telegram или сайтом?"
_AI_CANONICAL_RU = "Можно подключить AI-чат-бот к Telegram или сайту?"
_CRM_DUP_RU = "Вы делаете интеграции с существующей CRM или другими системами?"
_CRM_CANONICAL_RU = "Можно интегрировать с существующей CRM (AmoCRM, Bitrix24)?"

_AI_DUP_EN = "Do you integrate AI chatbots with Telegram or a website?"
_AI_CANONICAL_EN = "Can an AI chatbot connect to Telegram or a website?"
_CRM_DUP_EN = "Can you integrate with an existing CRM or other systems?"
_CRM_CANONICAL_EN = "Can you integrate with an existing CRM (AmoCRM, Bitrix24)?"


def test_fresh_seed_does_not_link_dup_questions_to_service(client):
    """app/faq_store.py::_SEED_SERVICE_KEY endi index 11/16'ni "ai"/"crm"ga
    bog'lamasligi kerak — fresh DB (test fixture) buni to'g'ridan-to'g'ri
    aks ettiradi."""

    async def _run():
        async with SessionLocal() as s:
            res = await s.execute(select(FaqItem).where(FaqItem.question_uz == _AI_DUP_UZ))
            item = res.scalar_one()
            assert item.service_key == ""

            res = await s.execute(select(FaqItem).where(FaqItem.question_uz == _CRM_DUP_UZ))
            item = res.scalar_one()
            assert item.service_key == ""

    asyncio.run(_run())


def test_ai_service_page_has_no_duplicate_faq_uz_ru_en(client):
    """/xizmatlar/ai/ sahifasida savol faqat BIR marta ko'rinishi kerak —
    faq_items'dagi deyarli bir xil ma'noli nusxa endi service_key="" bo'lgani
    uchun sahifaga chiqmasligi kerak."""
    pairs = [("uz", _AI_DUP_UZ, _AI_CANONICAL_UZ), ("ru", _AI_DUP_RU, _AI_CANONICAL_RU),
             ("en", _AI_DUP_EN, _AI_CANONICAL_EN)]
    for lang, dup, canonical in pairs:
        html = client.get(f"/{lang}/xizmatlar/ai/").text
        assert canonical in html
        assert dup not in html


def test_crm_service_page_has_no_duplicate_faq_uz_ru_en(client):
    pairs = [("uz", _CRM_DUP_UZ, _CRM_CANONICAL_UZ), ("ru", _CRM_DUP_RU, _CRM_CANONICAL_RU),
             ("en", _CRM_DUP_EN, _CRM_CANONICAL_EN)]
    for lang, dup, canonical in pairs:
        html = client.get(f"/{lang}/xizmatlar/crm/").text
        assert canonical in html
        assert dup not in html


def test_ai_crm_faq_jsonld_matches_visible_faq_exactly(client):
    """FAQPage JSON-LD (mainEntity) sahifadagi ko'rinadigan `s.faq` ro'yxati
    bilan bir xil manbadan (app/pages.py::service_detail) kelishi kerak —
    dublikat savol JSON-LD'da ham bo'lmasligi shart."""
    import re

    for slug in ("ai", "crm"):
        html = client.get(f"/uz/xizmatlar/{slug}/").text
        m = re.search(r'<script type="application/ld\+json">(\{"@context":"https://schema.org","@type":"FAQPage".*?)</script>', html)
        assert m, f"FAQPage JSON-LD topilmadi: {slug}"
        import json as _json
        schema = _json.loads(m.group(1))
        questions = [q["name"] for q in schema["mainEntity"]]
        assert len(questions) == len(set(questions)), f"{slug}: JSON-LD'da dublikat savol bor: {questions}"
        dup = _AI_DUP_UZ if slug == "ai" else _CRM_DUP_UZ
        assert dup not in questions


def test_faq_items_linked_dup_unlink_migration_fixes_stale_production_row():
    """Production'da bu migratsiya ishga tushishidan OLDIN yaratilgan qator
    (service_key="ai"/"crm" + audit'da keltirilgan aniq matn) hali ham
    mavjud bo'lsa, run_data_fixups uni service_key=""ga o'tkazishi kerak."""

    async def _run():
        async with SessionLocal() as s:
            marker = await s.get(Setting, "faq_items_linked_dup_unlink_v1_done")
            if marker is not None:
                await s.delete(marker)
            # eski (tuzatishdan oldingi) production holatini simulyatsiya qilamiz
            s.add(FaqItem(
                key="test_stale_ai_dup", order=999, published=True,
                category="AI", service_key="ai",
                question_uz=_AI_DUP_UZ, answer_uz="test",
                question_ru=_AI_DUP_RU, answer_ru="test",
                question_en=_AI_DUP_EN, answer_en="test",
            ))
            s.add(FaqItem(
                key="test_stale_crm_dup", order=1000, published=True,
                category="CRM", service_key="crm",
                question_uz=_CRM_DUP_UZ, answer_uz="test",
                question_ru=_CRM_DUP_RU, answer_ru="test",
                question_en=_CRM_DUP_EN, answer_en="test",
            ))
            await s.commit()

        try:
            async with SessionLocal() as s:
                await run_data_fixups(s)

            async with SessionLocal() as s:
                ai_item = await s.scalar(select(FaqItem).where(FaqItem.key == "test_stale_ai_dup"))
                crm_item = await s.scalar(select(FaqItem).where(FaqItem.key == "test_stale_crm_dup"))
                assert ai_item.service_key == ""
                assert crm_item.service_key == ""
        finally:
            async with SessionLocal() as s:
                for key in ("test_stale_ai_dup", "test_stale_crm_dup"):
                    item = await s.scalar(select(FaqItem).where(FaqItem.key == key))
                    if item is not None:
                        await s.delete(item)
                await s.commit()

    asyncio.run(_run())


def test_faq_items_linked_dup_unlink_migration_leaves_unrelated_rows_untouched():
    """Migratsiya faqat aniq mos matnli qatorni o'zgartirishi kerak — boshqa
    "ai"/"crm"ga bog'langan (haqiqiy, dublikat bo'lmagan) savollar va boshqa
    umumiy savollar tegilmasdan qolishi kerak."""

    async def _run():
        async with SessionLocal() as s:
            marker = await s.get(Setting, "faq_items_linked_dup_unlink_v1_done")
            if marker is not None:
                await s.delete(marker)
            await s.commit()

        async with SessionLocal() as s:
            before = {f.key: f.service_key for f in (await s.execute(select(FaqItem))).scalars().all()}

        async with SessionLocal() as s:
            await run_data_fixups(s)

        async with SessionLocal() as s:
            after = {f.key: f.service_key for f in (await s.execute(select(FaqItem))).scalars().all()}

        # yangi seed hech qanday dublikatni bog'lamaydi, shu sabab migratsiya
        # bu bazada haqiqiy no-op bo'lishi kerak — barcha service_key'lar
        # ("q10"/"q17" kabi haqiqiy "ai"/"crm" savollari qo'shilgan) saqlanadi
        assert after == before

    asyncio.run(_run())
