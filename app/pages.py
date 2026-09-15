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
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from . import seo, services_store
from .config import settings
from .content import LANGS
from .content.about import ABOUT
from .content.common import COMMON, FOOTER, LANG_NAMES, LANG_SHORT, NAV, ORG, PROJECT_TYPE_OPTIONS
from .content.faq import FAQ
from .content.legal import LEGAL_LABEL, LEGAL_SLUGS, PRIVACY, TERMS, UPDATED_DATE, UPDATED_LABEL
from .content.solutions import SLUGS as SOLUTION_SLUGS, SOLUTION_KEYS, SOLUTIONS
from .db import Content, Post, SessionLocal

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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


async def _base_ctx(request: Request, lang: str, path_by_lang: dict, title: str, desc: str,
                     breadcrumbs: list | None = None, og_type: str = "website") -> dict:
    canonical = seo.abs_url(path_by_lang[lang])
    alt = seo.alternates(path_by_lang)
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
        "org": org,
        "nav": NAV[lang],
        "footer": FOOTER[lang],
        "common": COMMON[lang],
        "page_title": title,
        "page_desc": desc,
        "ga_id": settings.GA_MEASUREMENT_ID,
        "legal": {
            "privacy": f"/{lang}/{LEGAL_SLUGS['privacy'][lang]}/",
            "terms": f"/{lang}/{LEGAL_SLUGS['terms'][lang]}/",
        },
        "org_schema": seo.json_ld(seo.organization_schema(org)),
        "website_schema": seo.json_ld(seo.website_schema(lang)),
        "breadcrumb_schema": crumb_schema,
        "breadcrumbs": crumbs_nav,
    }


def _service_cards(lang: str, services: list) -> list:
    return [{"slug": s["slugs"][lang], "nav": s[lang]["nav"], "value": s[lang]["value"]} for s in services]


