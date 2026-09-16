"""Blog postlari uchun juda cheklangan, XAVFSIZ matn->HTML render'i.

`Post.body` (app/db.py) — faqat admin panel orqali yoziladi (foydalanuvchi
submit qilmaydi), lekin baribir bevosita `|safe` bilan chiqarilmaydi: bu
modul avval BUTUN matnni escape qiladi (markupsafe.escape), keyin FAQAT
oldindan belgilangan, whitelist qilingan naqshlar ustida ishlaydi — shu
sabab hech qanday xom HTML admin tomonidan kiritilsa ham sahifaga
o'tkazilmaydi (masalan "<script>" matn sifatida ko'rinadi, bajarilmaydi).

Qo'llab-quvvatlanadigan minimal belgilash (markdown emas, faqat kichik
o'xshash to'plam):
  `## Sarlavha`              -> <h2>
  `- band`  (ketma-ket qator) -> <ul><li>
  `**qalin**`                 -> <strong>
  `[matn](https://... yoki /...)` -> <a href="...">  (faqat http(s):// yoki
                                     "/" bilan boshlanadigan ichki havolalar
                                     qabul qilinadi — boshqa sxema, masalan
                                     "javascript:", oddiy matn sifatida qoladi)
  bo'sh qator                 -> paragraf chegarasi
  qatordagi yagona \n         -> <br>
"""
import re

from markupsafe import Markup, escape

_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s()]+|/[^\s()]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def _inline(line: str) -> str:
    out = str(escape(line))
    out = _BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    out = _LINK_RE.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', out)
    return out


def render_body(text: str) -> Markup:
    if not text:
        return Markup("")
    blocks = re.split(r"\n\s*\n", text.strip())
    parts: list[str] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1 and lines[0].startswith("## "):
            parts.append(f"<h2>{_inline(lines[0][3:])}</h2>")
        elif all(ln.startswith("- ") for ln in lines):
            items = "".join(f"<li>{_inline(ln[2:])}</li>" for ln in lines)
            parts.append(f"<ul>{items}</ul>")
        else:
            parts.append(f"<p>{'<br>'.join(_inline(ln) for ln in lines)}</p>")
    return Markup("".join(parts))
