"""2-bosqich SEO tuzatishlari (2026-09-17, SEO_IMPLEMENTATION_REPORT.md) regressiyalari.

Bu testlar audit'da topilgan muammolar QAYTIB KELMASLIGINI tekshiradi:
- title'lar search-intent'ga mos va tillar bo'yicha takrorlanmaydi
- portfolio case title'lari uz/ru/en'da bir xil emas
- /favicon.ico ildizdan 200 qaytaradi
- og:image 1200x630 banner (256x256 logotip emas)
- JSON-LD'da bitta Organization tuguni (@id) va unga havolalar
- sitemap: faqat real `updated_at` bo'lgan sahifalarda lastmod
- /docs, /api/*, /admin indekslanmaydi (robots.txt + X-Robots-Tag)
- Search Console metasi faqat token berilganda chiqadi
"""
import xml.etree.ElementTree as ET

import pytest

SM_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ── title'lar ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path,must_contain", [
    ("/uz/xizmatlar/", "CRM/ERP"),
    ("/ru/xizmatlar/", "CRM/ERP"),
    ("/en/xizmatlar/", "CRM/ERP"),
    ("/uz/yechimlar/", "savdo"),
    ("/uz/portfolio/", "keys"),
    ("/uz/faq/", "narx"),
    ("/uz/aloqa/", "loyiha"),
    ("/uz/blog/", "CRM"),
])
def test_index_titles_are_search_intent_aligned(client, path, must_contain):
    """Ilgari "Xizmatlar — promtchi®" kabi 20 belgilik, kalit so'zsiz title edi."""
    html = client.get(path).text
    title = html.split("<title>")[1].split("</title>")[0]
    assert must_contain.lower() in title.lower(), title
    assert 30 <= len(title) <= 65, f"{len(title)}: {title}"


def test_index_h1_not_changed_by_title_rewrite(client):
    """<title> alohida o'zgaruvchida — H1 qisqa va o'z holicha qolishi kerak."""
    html = client.get("/uz/xizmatlar/").text
    h1 = html.split("<h1")[1].split(">", 1)[1].split("</h1>")[0].strip()
    assert h1 == "Xizmatlar", h1


def test_portfolio_case_titles_differ_per_language(client):
    """Uch tilda ham "Chindan Group — promtchi®" edi — endi case'ning `cat`i bilan farqlanadi."""
    titles = {}
    for lang in ("uz", "ru", "en"):
        r = client.get(f"/{lang}/portfolio/chindan-group/")
        assert r.status_code == 200
        titles[lang] = r.text.split("<title>")[1].split("</title>")[0]
    assert len(set(titles.values())) == 3, titles
    assert all("Chindan Group" in t for t in titles.values())


def test_no_duplicate_titles_across_main_pages(client):
    paths = [f"/{lang}/{p}" for lang in ("uz", "ru", "en")
             for p in ("", "xizmatlar/", "yechimlar/", "portfolio/", "faq/", "aloqa/", "blog/")]
    titles = []
    for p in paths:
        r = client.get(p)
        if r.status_code == 200 and "<title>" in r.text:
            titles.append(r.text.split("<title>")[1].split("</title>")[0])
    assert len(titles) == len(set(titles)), "takroriy title bor"


# ── favicon / og:image ───────────────────────────────────────────────────────

def test_favicon_ico_served_from_root(client):
    """Ilgari /favicon.ico 404 qaytarardi."""
    r = client.get("/favicon.ico")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/x-icon"
    assert len(r.content) > 500


def test_og_image_is_wide_banner_with_dimensions(client):
    html = client.get("/uz/faq/").text
    assert 'property="og:image" content="https://promtchi.uz/static/og-cover.png"' in html
    assert 'property="og:image:width" content="1200"' in html
    assert 'property="og:image:height" content="630"' in html
    assert 'name="twitter:card" content="summary_large_image"' in html
    assert "/static/logo.png" not in html.split("</head>")[0].split("og:image")[1][:200]


# ── JSON-LD grafi ────────────────────────────────────────────────────────────

def test_schema_graph_uses_single_organization_node(client):
    import json
    import re
    html = client.get("/uz/xizmatlar/crm/").text
    blocks = [json.loads(m) for m in
              re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)]
    by_type = {b.get("@type"): b for b in blocks}
    org = by_type["Organization"]
    assert org["@id"].endswith("/#organization")
    assert org["logo"]["@type"] == "ImageObject"
    assert by_type["WebSite"]["publisher"] == {"@id": org["@id"]}
    assert by_type["Service"]["provider"] == {"@id": org["@id"]}


# ── sitemap lastmod ──────────────────────────────────────────────────────────

def test_sitemap_lastmod_only_where_real_timestamp_exists(client):
    root = ET.fromstring(client.get("/sitemap.xml").text)
    urls = {u.find("s:loc", SM_NS).text: u.find("s:lastmod", SM_NS) for u in root.findall("s:url", SM_NS)}
    # xizmat sahifasida DB `updated_at` bor — lastmod bo'lishi kerak
    svc = [u for u in urls if "/uz/xizmatlar/" in u and u.count("/") > 4]
    assert svc and urls[svc[0]] is not None
    # bosh sahifa statik — sun'iy sana yozilmasligi kerak
    assert urls["https://promtchi.uz/uz/"] is None
    for lm in (v for v in urls.values() if v is not None):
        assert len(lm.text) == 10 and lm.text[4] == "-", lm.text


def test_sitemap_still_valid_and_complete(client):
    """Regressiya: lastmod qo'shilishi URL ro'yxatini buzmasligi kerak."""
    root = ET.fromstring(client.get("/sitemap.xml").text)
    locs = [u.find("s:loc", SM_NS).text for u in root.findall("s:url", SM_NS)]
    assert len(locs) == len(set(locs)) and len(locs) > 60
    for lang in ("uz", "ru", "en"):
        assert f"https://promtchi.uz/{lang}/" in locs


# ── indekslanmasligi kerak bo'lgan yo'llar ───────────────────────────────────

def test_robots_disallows_api_docs(client):
    body = client.get("/robots.txt").text
    for line in ("Disallow: /docs", "Disallow: /redoc", "Disallow: /openapi.json"):
        assert line in body
    assert "Allow: /" in body and "Sitemap: https://promtchi.uz/sitemap.xml" in body


@pytest.mark.parametrize("path", ["/api/content?lang=uz", "/admin"])
def test_private_paths_marked_noindex(client, path):
    r = client.get(path)
    assert r.headers.get("x-robots-tag") == "noindex, nofollow", path


@pytest.mark.parametrize("path", ["/uz/", "/uz/faq/", "/uz/xizmatlar/crm/"])
def test_public_pages_not_marked_noindex(client, path):
    assert "x-robots-tag" not in client.get(path).headers, path


# ── Search Console metasi ────────────────────────────────────────────────────

def test_no_verification_meta_without_token(client):
    """Token o'rnatilmagan — soxta/taxminiy meta chiqmasligi kerak."""
    for path in ("/uz/", "/uz/faq/"):
        assert "google-site-verification" not in client.get(path).text