def _case_cards(lang: str, cases: list, exclude: str | None = None) -> list:
    return [{"slug": c["slugs"][lang], **c[lang]} for c in cases if c["key"] != exclude]


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
    title = {"uz": "Xizmatlar", "ru": "Услуги", "en": "Services"}[lang]
    ctx = await _base_ctx(request, lang, path_by_lang,
                     title=f"{title} — promtchi®", desc=intro,
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
    ctx.update(
        s={**s, "slug": slug},
        all_services=_service_cards(lang, services),
        related_cases=_case_cards(lang, cases)[:2],
        service_schema=seo.json_ld(seo.service_schema(s["h1"], s["value"], canonical_url, lang)),
        faq_schema=seo.json_ld(seo.faq_schema(s["faq"])) if s.get("faq") else None,
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
    title = {"uz": "Yechimlar", "ru": "Решения", "en": "Solutions"}[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=f"{title} — promtchi®", desc=intro,
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
    title = {"uz": "Portfolio", "ru": "Портфолио", "en": "Portfolio"}[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=f"{title} — promtchi®", desc=intro,
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
    ctx = await _base_ctx(request, lang, path_by_lang, title=f"{c['title']} — promtchi®", desc=c["meta"],
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"),
                                  (NAV[lang]["portfolio"], f"/{lang}/portfolio/"),
                                  (c["title"], None)])
    ctx.update(c={**c, "slug": slug}, other_cases=_case_cards(lang, cases, exclude=match["key"]))
    return templates.TemplateResponse(request, "portfolio_detail.html", ctx)


# ══════════ FAQ ══════════

@router.get("/{lang}/faq/", response_class=HTMLResponse)
async def faq_page(request: Request, lang: str):
    _check_lang(lang)
    path_by_lang = {l: f"/{l}/faq/" for l in LANGS}
    items = FAQ[lang]
    desc = {"uz": "promtchi haqida ko'p so'raladigan savollar: narx, muddat, to'lov, texnik yordam va xizmatlar.",
            "ru": "Часто задаваемые вопросы о promtchi: цена, сроки, оплата, техподдержка и услуги.",
            "en": "Frequently asked questions about promtchi: pricing, timelines, payment, support and services."}[lang]
    title = {"uz": "Savol-javob (FAQ)", "ru": "Вопросы и ответы (FAQ)", "en": "FAQ"}[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=f"{title} — promtchi®", desc=desc,
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
    team = [
        {"name": "G'iyosiddin Tursunxo'jayev", "role": {"uz": "Founder", "ru": "Основатель", "en": "Founder"}[lang]},
        {"name": "Jamolxon Yo'ldashaliyev", "role": {"uz": "Co-Founder", "ru": "Сооснователь", "en": "Co-Founder"}[lang]},
        {"name": "Abbos Setdarov", "role": {"uz": "IT Specialist", "ru": "IT-специалист", "en": "IT Specialist"}[lang]},
        {"name": "Samandar Orifjonov", "role": {"uz": "IT Specialist", "ru": "IT-специалист", "en": "IT Specialist"}[lang]},
    ]
    ctx.update(a=a, team=team)
    return templates.TemplateResponse(request, "about.html", ctx)


# ══════════ ALOQA ══════════

@router.get("/{lang}/aloqa/", response_class=HTMLResponse)
async def contact_page(request: Request, lang: str):
    _check_lang(lang)
    path_by_lang = {l: f"/{l}/aloqa/" for l in LANGS}
    title = {"uz": "Aloqa", "ru": "Контакты", "en": "Contact"}[lang]
    desc = {"uz": "promtchi bilan bog'laning — Telegram, email yoki forma orqali. 24 soat ichida javob beramiz.",
            "ru": "Свяжитесь с promtchi — через Telegram, email или форму. Ответим в течение 24 часов.",
            "en": "Get in touch with promtchi — via Telegram, email or the form. We reply within 24 hours."}[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=f"{title} — promtchi®", desc=desc,
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
    desc = {"uz": "promtchi blogi — AI, avtomatlashtirish, CRM/ERP va dasturiy ta'minot haqida maqolalar.",
            "ru": "Блог promtchi — статьи об AI, автоматизации, CRM/ERP и разработке ПО.",
            "en": "The promtchi blog — articles on AI, automation, CRM/ERP and software development."}[lang]
    async with SessionLocal() as session:
        res = await session.execute(
            select(Post).where(Post.published == True).order_by(Post.created_at.desc(), Post.id.desc()).limit(50)  # noqa: E712
        )
        rows = res.scalars().all()
    posts = [{
        "slug": _slugify(p.title, p.id),
        "title": p.title,
        "date": p.created_at.strftime("%Y-%m-%d"),
        "excerpt": (p.body[:150] + "…") if len(p.body) > 150 else p.body,
    } for p in rows]
    empty = {"uz": "Hozircha maqolalar yo'q — tez orada qo'shiladi.",
             "ru": "Пока нет статей — скоро появятся.",
             "en": "No articles yet — coming soon."}[lang]
    ctx = await _base_ctx(request, lang, path_by_lang, title=f"{title} — promtchi®", desc=desc,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"), (NAV[lang]["blog"], None)])
    ctx.update(posts=posts, t_h1=title, t_empty=empty)
    return templates.TemplateResponse(request, "blog_index.html", ctx)


@router.get("/{lang}/blog/{slug}/", response_class=HTMLResponse)
async def blog_detail(request: Request, lang: str, slug: str):
    _check_lang(lang)
    post_id = _post_id_from_slug(slug)
    if post_id is None:
        raise HTTPException(404, "Post topilmadi")
    async with SessionLocal() as session:
        p = await session.get(Post, post_id)
    if p is None or not p.published or _slugify(p.title, p.id) != slug:
        raise HTTPException(404, "Post topilmadi")
    path_by_lang = {l: f"/{l}/blog/{slug}/" for l in LANGS}
    excerpt = (p.body[:160] + "…") if len(p.body) > 160 else p.body
    ctx = await _base_ctx(request, lang, path_by_lang, title=f"{p.title} — promtchi®", desc=excerpt,
                     breadcrumbs=[(NAV[lang]["home"], f"/{lang}/"),
                                  (NAV[lang]["blog"], f"/{lang}/blog/"), (p.title, None)],
                     og_type="article")
    canonical_url = seo.abs_url(path_by_lang[lang])
    ctx.update(
        p={"title": p.title, "body": p.body, "image": p.image, "date": p.created_at.strftime("%Y-%m-%d")},
        article_schema=seo.json_ld(seo.article_schema(
            p.title, excerpt, canonical_url, p.created_at.date().isoformat(), p.image, lang)),
    )
    return templates.TemplateResponse(request, "blog_detail.html", ctx)


# ══════════ SITEMAP / ROBOTS ══════════

async def _all_urls() -> list[tuple[dict, str]]:
    """[(path_by_lang, lastmod_hint), ...] — har biri uchun hreflang alternate qatorlari chiqadi."""
    services = await services_store.get_services()
    cases = await services_store.get_cases()
    urls = []
    for l in LANGS:
        urls.append(({lang: f"/{lang}/" for lang in LANGS}, None))
    for sv in services:
        urls.append(({l: f"/{l}/xizmatlar/" for l in LANGS}, None))
    for sv in services:
        urls.append(({l: f"/{l}/xizmatlar/{sv['slugs'][l]}/" for l in LANGS}, None))
    for k in SOLUTION_KEYS:
        urls.append(({l: f"/{l}/yechimlar/" for l in LANGS}, None))
    for k in SOLUTION_KEYS:
        urls.append(({l: f"/{l}/yechimlar/{SOLUTION_SLUGS[k][l]}/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/portfolio/" for l in LANGS}, None))
    for c in cases:
        urls.append(({l: f"/{l}/portfolio/{c['slugs'][l]}/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/faq/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/biz-haqimizda/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/aloqa/" for l in LANGS}, None))
    urls.append(({l: f"/{l}/blog/" for l in LANGS}, None))
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
    for path_by_lang, _hint in await _all_urls():
        for lang in LANGS:
            loc = seo.abs_url(path_by_lang[lang])
            alt_tags = "".join(
                f'<xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>'
                for h, u in seo.alternates(path_by_lang)
            )
            parts.append(f"<url><loc>{loc}</loc>{alt_tags}</url>")
    # blog postlari — real DB'dan
    async with SessionLocal() as session:
        res = await session.execute(select(Post).where(Post.published == True))  # noqa: E712
        for p in res.scalars().all():
            slug = _slugify(p.title, p.id)
            path_by_lang = {l: f"/{l}/blog/{slug}/" for l in LANGS}
            for lang in LANGS:
                loc = seo.abs_url(path_by_lang[lang])
                lastmod = (p.updated_at or p.created_at).date().isoformat()
                alt_tags = "".join(
                    f'<xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>'
                    for h, u in seo.alternates(path_by_lang)
                )
                parts.append(f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>{alt_tags}</url>")
    parts.append("</urlset>")
    return Response("".join(parts), media_type="application/xml")


@router.get("/robots.txt", include_in_schema=False)
async def robots():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/admin/\n"
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
