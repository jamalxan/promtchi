"""3 tilli (UZ/RU/EN) SSR sahifalar — xizmatlar, yechimlar, portfolio, FAQ,
biz haqimizda, aloqa, blog, sitemap.xml, robots.txt.

Bosh sahifa (/{lang}/) BU YERDA emas — main.py'dagi tez ishlaydigan
_PageCache orqali xizmat qiladi (static/index*.html, admin-tahrirlanadigan
kontentga bog'liq). Bu yerdagi sahifalar Jinja2 orqali kod-darajasida
saqlangan, real faktlarga asoslangan trilingual kontentni (app/content/*)
render qiladi — TZ v1.0 (15.09.2026), 2/5/6/8/9/13-bo'limlar.
"""
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from . import faq_store, seo, services_store
from .content.markdown_lite import render_body
from .config import settings
from .content import LANGS
from .content.about import ABOUT
from .content.common import COMMON, FOOTER, LANG_NAMES, LANG_SHORT, NAV, ORG, PROJECT_TYPE_OPTIONS
from .content.legal import LEGAL_LABEL, LEGAL_SLUGS, PRIVACY, TERMS, UPDATED_DATE, UPDATED_LABEL
from .content.solutions import SLUGS as SOLUTION_SLUGS, SOLUTION_KEYS, SOLUTIONS
from .db import Content, Post, SessionLocal

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _asset_v(*names: str) -> str:
    """Statik fayllar uchun kesh-buster.

    site.css `max-age=86400` bilan uzatiladi, shuning uchun deploy'dan keyin
    qaytgan foydalanuvchi YANGI HTML + ESKI CSS oladi va sahifa buzilgan
    ko'rinadi (sr-only sarlavha chiqib qoladi, nav ro'yxat bo'lib to'kiladi).
    Fayl mtime'idan hosil qilingan qiymat URL'ni o'zgartiradi — brauzer
    yangisini so'rashga majbur bo'ladi."""
    stamp = 0.0
    for name in names:
        try:
            stamp = max(stamp, (STATIC_DIR / name).stat().st_mtime)
        except OSError:
            continue
    return format(int(stamp), "x")


ASSET_V = _asset_v("site.css", "site.js")


def _check_lang(lang: str) -> str:
    if lang not in LANGS:
        raise HTTPException(404, "Sahifa topilmadi")
    return lang


def _slug_for(slugs_map: dict, key: str, lang: str) -> str:
    return slugs_map[key][lang]


def _key_for_slug(slugs_map: dict, slug: str, lang: str) -> str | None:
    for key, by_lang in slugs_map.items():
        if by_lang.get(lang) == slug:
            return key
    return None


# Statik ORG (app/content/common.py) — admin panelda o'zgartiriladigan
# aloqa ma'lumotlari (Telegram/Email/Telefon/Instagram) bilan sinxron
# turishi uchun har 60s'da /api/content dagi `contacts`/`socials`'dan
# yengil kesh orqali yangilanadi (bosh sahifadagi katta trafikga
# mo'ljallangan content_cache'dan alohida — bu yerda faqat aloqa
# maydonlari kerak, ichki sahifalar kamroq so'raladi).
_live_org_cache: dict = {"org": None, "ts": 0.0}
_LIVE_ORG_TTL = 60.0


async def _live_org() -> dict:
    now = time.monotonic()
    cached = _live_org_cache["org"]
    if cached is not None and (now - _live_org_cache["ts"]) < _LIVE_ORG_TTL:
        return cached
    org = dict(ORG)
    try:
        async with SessionLocal() as session:
            row = await session.get(Content, 1)
        data = row.data if row else {}
        contacts = {c.get("label"): c for c in data.get("contacts", [])}
        tg = contacts.get("Telegram")
        if tg and tg.get("value"):
            org["telegram_handle"] = tg["value"]
            org["telegram_url"] = tg.get("url") or org["telegram_url"]
        email = contacts.get("Email")
        if email and email.get("value"):
            org["email"] = email["value"]
        phone = contacts.get("Telefon") or contacts.get("Phone")
        if phone and phone.get("value"):
            org["phone"] = phone["value"]
            url = phone.get("url", "")
            if url.startswith("tel:"):
                org["phone_tel"] = url[len("tel:"):]
        ig = next((s for s in data.get("socials", []) if s.get("icon") == "instagram"), None)
        if ig and ig.get("url"):
            org["instagram_url"] = ig["url"]
    except Exception:
        pass  # DB vaqtincha ishlamasa — statik ORG bilan davom etadi
    _live_org_cache["org"] = org
    _live_org_cache["ts"] = now
    return org


