"""IndexNow (Bing/Yandex tezkor indekslash), llms-full.txt va Article schema
regressiyalari (2026-10-15 SEO/GEO yakuniy audit).

- /{INDEXNOW_KEY}.txt kalit fayli faqat kalit sozlanganda va aynan mos
  kelganda 200 beradi (boshqa *.txt — 404)
- submit() to'g'ri JSON (host/key/keyLocation/urlList) yuboradi, 202 — ok,
  403 — rad; hech qachon exception ko'tarmaydi
- kalit bo'sh bo'lsa notify() hech narsa to'plamaydi (dev/test xavfsiz)
- admin POST /api/admin/seo/indexnow sitemap'dagi URL'lar sonini yuboradi
  (sitemap <loc> to'plami bilan aynan bir xil)
- /llms-full.txt — xizmat/yechim/FAQ/blog to'liq matni
- blog maqolasida Article.dateModified, absolyut image va article:* meta
"""
import asyncio
import json
import re
import xml.etree.ElementTree as ET

import httpx
import pytest

from app import indexnow
from app.config import settings

SM_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
KEY = "promtchitestkey0123456789abcdef"


class _FakeClient:
    def __init__(self, status: int = 202, raise_exc: Exception | None = None):
        self.status = status
        self.raise_exc = raise_exc
        self.calls: list[tuple[str, dict]] = []

    async def post(self, url, json=None, headers=None):  # noqa: A002 — httpx imzosi
        self.calls.append((url, json))
        if self.raise_exc:
            raise self.raise_exc
        return httpx.Response(self.status, request=httpx.Request("POST", url))


@pytest.fixture()
def indexnow_on(monkeypatch):
    """Kalit + soxta klient; testdan keyin yig'ilganlar tozalanadi."""
    fake = _FakeClient()
    monkeypatch.setattr(settings, "INDEXNOW_KEY", KEY)
    monkeypatch.setattr(indexnow, "client", fake)
    indexnow._pending.clear()
    yield fake
    indexnow._pending.clear()


# ── kalit fayli ──────────────────────────────────────────────────────────────

def test_key_file_404_when_not_configured(client):
    assert settings.INDEXNOW_KEY == ""  # conftest kafolati
    assert client.get(f"/{KEY}.txt").status_code == 404


def test_key_file_served_only_for_exact_key(client, indexnow_on):
    r = client.get(f"/{KEY}.txt")
    assert r.status_code == 200, r.text
    assert r.text == KEY
    assert r.headers["content-type"].startswith("text/plain")
    assert r.headers.get("x-robots-tag") == "noindex"
    assert client.get("/wrongkey00000000.txt").status_code == 404
    # robots/llms aniq yo'llari dinamik marshrutdan ustun qoladi
    assert "User-agent" in client.get("/robots.txt").text
    assert client.get("/llms.txt").text.startswith("# promtchi")


# ── submit / notify ──────────────────────────────────────────────────────────

def test_submit_posts_protocol_body(indexnow_on):
    ok = asyncio.run(indexnow.submit(["/uz/", "https://promtchi.uz/uz/faq/", "/uz/"]))
    assert ok is True
    assert len(indexnow_on.calls) == 1
    url, body = indexnow_on.calls[0]
    assert url == indexnow.ENDPOINT
    assert body["host"] == settings.CANONICAL_HOST
    assert body["key"] == KEY
    assert body["keyLocation"] == f"{settings.SITE_URL}/{KEY}.txt"
    # dublikat olib tashlandi, nisbiy yo'l absolyutga aylandi
    assert body["urlList"] == sorted({f"{settings.SITE_URL}/uz/", "https://promtchi.uz/uz/faq/"})
    assert indexnow.last_result["ok"] is True and indexnow.last_result["status"] == 202


def test_submit_rejection_and_network_error_never_raise(monkeypatch, indexnow_on):
    indexnow_on.status = 403
    assert asyncio.run(indexnow.submit(["/uz/"])) is False
    assert indexnow.last_result["status"] == 403
    monkeypatch.setattr(indexnow, "client", _FakeClient(raise_exc=httpx.ConnectError("down")))
    assert asyncio.run(indexnow.submit(["/uz/"])) is False
    assert indexnow.last_result["status"] is None


def test_submit_empty_is_noop(indexnow_on):
    assert asyncio.run(indexnow.submit([])) is True
    assert indexnow_on.calls == []


def test_notify_is_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "INDEXNOW_KEY", "")
    indexnow._pending.clear()
    indexnow.notify(["/uz/"])
    assert indexnow._pending == set()
    assert indexnow.enabled() is False


