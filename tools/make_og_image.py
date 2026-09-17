"""OG preview rasmi (1200x630) va favicon.ico generatori.

Nega kerak: og:image sifatida 256x256 logotip ishlatilgan edi — ijtimoiy
tarmoq va qidiruv preview'lari uchun tavsiya etilgan o'lcham 1200x630.
Bu skript brend ranglari va saytning o'z fonti (Anton, OFL litsenziya —
sayt uni Google Fonts orqali yuklaydi) bilan bitta neytral banner chizadi:
uch til uchun ham mos bo'lishi kerak, shuning uchun matn minimal.

Ishlatish:  python tools/make_og_image.py
Natija:     static/og-cover.png, static/favicon.ico
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

BLK = (11, 11, 14)
CREAM = (252, 251, 247)
ACID = (217, 255, 63)
MUTED = (150, 150, 145)

ANTON_URL = "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf"
FONT_CACHE = ROOT / "tools" / "Anton-Regular.ttf"


def anton(size: int) -> ImageFont.FreeTypeFont:
    if not FONT_CACHE.exists():
        FONT_CACHE.write_bytes(urllib.request.urlopen(ANTON_URL, timeout=60).read())
    return ImageFont.truetype(str(FONT_CACHE), size)


def mono(size: int) -> ImageFont.FreeTypeFont:
    for name in ("consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_og() -> Path:
    img = Image.new("RGB", (1200, 630), BLK)
    d = ImageDraw.Draw(img)

    # pastki acid chiziq — saytdagi urg'u rangi
    d.rectangle([0, 606, 1200, 630], fill=ACID)

    # logo (mavjud brend fayli)
    logo = Image.open(STATIC / "logo.png").convert("RGBA").resize((96, 96), Image.LANCZOS)
    img.paste(logo, (80, 74), logo)

    d.text((196, 92), "promtchi", font=anton(64), fill=CREAM)
    d.text((196 + d.textlength("promtchi", font=anton(64)) + 8, 92), "®", font=mono(22), fill=ACID)

    # asosiy satr — uch tilda ham o'qiladigan, brend darajasidagi xabar
    d.text((80, 250), "WEB · MOBILE", font=anton(92), fill=CREAM)
    d.text((80, 352), "CRM/ERP · AI", font=anton(92), fill=ACID)

    d.text((80, 500), "promtchi.uz", font=mono(30), fill=CREAM)
    d.text((80, 540), "Tashkent, Uzbekistan", font=mono(24), fill=MUTED)

    out = STATIC / "og-cover.png"
    img.save(out, "PNG", optimize=True)
    return out


def make_favicon() -> Path:
    src = Image.open(STATIC / "favicon.png").convert("RGBA")
    out = STATIC / "favicon.ico"
    src.save(out, sizes=[(16, 16), (32, 32), (48, 48)])
    return out


if __name__ == "__main__":
    for p in (make_og(), make_favicon()):
        print(p.relative_to(ROOT), p.stat().st_size, "bayt")