def _abs_image(image: str) -> str | None:
    """og:image mutlaq URL bo'lishi kerak. `image` — admin panelda tasdiqlangan
    ikkita shakldan biri (schemas._validate_media_url): to'liq http(s):// havola
    yoki /static/uploads/... nisbiy yo'l — faqat ikkinchisiga SITE_URL qo'shiladi
    (seo.abs_url ni to'g'ridan-to'g'ri chaqirish allaqachon mutlaq havolani
    ikki marta prefikslab, buzib qo'yishi mumkin edi)."""
    if not image:
        return None
    return image if image.startswith("http") else seo.abs_url(image)


async def _base_ctx(request: Request, lang: str, path_by_lang: dict, title: str, desc: str,
                     breadcrumbs: list | None = None, og_type: str = "website",
                     noindex: bool = False, hreflang_paths: dict | None = None,
                     og_image: str | None = None) -> dict:
    """`hreflang_paths` — faqat <head> hreflang teglari uchun (bo'lmasa path_by_lang
    ishlatiladi). Bir tilda mavjud, boshqalarida yo'q kontent (masalan blog posti)
    uchun ikkalasi FARQLANADI: `path_by_lang` header'dagi til almashtirgich uchun
    (boshqa tilda mos indeks sahifasiga yo'naltiradi), `hreflang_paths` esa faqat
    haqiqatan mavjud tarjimalarni e'lon qiladi — aks holda mavjud bo'lmagan
    "tarjima"ni qidiruv tizimiga yolg'on va'da qilgan bo'lardik."""
    canonical = seo.abs_url(path_by_lang[lang])
    alt = seo.alternates(hreflang_paths if hreflang_paths is not None else path_by_lang)
    crumb_schema = None
    crumbs_nav = None
    if breadcrumbs:
        crumbs_nav = breadcrumbs
        crumb_schema = seo.json_ld(seo.breadcrumb_schema(breadcrumbs))
    org = await _live_org()
    return {
        "request": request,
        "lang": lang,
        "html_lang": seo.hreflang_code(lang).split("-")[0],
        "langs": LANGS,
        "lang_short": LANG_SHORT,
        "lang_names": LANG_NAMES,
        "lang_urls": path_by_lang,
        "canonical": canonical,
        "alt_links": alt,
        "og_type": og_type,
        "og_locale": seo.hreflang_code(lang).replace("-", "_"),
        "og_image": og_image or seo.OG_DEFAULT,
        "org": org,
        "nav": NAV[lang],
        "footer": FOOTER[lang],
        "common": COMMON[lang],
        "page_title": title,
        "page_desc": desc,
        "ga_id": settings.GA_MEASUREMENT_ID,
        "gsc_token": settings.SEARCH_CONSOLE_VERIFICATION,
        "asset_v": ASSET_V,
        "legal": {
            "privacy": f"/{lang}/{LEGAL_SLUGS['privacy'][lang]}/",
            "terms": f"/{lang}/{LEGAL_SLUGS['terms'][lang]}/",
        },
        "org_schema": seo.json_ld(seo.organization_schema(org)),
        "website_schema": seo.json_ld(seo.website_schema(lang)),
        "breadcrumb_schema": crumb_schema,
        "breadcrumbs": crumbs_nav,
        "noindex": noindex,
    }


def _service_cards(lang: str, services: list) -> list:
    return [{"slug": s["slugs"][lang], "nav": s[lang]["nav"], "value": s[lang]["value"]} for s in services]


def _case_cards(lang: str, cases: list, exclude: str | None = None) -> list:
    return [{"slug": c["slugs"][lang], **c[lang]} for c in cases if c["key"] != exclude]


