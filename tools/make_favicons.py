"""Favicon to'plami: faqat `>_` belgisi (brendbuk), so'z qismisiz.

Belgi geometriyasi brend SVG'dan (04-svg/promtchi-icon-*.svg). Kichik
o'lchamlarda (<=32px) chiziqlar qalinlashtiriladi va bo'sh joy kamaytiriladi —
aks holda 16px'da belgi xira bo'lib qoladi.

Ishlatish:  python tools/make_favicons.py
Natija:     static/{icon.svg,favicon.ico,favicon.png,apple-touch-icon.png,icon-192.png,icon-512.png}
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parent.parent / "static"

BASE, WHITE, TEAL = (13, 17, 23), (255, 255, 255), (20, 200, 180)
CHEVRON = [(-14.35, -103), (14.35, -103), (67.35, -51.5), (14.35, 0), (-14.35, 0), (38.65, -51.5)]
CURSOR = (63, -20, 119, 0)  # x0, y0, x1, y1
X0, Y0, W, H = -14.35, -103, 133.35, 103  # belgi chegaralari


def render(size: int, pad: float, bold: float = 0.0, radius: float = 0.0) -> Image.Image:
    """pad — chetdan bo'sh joy ulushi, bold — chiziq qalinlashuvi (belgi enining ulushi)."""
    ss = 8
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if radius:
        d.rounded_rectangle([0, 0, n - 1, n - 1], radius=int(n * radius), fill=BASE)
    else:
        d.rectangle([0, 0, n, n], fill=BASE)
    scale = n * (1 - 2 * pad) / W  # belgi kenglik bo'yicha sig'adi
    ox = (n - W * scale) / 2 - X0 * scale
    oy = (n - H * scale) / 2 - Y0 * scale
    p = lambda x, y: (ox + x * scale, oy + y * scale)
    w = max(0, round(bold * W * scale))
    d.polygon([p(*c) for c in CHEVRON], fill=WHITE, outline=WHITE, width=w)
    x0, y0, x1, y1 = CURSOR
    (a, b), (c, e) = p(x0, y0), p(x1, y1)
    d.rectangle([a - w / 2, b - w / 2, c + w / 2, e + w / 2], fill=TEAL)
    return img.resize((size, size), Image.LANCZOS)


def write_ico(path: Path, images: list[Image.Image]) -> None:
    """Pillow ICO'ni bitta rasmdan qayta o'lchaydi — har o'lcham alohida PNG sifatida yig'iladi."""
    import io
    import struct

    blobs = []
    for im in images:
        b = io.BytesIO()
        im.save(b, "PNG", optimize=True)
        blobs.append((im.width, b.getvalue()))
    head = struct.pack("<HHH", 0, 1, len(blobs))
    off = 6 + 16 * len(blobs)
    entries = b""
    for w, data in blobs:
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), off)
        off += len(data)
    path.write_bytes(head + entries + b"".join(d for _, d in blobs))


def svg() -> str:
    pad = 0.18
    s = 100 * (1 - 2 * pad) / W
    ox, oy = (100 - W * s) / 2 - X0 * s, (100 - H * s) / 2 - Y0 * s
    pts = " ".join(f"{ox + x * s:.2f},{oy + y * s:.2f}" for x, y in CHEVRON)
    x0, y0, x1, y1 = CURSOR
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<rect width="100" height="100" rx="18" fill="#0D1117"/>'
        f'<polygon points="{pts}" fill="#fff"/>'
        f'<rect x="{ox + x0 * s:.2f}" y="{oy + y0 * s:.2f}" width="{(x1 - x0) * s:.2f}" '
        f'height="{(y1 - y0) * s:.2f}" fill="#14C8B4"/></svg>\n'
    )


if __name__ == "__main__":
    (STATIC / "icon.svg").write_text(svg(), encoding="utf-8")
    ico = [render(16, 0.06, 0.07), render(32, 0.08, 0.04), render(48, 0.12)]
    write_ico(STATIC / "favicon.ico", ico)
    render(96, 0.12, 0.0, 0.18).save(STATIC / "favicon.png", optimize=True)
    render(180, 0.15).convert("RGB").save(STATIC / "apple-touch-icon.png", optimize=True)
    render(192, 0.15, 0.0, 0.18).save(STATIC / "icon-192.png", optimize=True)
    render(512, 0.15, 0.0, 0.18).save(STATIC / "icon-512.png", optimize=True)
