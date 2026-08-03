"""Zaxiradan tiklash: Telegram guruhidagi mijoz xabarlaridan Lead larni tiklaydi.

MUHIM CHEKLOV: Telegram Bot API guruh TARIXINI o'qish imkonini bermaydi (bot
faqat ishga tushgandan keyingi yangi xabarlarni ko'radi — getUpdates buferi
ham cheksiz emas, eski xabarlarni "orqaga qaytarib" bera olmaydi). Shu sabab
bu buyruq guruhga to'g'ridan-to'g'ri ulanmaydi — o'rniga Telegram Desktop'ning
"Export chat history" (JSON) natijasini o'qiydi va app/crm_service.py'dagi
qat'iy xabar shablonidan (5.2-bo'lim) Lead larni qayta tiklaydi. Har bir
xabar tahrirlanganda export'da eng oxirgi holati saqlanadi — shu holat
qabul qilinadi.

Ishlatish:
    python -m app.restore_from_telegram export_result.json          # dry-run
    python -m app.restore_from_telegram export_result.json --apply  # bazaga yozadi

Mavjud (id bo'yicha) Lead lar YANGILANADI (o'chirilmaydi); topilmagan ID lar
YANGI Lead sifatida yaratiladi.
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from . import crm_constants as crm
from .db import Lead, LeadStageHistory, SessionLocal

_HEADER_RE = re.compile(r"MIJOZ #(\d+)")
_FIELD_RES = {
    "name": re.compile(r"Ism Familiya:\s*(.+)"),
    "phone": re.compile(r"Aloqa:\s*(.+)"),
    "project": re.compile(r"Loyiha:\s*(.+)"),
    "message": re.compile(r"Habar:\s*(.+)"),
    "stage_label": re.compile(r"Bosqich:\s*\S*\s*(.+)"),
    "assigned": re.compile(r"Mas'ul:\s*(.+)"),
}

_STAGE_LABEL_TO_SLUG = {s["label"]: s["slug"] for s in crm.STAGES}
_PROJECT_LABEL_TO_SLUG = {p["label"]: p["slug"] for p in crm.PROJECT_TYPES}


def _extract_text(msg: dict) -> str:
    """Telegram Desktop JSON eksportida `text` massiv yoki oddiy satr bo'lishi mumkin."""
    t = msg.get("text", "")
    if isinstance(t, list):
        return "".join(chunk if isinstance(chunk, str) else chunk.get("text", "") for chunk in t)
    return t or ""


def parse_export(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    messages = data.get("messages", data if isinstance(data, list) else [])
    found: dict[int, dict] = {}
    for msg in messages:
        if msg.get("type") != "message":
            continue
        text = _extract_text(msg)
        m = _HEADER_RE.search(text)
        if not m:
            continue
        lead_id = int(m.group(1))
        parsed = {"id": lead_id, "tg_message_id": msg.get("id")}
        for key, rx in _FIELD_RES.items():
            fm = rx.search(text)
            if fm:
                parsed[key] = fm.group(1).strip()
        # Xabar bir necha marta tahrirlangan bo'lsa export'da bir nechta nusxa
        # bo'ladi — messages ro'yxati vaqt tartibida keladi, shuning uchun
        # oxirgi uchragani (eng yangi holat) g'olib chiqadi.
        found[lead_id] = parsed
    return list(found.values())


async def restore(records: list[dict], apply: bool) -> None:
    created, updated = 0, 0
    async with SessionLocal() as session:
        for rec in records:
            lead = await session.get(Lead, rec["id"])
            stage_label = rec.get("stage_label", "")
            stage = _STAGE_LABEL_TO_SLUG.get(stage_label, crm.DEFAULT_STAGE)
            project_type = _PROJECT_LABEL_TO_SLUG.get(rec.get("project", ""), "other")
            assigned = rec.get("assigned", "—")
            assigned_to = None if assigned in ("—", "") else assigned

            if lead is None:
                created += 1
                print(f"  [YANGI]     #{rec['id']} {rec.get('name', '?')} -> {stage}")
                if apply:
                    lead = Lead(
                        id=rec["id"], name=rec.get("name", "Noma'lum"),
                        phone="" if rec.get("phone", "—") == "—" else rec.get("phone", ""),
                        project_type=project_type,
                        message="" if rec.get("message", "—") == "—" else rec.get("message", ""),
                        stage=stage, assigned_to=assigned_to,
                        tg_message_id=rec.get("tg_message_id"),
                    )
                    session.add(lead)
                    await session.flush()
                    session.add(LeadStageHistory(lead_id=lead.id, from_stage="", to_stage=stage, changed_by=None))
            else:
                updated += 1
                print(f"  [YANGILASH] #{rec['id']} {lead.name} -> {stage}")
                if apply:
                    lead.stage = stage
                    lead.assigned_to = assigned_to
        if apply:
            await session.commit()
    tail = "" if apply else " (DRY-RUN — bazaga yozilmadi, --apply qo'shing)"
    print(f"\nJami: {created} ta yangi, {updated} ta yangilanadi.{tail}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("export_file", help="Telegram Desktop JSON eksport fayli")
    parser.add_argument("--apply", action="store_true", help="Bazaga haqiqatan yozadi (aks holda dry-run)")
    args = parser.parse_args()

    path = Path(args.export_file)
    if not path.exists():
        print(f"Fayl topilmadi: {path}", file=sys.stderr)
        sys.exit(1)

    records = parse_export(path)
    if not records:
        print("Hech qanday mijoz xabari topilmadi — export fayli to'g'riligini tekshiring.")
        sys.exit(1)
    print(f"{len(records)} ta mijoz xabari topildi.\n")
    asyncio.run(restore(records, args.apply))


if __name__ == "__main__":
    main()