def _post_tags(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


async def _posts_tagged(lang: str, tag: str, limit: int = 3) -> list[dict]:
    """Berilgan `tag` (odatda xizmat `key`i) bilan belgilangan, chop etilgan
    postlar — xizmat sahifasidagi "Mavzu bo'yicha maqolalar" bo'limi va
    blog<->xizmat topical cluster bog'lanishi uchun (TZ GEO audit, 8-bo'lim:
    "Blog → Service → Contact internal linking")."""
    async with SessionLocal() as session:
        res = await session.execute(
            select(Post).where(Post.published == True, Post.lang == lang)  # noqa: E712
            .order_by(Post.created_at.desc(), Post.id.desc()).limit(200)
        )
        rows = res.scalars().all()
    matched = [p for p in rows if tag in _post_tags(p.tags)][:limit]
    return [{
        "slug": _slugify(p.title, p.id),
        "title": p.title,
        "excerpt": p.excerpt or ((p.body[:130] + "…") if len(p.body) > 130 else p.body),
    } for p in matched]


# ══════════ XIZMATLAR ══════════
# Kontent app/db.py Service jadvalidan (admin-tahrirlanadigan, TZ 19-bo'lim) —
# app/services_store.py orqali xotira keshi bilan o'qiladi.

@router.get("/{lang}/xizmatlar/", response_class=HTMLResponse)
async def services_index(request: Request, lang: str):
    _check_lang(lang)
    services = await services_store.get_services()
    path_by_lang = {l: f"/{l}/xizmatlar/" for l in LANGS}
    intro = {
        "uz": "Web va mobil ilovadan tortib, AI va CRM/ERP tizimlarigacha — biznesingiz uchun kerakli barcha raqamli yechimlar.",
        "ru": "От веб- и мобильных приложений до AI и CRM/ERP систем — все цифровые решения, нужные вашему бизнесу.",
        "en": "From web and mobile apps to AI and CRM/ERP systems — every digital solution your business needs.",
    }[lang]
    # <title> H1'dan alohida: H1 qisqa va sahifa ichida tabiiy ko'rinadi,
    # <title> esa qidiruv natijasida nima taklif qilinishini aytadi.
    seo_title = {
        "uz": "Xizmatlar — veb-sayt, mobil ilova, CRM/ERP va AI | promtchi",
        "ru": "Услуги — сайты, мобильные приложения, CRM/ERP и AI | promtchi",
        "en": "Services — web, mobile, CRM/ERP and AI development | promtchi",
    }[lang]
    ctx = await _base_ctx(request, lang, path_by_lang,
                     title=seo_title, desc=intro,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["services"], None)])
    ctx.update(services=_service_cards(lang, services), t_h1=NAV[lang]["services"], t_intro=intro)
    return templates.TemplateResponse(request, "services_index.html", ctx)


@router.get("/{lang}/xizmatlar/{slug}/", response_class=HTMLResponse)
async def service_detail(request: Request, lang: str, slug: str):
    _check_lang(lang)
    services = await services_store.get_services()
    match = next((s for s in services if s["slugs"][lang] == slug), None)
    if match is None:
        new_path = await services_store.find_redirect(f"/{lang}/xizmatlar/{slug}/")
        if new_path:
            return RedirectResponse(new_path, status_code=301)
        raise HTTPException(404, "Xizmat topilmadi")
    s = match[lang]
    slugs = match["slugs"]
    path_by_lang = {l: f"/{l}/xizmatlar/{slugs[l]}/" for l in LANGS}
    ctx = await _base_ctx(request, lang, path_by_lang, title=s["title"], desc=s["meta"],
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"),
                                  (NAV[lang]["services"], f"/{lang}/xizmatlar/"),
                                  (s["nav"], None)])
    cases = await services_store.get_cases()
    canonical_url = seo.abs_url(path_by_lang[lang])
    # Shu xizmatga bog'langan umumiy FAQ (admin "FAQ sahifasi"da service'ga
    # biriktirgan savollar, TZ 14-bo'lim) xizmatning o'ziga xos FAQ ro'yxatiga
    # qo'shiladi — ikkalasi ham /faq/ va shu sahifada ko'rinadi (indexable).
    linked_faq = [(f["question"], f["answer"]) for f in await faq_store.get_items(lang, service_key=match["key"])]
    faq_items = [*s.get("faq", []), *linked_faq]
    ctx.update(
        s={**s, "slug": slug, "faq": faq_items},
        all_services=_service_cards(lang, services),
        related_cases=_case_cards(lang, cases)[:2],
        related_posts=await _posts_tagged(lang, match["key"]),
        service_schema=seo.json_ld(seo.service_schema(s["h1"], s["value"], canonical_url, lang)),
        faq_schema=seo.json_ld(seo.faq_schema(faq_items)) if faq_items else None,
    )
    return templates.TemplateResponse(request, "service_detail.html", ctx)


# ══════════ YECHIMLAR ══════════

