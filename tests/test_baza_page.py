"""/baza lead-magnit sahifasi: ochiladi, indekslanmaydi, aktivlari mavjud."""
import re


def test_baza_page_served(client):
    r = client.get("/baza")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert 'name="robots" content="noindex' in r.text
    assert 'name="viewport"' in r.text


def test_baza_trailing_slash_redirects(client):
    r = client.get("/baza/", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/baza"


def test_baza_assets_exist(client):
    html = client.get("/baza").text
    paths = set(re.findall(r'(/static/baza/[^"\')]+)', html))
    assert len(paths) == 6
    for p in paths:
        assert client.get(p).status_code == 200, p