def test_notify_collects_and_flush_sends_once(indexnow_on):
    async def run():
        indexnow.notify(["/uz/blog/"])
        indexnow.notify(["/uz/blog/", "/uz/"])
        assert len(indexnow._pending) == 2
        return await indexnow.flush_now()

    assert asyncio.run(run()) is True
    assert len(indexnow_on.calls) == 1
    assert len(indexnow_on.calls[0][1]["urlList"]) == 2
    assert indexnow._pending == set()


# ── admin endpoint + sitemap muvofiqligi ─────────────────────────────────────

def test_admin_indexnow_requires_auth(client):
    client.cookies.clear()
    assert client.post("/api/admin/seo/indexnow").status_code in (401, 403)
    assert client.get("/api/admin/seo/indexnow").status_code in (401, 403)


def test_admin_indexnow_disabled_returns_400(admin_client):
    r = admin_client.post("/api/admin/seo/indexnow")
    assert r.status_code == 400
    st = admin_client.get("/api/admin/seo/indexnow").json()
    assert st["enabled"] is False and st["key_location"] is None


def test_admin_full_submit_matches_sitemap(admin_client, indexnow_on):
    sitemap = admin_client.get("/sitemap.xml").text
    locs = {el.text for el in ET.fromstring(sitemap).findall(".//s:loc", SM_NS)}
    r = admin_client.post("/api/admin/seo/indexnow")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["submitted"] == len(locs)
    sent = set(indexnow_on.calls[-1][1]["urlList"])
    assert sent == locs, sent ^ locs
    st = admin_client.get("/api/admin/seo/indexnow").json()
    assert st["enabled"] is True and st["key_location"].endswith(f"/{KEY}.txt")


def test_admin_post_create_notifies_post_and_index(admin_client, indexnow_on):
    r = admin_client.post("/api/admin/posts", json={
        "title": "IndexNow test maqola", "body": "Matn " * 20, "excerpt": "", "image": "",
        "video": "", "category": "", "tags": "", "author": "", "lang": "uz",
        "seo_title": "", "seo_description": "", "noindex": False, "published": True,
    })
    assert r.status_code == 201, r.text
    slug = r.json()["slug"]
    pending = set(indexnow._pending)
    assert f"{settings.SITE_URL}/uz/blog/{slug}/" in pending
    assert f"{settings.SITE_URL}/uz/blog/" in pending
    admin_client.delete(f"/api/admin/posts/{r.json()['id']}")


# ── llms-full.txt ────────────────────────────────────────────────────────────

def test_llms_full_txt_has_full_content(client):
    r = client.get("/llms-full.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    t = r.text
    assert t.startswith("# promtchi")
    assert "# Full content" in t
    for section in ("## Services (full)", "## Industry solutions (full)", "## Case studies (full)",
                    "## All FAQ", "## Blog articles"):
        assert section in t, section
    # xizmat sahifasining ichki bo'limlari (faqat ro'yxat emas)
    assert "### What is included" in t and "### FAQ" in t
    assert "URL: https://promtchi.uz/en/xizmatlar/" in t or f"URL: {settings.SITE_URL}/en/xizmatlar/" in t
    assert len(t) > len(client.get("/llms.txt").text) * 2


# ── Article schema ───────────────────────────────────────────────────────────

def test_blog_post_article_schema_and_meta(admin_client):
    r = admin_client.post("/api/admin/posts", json={
        "title": "Schema test maqola", "body": "Matn " * 20, "excerpt": "Qisqa", "image": "https://promtchi.uz/static/og-cover.png",
        "video": "", "category": "CRM", "tags": "crm, erp", "author": "", "lang": "uz",
        "seo_title": "", "seo_description": "", "noindex": False, "published": True,
    })
    assert r.status_code == 201, r.text
    pid, slug = r.json()["id"], r.json()["slug"]
    try:
        html = admin_client.get(f"/uz/blog/{slug}/").text
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        art = next(json.loads(b) for b in blocks if '"Article"' in b)
        assert art["datePublished"] == art["dateModified"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", art["dateModified"])
        assert art["image"].startswith("http"), art["image"]
        assert art["mainEntityOfPage"]["@id"] == art["url"]
        assert re.search(r'<meta property="article:published_time" content="\d{4}-\d{2}-\d{2}T', html)
        assert '<meta property="article:modified_time"' in html
        assert '<meta property="article:section" content="CRM">' in html
        assert '<meta property="article:tag" content="crm">' in html
        assert '<meta property="article:tag" content="erp">' in html
    finally:
        admin_client.delete(f"/api/admin/posts/{pid}")