@router.get("/{lang}/yechimlar/", response_class=HTMLResponse)
async def solutions_index(request: Request, lang: str):
    _check_lang(lang)
    path_by_lang = {l: f"/{l}/yechimlar/" for l in LANGS}
    intro = {
        "uz": "Sohangizga mos raqamli yechim — savdo, logistika va ishlab chiqarish uchun real tajribaga asoslangan CRM/ERP/avtomatlashtirish.",
        "ru": "Цифровое решение под вашу отрасль — CRM/ERP/автоматизация на основе реального опыта для продаж, логистики и производства.",
        "en": "A digital solution for your industry — CRM/ERP/automation grounded in real experience for sales, logistics and manufacturing.",
    }[lang]
    seo_title = {
        "uz": "Yechimlar — savdo, logistika va ishlab chiqarish | promtchi",
        "ru": "Решения — продажи, логистика и производство | promtchi",
        "en": "Solutions — sales, logistics and manufacturing | promtchi",
    }[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=seo_title, desc=intro,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["solutions"], None)])
    solutions = [{"slug": SOLUTION_SLUGS[k][lang], "nav": SOLUTIONS[k][lang]["nav"],
                  "intro": SOLUTIONS[k][lang]["intro"]} for k in SOLUTION_KEYS]
    ctx.update(solutions=solutions, t_h1=NAV[lang]["solutions"], t_intro=intro)
    return templates.TemplateResponse(request, "solutions_index.html", ctx)


@router.get("/{lang}/yechimlar/{slug}/", response_class=HTMLResponse)
async def solution_detail(request: Request, lang: str, slug: str):
    _check_lang(lang)
    key = _key_for_slug(SOLUTION_SLUGS, slug, lang)
    if key is None:
        raise HTTPException(404, "Yechim topilmadi")
    s = SOLUTIONS[key][lang]
    path_by_lang = {l: f"/{l}/yechimlar/{SOLUTION_SLUGS[key][l]}/" for l in LANGS}
    ctx = await _base_ctx(request, lang, path_by_lang, title=s["title"], desc=s["meta"],
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"),
                                  (NAV[lang]["solutions"], f"/{lang}/yechimlar/"),
                                  (s["nav"], None)])
    services_by_key = {sv["key"]: sv for sv in await services_store.get_services()}
    cases_by_key = {c["key"]: c for c in await services_store.get_cases()}
    related_services = [{"slug": services_by_key[k]["slugs"][lang], "nav": services_by_key[k][lang]["nav"]}
                         for k in s.get("services_ref", []) if k in services_by_key]
    related_cases = [{"slug": cases_by_key[k]["slugs"][lang], **cases_by_key[k][lang]}
                      for k in s.get("case_ref", []) if k in cases_by_key]
    ctx.update(
        s=s, related_services=related_services, related_cases=related_cases,
        faq_schema=seo.json_ld(seo.faq_schema(s["faq"])) if s.get("faq") else None,
    )
    return templates.TemplateResponse(request, "solution_detail.html", ctx)


# ══════════ PORTFOLIO ══════════

@router.get("/{lang}/portfolio/", response_class=HTMLResponse)
async def portfolio_index(request: Request, lang: str):
    _check_lang(lang)
    cases = await services_store.get_cases()
    path_by_lang = {l: f"/{l}/portfolio/" for l in LANGS}
    intro = {
        "uz": "Real loyihalarimiz — muammo, yechim va natija bilan. Har biri haqiqiy mijoz uchun (yoki o'z mahsulotimiz sifatida) ishlab chiqilgan.",
        "ru": "Наши реальные проекты — с проблемой, решением и результатом. Каждый разработан для реального клиента (или как наш собственный продукт).",
        "en": "Our real projects — with the problem, solution and result. Each was built for a real client (or as our own product).",
    }[lang]
    seo_title = {
        "uz": "Portfolio — real loyihalar va keyslar | promtchi",
        "ru": "Портфолио — реальные проекты и кейсы | promtchi",
        "en": "Portfolio — real projects and case studies | promtchi",
    }[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=seo_title, desc=intro,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["portfolio"], None)])
    ctx.update(cases=_case_cards(lang, cases), t_h1=NAV[lang]["portfolio"], t_intro=intro)
    return templates.TemplateResponse(request, "portfolio_index.html", ctx)


@router.get("/{lang}/portfolio/{slug}/", response_class=HTMLResponse)
async def portfolio_detail(request: Request, lang: str, slug: str):
    _check_lang(lang)
    cases = await services_store.get_cases()
    match = next((c for c in cases if c["slugs"][lang] == slug), None)
    if match is None:
        new_path = await services_store.find_redirect(f"/{lang}/portfolio/{slug}/")
        if new_path:
            return RedirectResponse(new_path, status_code=301)
        raise HTTPException(404, "Loyiha topilmadi")
    c = match[lang]
    slugs = match["slugs"]
    path_by_lang = {l: f"/{l}/portfolio/{slugs[l]}/" for l in LANGS}
    # Case title uch tilda ham bir xil (brend nomi) edi — endi case'ning O'Z
    # `cat` maydoni (DB'dagi tasdiqlangan kategoriya) bilan farqlanadi.
    case_title = {
        "uz": f"{c['title']} — {c.get('cat', '')} keysi | promtchi",
        "ru": f"{c['title']} — кейс: {c.get('cat', '')} | promtchi",
        "en": f"{c['title']} — {c.get('cat', '')} case study | promtchi",
    }[lang].replace("  ", " ").replace(" —  ", " — ")
    ctx = await _base_ctx(request, lang, path_by_lang, title=case_title, desc=c["meta"],
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"),
                                  (NAV[lang]["portfolio"], f"/{lang}/portfolio/"),
                                  (c["title"], None)],
                     og_image=_abs_image(match["image"]))
    ctx.update(c={**c, "slug": slug, "image": match["image"]}, other_cases=_case_cards(lang, cases, exclude=match["key"]))
    return templates.TemplateResponse(request, "portfolio_detail.html", ctx)


