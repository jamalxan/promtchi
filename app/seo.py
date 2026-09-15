"""SEO yordamchilari — canonical/hreflang havolalar va JSON-LD schema quruvchilar.

Barcha ichki SSR sahifalar (app/pages.py) shu yerdagi funksiyalardan foydalanadi;
bitta manbadan boshqarilgani uchun hreflang/canonical/schema doim izchil bo'ladi.
"""
import json

from .config import settings
from .content import LANGS
from .content.common import ORG

SITE_URL = settings.SITE_URL.rstrip("/")


def abs_url(path: str) -> str:
    """`/uz/xizmatlar/` kabi nisbiy yo'lni to'liq URL'ga aylantiradi."""
    if not path.startswith("/"):
        path = "/" + path
    return SITE_URL + path


def hreflang_code(lang: str) -> str:
    return {"uz": "uz-UZ", "ru": "ru-RU", "en": "en"}.get(lang, lang)


def alternates(path_by_lang: dict) -> list[tuple[str, str]]:
    """hreflang -> to'liq URL juftliklari, shu jumladan x-default (uz).

    path_by_lang: {"uz": "/uz/...", "ru": "/ru/...", "en": "/en/..."}
    """
    pairs = [(hreflang_code(lang), abs_url(path_by_lang[lang])) for lang in LANGS if lang in path_by_lang]
    if "uz" in path_by_lang:
        pairs.append(("x-default", abs_url(path_by_lang["uz"])))
    return pairs


def json_ld(data: dict) -> str:
    """<script type="application/ld+json"> ichiga qo'yiladigan xavfsiz JSON matn.

    `</script>` injektsiyasining oldini olish uchun '<' escape qilinadi.
    """
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def organization_schema() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": ORG["name"],
        "url": SITE_URL + "/",
        "logo": ORG["logo"],
        "foundingDate": ORG["founded"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": ORG["city_en"],
            "addressCountry": "UZ",
        },
        "contactPoint": [{
            "@type": "ContactPoint",
            "contactType": "customer service",
            "email": ORG["email"],
            "telephone": ORG["phone"],
            "url": ORG["telegram_url"],
            "areaServed": "UZ",
            "availableLanguage": ["uz", "ru", "en"],
        }],
        "sameAs": [ORG["telegram_url"], ORG["instagram_url"]],
    }


def website_schema(lang: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "promtchi",
        "url": abs_url(f"/{lang}/"),
        "inLanguage": hreflang_code(lang),
    }


def breadcrumb_schema(items: list) -> dict:
    """items: [(name, url_path_or_None), ...] — oxirgisi joriy sahifa (url shart emas)."""
    els = []
    for i, (name, path) in enumerate(items, start=1):
        entry = {"@type": "ListItem", "position": i, "name": name}
        if path:
            entry["item"] = abs_url(path)
        els.append(entry)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": els}


def service_schema(name: str, description: str, url: str, lang: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": name,
        "description": description,
        "url": url,
        "provider": {"@type": "Organization", "name": "promtchi", "url": SITE_URL + "/"},
        "areaServed": "UZ",
        "inLanguage": hreflang_code(lang),
    }


def faq_schema(items: list) -> dict:
    """items: [(question, answer_html_or_text), ...]"""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in items
        ],
    }


def article_schema(title: str, description: str, url: str, date_published: str, image: str, lang: str) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "url": url,
        "datePublished": date_published,
        "author": {"@type": "Organization", "name": "promtchi"},
        "publisher": {"@type": "Organization", "name": "promtchi", "logo": {"@type": "ImageObject", "url": ORG["logo"]}},
        "inLanguage": hreflang_code(lang),
    }
    if image:
        data["image"] = image
    return data
