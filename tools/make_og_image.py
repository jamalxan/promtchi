"""OG preview rasmi (1200x630) va favicon.ico generatori.

Nega kerak: og:image sifatida 256x256 logotip ishlatilgan edi — ijtimoiy
tarmoq va qidiruv preview'lari uchun tavsiya etilgan o'lcham 1200x630.
Bu skript brendbuk ranglari va brend shrifti (Outfit, OFL litsenziya —
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

BASE = (13, 17, 23)
WHITE = (255, 255, 255)
TEAL = (20, 200, 180)
MUTED = (155, 163, 175)

# Brend shrifti — Outfit (SIL OFL, Google Fonts), o'zgaruvchan og'irlikli fayl
OUTFIT_URL = "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf"
FONT_CACHE = ROOT / "tools" / "Outfit-wght.ttf"


def outfit(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    if not FONT_CACHE.exists():
        FONT_CACHE.write_bytes(urllib.request.urlopen(OUTFIT_URL, timeout=60).read())
    font = ImageFont.truetype(str(FONT_CACHE), size)
    font.set_variation_by_axes([weight])
    return font


def make_og() -> Path:
    img = Image.new("RGB", (1200, 630), BASE)
    d = ImageDraw.Draw(img)

    # brendbuk gorizontal logotipi (shaffof fon, oq + firuza kursor)
    logo = Image.open(STATIC / "brand" / "promtchi-horizontal-1024.png").convert("RGBA")
    logo = logo.resize((360, round(360 * logo.height / logo.width)), Image.LANCZOS)
    img.paste(logo, (72, 72), logo)

    # asosiy satr — uch tilda ham o'qiladigan, faqat birinchi harf katta (07 Tipografiya)
    d.text((80, 248), "Web, mobil va CRM/ERP", font=outfit(76, 500), fill=WHITE)
    d.text((80, 340), "AI bilan bitta tizimda", font=outfit(76, 500), fill=TEAL)

    d.text((80, 498), "promtchi.uz", font=outfit(32, 500), fill=WHITE)
    d.text((80, 542), "Toshkent, O‘zbekiston", font=outfit(26), fill=MUTED)

    # pastki kursor bloki — logotipdagi `_`
    d.rectangle([1048, 540, 1128, 566], fill=TEAL)

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