# ══════════ FAQ ══════════

@router.get("/{lang}/faq/", response_class=HTMLResponse)
async def faq_page(request: Request, lang: str):
    _check_lang(lang)
    path_by_lang = {l: f"/{l}/faq/" for l in LANGS}
    items = [(f["question"], f["answer"]) for f in await faq_store.get_items(lang)]
    desc = {"uz": "promtchi haqida ko'p so'raladigan savollar: narx, muddat, to'lov, texnik yordam va xizmatlar.",
            "ru": "Часто задаваемые вопросы о promtchi: цена, сроки, оплата, техподдержка и услуги.",
            "en": "Frequently asked questions about promtchi: pricing, timelines, payment, support and services."}[lang]
    title = {"uz": "Savol-javob (FAQ)", "ru": "Вопросы и ответы (FAQ)", "en": "FAQ"}[lang]
    seo_title = {
        "uz": "Savol-javob — narx, muddat va ish jarayoni | promtchi",
        "ru": "Вопросы и ответы — цены, сроки и процесс работы | promtchi",
        "en": "FAQ — pricing, timelines and how we work | promtchi",
    }[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=seo_title, desc=desc,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["faq"], None)])
    ctx.update(items=items, t_h1=title, faq_schema=seo.json_ld(seo.faq_schema(items)))
    return templates.TemplateResponse(request, "faq.html", ctx)


# ══════════ BIZ HAQIMIZDA ══════════

@router.get("/{lang}/biz-haqimizda/", response_class=HTMLResponse)
async def about_page(request: Request, lang: str):
    _check_lang(lang)
    path_by_lang = {l: f"/{l}/biz-haqimizda/" for l in LANGS}
    a = ABOUT[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=a["title"], desc=a["meta"],
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["about"], None)])
    # Real jamoa a'zolarining ism/rasm/bio'sini ko'rsatish uchun ularning roziligi
    # biznes tomonidan hali tasdiqlanmagan (TZ 12/29-bo'lim) — shu sabab bu yerda
    # ismlar EMAS, faqat umumiy "Bizning ekspertiza" bloki (a.team_title/team_lead,
    # app/content/about.py) ko'rsatiladi. Rozilik kelgach shu yerga real profillar
    # (TeamIn: name/role/photo) qo'shiladi.
    ctx.update(a=a, faq_schema=seo.json_ld(seo.faq_schema(a["entity_qa"])))
    return templates.TemplateResponse(request, "about.html", ctx)


@router.get("/{lang}/jamoa/", include_in_schema=False)
async def team_redirect(lang: str):
    """TZ 3.2 route ro'yxatida /{lang}/jamoa/ tavsiya etilgan, lekin real jamoa
    profillari hali alohida sahifa uchun tayyor emas (TZ 12/29-bo'lim — rozilik
    kutilmoqda). Bo'sh/thin sahifa yoki 404 o'rniga /biz-haqimizda/ dagi mavjud
    "Bizning ekspertiza" blokiga 301 — profillar tasdiqlangach shu yerga
    to'liq /jamoa/ sahifasi qo'shilishi mumkin."""
    _check_lang(lang)
    return RedirectResponse(f"/{lang}/biz-haqimizda/", status_code=301)


# ══════════ ALOQA ══════════

@router.get("/{lang}/aloqa/", response_class=HTMLResponse)
async def contact_page(request: Request, lang: str):
    _check_lang(lang)
    path_by_lang = {l: f"/{l}/aloqa/" for l in LANGS}
    title = {"uz": "Aloqa", "ru": "Контакты", "en": "Contact"}[lang]
    seo_title = {
        "uz": "Aloqa — loyihangizni muhokama qilamiz | promtchi",
        "ru": "Контакты — обсудим ваш проект | promtchi",
        "en": "Contact — let's discuss your project | promtchi",
    }[lang]
    desc = {"uz": "promtchi bilan bog'laning — Telegram, email yoki forma orqali. 24 soat ichida javob beramiz.",
            "ru": "Свяжитесь с promtchi — через Telegram, email или форму. Ответим в течение 24 часов.",
            "en": "Get in touch with promtchi — via Telegram, email or the form. We reply within 24 hours."}[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=seo_title, desc=desc,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["contact"], None)])
    sub = {"uz": "G'oyangizni yozing — 24 soat ichida bog'lanamiz.",
           "ru": "Опишите идею — свяжемся с вами в течение 24 часов.",
           "en": "Write down your idea — we'll get back to you within 24 hours."}[lang]
    ctx.update(t_h1=title, t_sub=sub, project_types=PROJECT_TYPE_OPTIONS[lang])
    return templates.TemplateResponse(request, "contact.html", ctx)


# ══════════ MAXFIYLIK SIYOSATI / FOYDALANISH SHARTLARI ══════════

async def _legal_page(request: Request, lang: str, doc_key: str, docs: dict):
    doc = docs[lang]
    path_by_lang = {l: f"/{l}/{LEGAL_SLUGS[doc_key][l]}/" for l in LANGS}
    ctx = await _base_ctx(request, lang, path_by_lang, title=doc["title"], desc=doc["meta"],
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (doc["h1"], None)])
    ctx.update(doc=doc, legal_label=LEGAL_LABEL[lang], updated_label=UPDATED_LABEL[lang], updated_date=UPDATED_DATE)
    return templates.TemplateResponse(request, "legal.html", ctx)


# Har til o'z slug'iga ega (TZ 3.3) — {lang} path param emas, aks holda
# masalan /ru/maxfiylik-siyosati/ noto'g'ri (uz) tilda render bo'lardi.
for _l in LANGS:
    def _mk_privacy(lang=_l):
        async def handler(request: Request):
            return await _legal_page(request, lang, "privacy", PRIVACY)
        return handler

    def _mk_terms(lang=_l):
        async def handler(request: Request):
            return await _legal_page(request, lang, "terms", TERMS)
        return handler

    router.add_api_route(f"/{_l}/{LEGAL_SLUGS['privacy'][_l]}/", _mk_privacy(),
                          methods=["GET"], response_class=HTMLResponse)
    router.add_api_route(f"/{_l}/{LEGAL_SLUGS['terms'][_l]}/", _mk_terms(),
                          methods=["GET"], response_class=HTMLResponse)


# ══════════ /{lang}/ ni majburiy trailing-slash'siz variantlar uchun redirect ══════════
# (masalan /uz/aloqa -> /uz/aloqa/) — hreflang/canonical bitta shaklga ega bo'lishi uchun.


# ══════════ BLOG (mavjud Post admin CRUD'idan — app/main.py) ══════════

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, post_id: int) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _SLUG_RE.sub("-", norm.lower()).strip("-")[:80] or "post"
    return f"{slug}-{post_id}"


def _post_id_from_slug(slug: str) -> int | None:
    m = re.search(r"-(\d+)$", slug)
    return int(m.group(1)) if m else None


@router.get("/{lang}/blog/", response_class=HTMLResponse)
async def blog_index(request: Request, lang: str):
    _check_lang(lang)
    path_by_lang = {l: f"/{l}/blog/" for l in LANGS}
    title = {"uz": "Blog", "ru": "Блог", "en": "Blog"}[lang]
    desc = {"uz": "promtchi blogi — AI, avtomatlashtirish, CRM/ERP va dasturiy ta'minot haqida amaliy maqolalar: nimadan boshlash va qaysi yechim kimga mos.",
            "ru": "Блог promtchi — практические статьи об AI, автоматизации, CRM/ERP и разработке ПО: с чего начать и какое решение кому подходит.",
            "en": "The promtchi blog — practical articles on AI, automation, CRM/ERP and software development: where to start and which solution fits whom."}[lang]
    async with SessionLocal() as session:
        res = await session.execute(
            select(Post).where(Post.published == True, Post.lang == lang)  # noqa: E712
            .order_by(Post.created_at.desc(), Post.id.desc()).limit(50)
        )
        rows = res.scalars().all()
    posts = [{
        "slug": _slugify(p.title, p.id),
        "title": p.title,
        "date": p.created_at.strftime("%Y-%m-%d"),
        "category": p.category,
        "excerpt": p.excerpt or ((p.body[:150] + "…") if len(p.body) > 150 else p.body),
    } for p in rows]
    empty = {"uz": "Hozircha maqolalar yo'q — tez orada qo'shiladi.",
             "ru": "Пока нет статей — скоро появятся.",
             "en": "No articles yet — coming soon."}[lang]
    seo_title = {
        "uz": "Blog — avtomatlashtirish, CRM va AI haqida | promtchi",
        "ru": "Блог — об автоматизации, CRM и AI | promtchi",
        "en": "Blog — automation, CRM and AI insights | promtchi",
    }[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=seo_title, desc=desc,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["blog"], None)])
    ctx.update(posts=posts, t_h1=title, t_empty=empty)
    return templates.TemplateResponse(request, "blog_index.html", ctx)


@router.get("/{lang}/blog/{slug}/", response_class=HTMLResponse)
async def blog_detail(request: Request, lang: str, slug: str):
    _check_lang(lang)
    post_id = _post_id_from_slug(slug)
    p = None
    if post_id is not None:
        async with SessionLocal() as session:
            p = await session.get(Post, post_id)
    if p is None or not p.published or p.lang != lang or _slugify(p.title, p.id) != slug:
        # Sarlavha/til o'zgarib eski slug ishlamay qolgan bo'lishi mumkin —
        # 404'dan oldin redirect jadvalini tekshiramiz (TZ 27-bo'lim).
        new_path = await services_store.find_redirect(f"/{lang}/blog/{slug}/")
        if new_path:
            return RedirectResponse(new_path, status_code=301)
        raise HTTPException(404, "Post topilmadi")
    # Boshqa 2 til uchun mos tarjima yo'q — til almashtirgich o'sha tilning
    # blog ro'yxatiga tushadi, lekin <head> hreflang faqat o'z tiliga beriladi
    # (yolg'on "tarjima bor" da'vosi qilinmasin).
    own_path = f"/{lang}/blog/{slug}/"
    path_by_lang = {l: (own_path if l == lang else f"/{l}/blog/") for l in LANGS}
    excerpt = p.excerpt or ((p.body[:160] + "…") if len(p.body) > 160 else p.body)
    seo_title = p.seo_title or f"{p.title} — promtchi®"
    seo_desc = p.seo_description or excerpt
    ctx = await _base_ctx(request, lang, path_by_lang, title=seo_title, desc=seo_desc,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"),
                                  (NAV[lang]["blog"], f"/{lang}/blog/"), (p.title, None)],
                     og_type="article", noindex=p.noindex, hreflang_paths={lang: own_path},
                     og_image=_abs_image(p.image))
    canonical_url = seo.abs_url(own_path)
    tags = _post_tags(p.tags)
    services_by_key = {sv["key"]: sv for sv in await services_store.get_services()}
    # `tags` tartibi muhim — birinchi mos keluvchi xizmat "asosiy" hisoblanadi
    # (masalan ERP/CRM'ni solishtiruvchi maqolada birinchi tag ERP'ni belgilaydi).
    related_service = next((services_by_key[t] for t in tags if t in services_by_key), None)
    ctx.update(
        p={
            "title": p.title, "body_html": render_body(p.body), "image": p.image,
            "date": p.created_at.strftime("%Y-%m-%d"),
            "category": p.category,
            "tags": tags,
            "author": p.author,
        },
        related_service=({"slug": related_service["slugs"][lang], "nav": related_service[lang]["nav"]}
                          if related_service else None),
        article_schema=seo.json_ld(seo.article_schema(
            p.title, excerpt, canonical_url, p.created_at.date().isoformat(), p.image, lang)),
    )
    return templates.TemplateResponse(request, "blog_detail.html", ctx)


# ══════════ SITEMAP / ROBOTS ══════════

def _day(iso: str | None) -> str | None:
    """ISO vaqt tamg'asidan YYYY-MM-DD — sitemap <lastmod> uchun."""
    return iso.split("T")[0] if iso else None


def _newest(rows: list[dict]) -> str | None:
    days = [d for d in (_day(r.get("updated_at")) for r in rows) if d]
    return max(days) if days else None


async def _all_urls() -> list[tuple[dict, str]]:
    """[(path_by_lang, lastmod_hint), ...] — har biri uchun hreflang alternate qatorlari chiqadi.

    lastmod FAQAT kontenti qachon o'zgargani REAL ma'lum bo'lgan sahifalarga
    qo'yiladi (DB qatorining `updated_at`i): xizmat/portfolio sahifalari, ularning
    indekslari va blog. Statik kontentli sahifalarga (bosh sahifa, yechimlar,
    biz haqimizda, aloqa, huquqiy sahifalar) sana YOZILMAYDI — hammasiga bir xil
    "bugun"ni yozish noto'g'ri signal bo'lardi va Google bunday lastmod'ga
    ishonishni to'xtatadi.
    """
    services = await services_store.get_services()
    cases = await services_store.get_cases()
    async with SessionLocal() as session:
        blog_last = await session.scalar(
            select(func.max(Post.updated_at)).where(Post.published == True, Post.noindex == False)  # noqa: E712
        )
    blog_day = blog_last.date().isoformat() if blog_last else None
    urls = []
    for l in LANGS:
        urls.append(({lang: f"/{lang}/" for lang in LANGS}, None))
    for sv in services:
        urls.append(({l: f"/{l}/xizmatlar/" for l in LANGS}, _newest(services)))
    for sv in services:
        urls.append(({l: f"/{l}/xizmatlar/{sv['slugs'][l]}/" for l in LANGS}, _day(sv.get("updated_at"))))
    for k in SOLUTION_KEYS:
        urls.append(({l: f"/{l}/yechimlar/" for l in LANGS}, None))
    for k in SOLUTION_KEYS:
        urls.append(({l: f"/{l}/yechimlar/{SOLUTION_SLUGS[k][l]}/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/portfolio/" for l in LANGS}, _newest(cases)))
    for c in cases:
        urls.append(({l: f"/{l}/portfolio/{c['slugs'][l]}/" for l in LANGS}, _day(c.get("updated_at"))))
    urls.append(({l: f"/{l}/faq/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/biz-haqimizda/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/aloqa/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/blog/" for l in LANGS}, blog_day))
    urls.append(({l: f"/{l}/{LEGAL_SLUGS['privacy'][l]}/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/{LEGAL_SLUGS['terms'][l]}/" for l in LANGS}, None))
    # duplikatlarni olib tashlaymiz (services_index N marta qo'shildi — soddalik uchun)
    seen = set()
    uniq = []
    for path_by_lang, hint in urls:
        key = path_by_lang["uz"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append((path_by_lang, hint))
    return uniq


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(request: Request):
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for path_by_lang, hint in await _all_urls():
        for lang in LANGS:
            loc = seo.abs_url(path_by_lang[lang])
            alt_tags = "".join(
                f'<xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>'
                for h, u in seo.alternates(path_by_lang)
            )
            lastmod = f"<lastmod>{hint}</lastmod>" if hint else ""
            parts.append(f"<url><loc>{loc}</loc>{lastmod}{alt_tags}</url>")
    # blog postlari — real DB'dan; noindex postlar va boshqa tilning
    # mavjud bo'lmagan "tarjimasi" (hreflang alternate) sitemap'ga qo'shilmaydi.
    async with SessionLocal() as session:
        res = await session.execute(
            select(Post).where(Post.published == True, Post.noindex == False)  # noqa: E712
        )
        for p in res.scalars().all():
            slug = _slugify(p.title, p.id)
            own_path = f"/{p.lang}/blog/{slug}/"
            loc = seo.abs_url(own_path)
            lastmod = (p.updated_at or p.created_at).date().isoformat()
            alt_tags = "".join(
                f'<xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>'
                for h, u in seo.alternates({p.lang: own_path})
            )
            parts.append(f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>{alt_tags}</url>")
    parts.append("</urlset>")
    return Response("".join(parts), media_type="application/xml")


# Brauzerlar va ba'zi kroulerlar faviconni HTML'dagi <link>dan qat'i nazar
# ildizdan (/favicon.ico) so'raydi — ilgari bu 404 qaytarardi.
_FAVICON = Path(__file__).resolve().parent.parent / "static" / "favicon.ico"


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(
        _FAVICON,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=604800"},
    )


@router.get("/robots.txt", include_in_schema=False)
async def robots():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/admin/\n"
        # Interaktiv API hujjatlari qidiruv natijasida chiqmasligi kerak
        # (ENABLE_DOCS=false bo'lganda ular umuman ochilmaydi — bu esa
        # yoqib qo'yilgan holat uchun qo'shimcha himoya).
        "Disallow: /docs\n"
        "Disallow: /redoc\n"
        "Disallow: /openapi.json\n"
        f"Sitemap: {settings.SITE_URL}/sitemap.xml\n"
    )
    return Response(body, media_type="text/plain")


# ══════════ 404 (til-mos) ══════════

@router.get("/{lang}/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def lang_404(request: Request, lang: str, full_path: str):
    lang = lang if lang in LANGS else "uz"
    path_by_lang = {l: f"/{l}/" for l in LANGS}
    ctx = await _base_ctx(request, lang, path_by_lang,
                     title=f"{COMMON[lang]['not_found_title']} — promtchi®",
                     desc=COMMON[lang]["not_found_body"])
    ctx.update(is_404=True)
    return templates.TemplateResponse(request, "404.html", ctx, status_code=404)
