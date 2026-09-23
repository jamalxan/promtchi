"""Ma'lumotlar bazasi zaxirasi va tiklash (TZ 20-bo'lim: "Backup va restore mexanizmi").

Nega shu ko'rinishda:

* **SQLite** — zaxira `VACUUM INTO` orqali olinadi. Oddiy fayl nusxasi (`cp`)
  yozuv tranzaksiyasi o'rtasida buzuq snapshot berishi mumkin; `VACUUM INTO`
  esa izchil, siqilgan (bo'sh sahifalarsiz) nusxa yaratadi va ishlab turgan
  ilovani to'xtatmaydi. Natija gzip bilan siqiladi.
* **Postgres** — bu yerda zaxira OLINMAYDI. U server darajasida (`pg_dump`,
  managed snapshot) bajariladi; soxta "zaxira tayyor" degan yozuv chiqarmaymiz.
* **Tiklash faqat CLI** — HTTP endpoint ATAYLAB yo'q: bitta noto'g'ri so'rov
  butun bazani almashtirib yuborardi. Tiklashdan oldin joriy baza
  `*.before-restore` nomi bilan saqlanadi.

Ishlatish:

    python -m app.backup create           # hozir zaxira olish
    python -m app.backup list             # mavjud zaxiralar
    python -m app.backup restore <fayl>   # tiklash (tasdiqlash so'raladi)

Avtomatik rejim: `BACKUP_ENABLED=true` bo'lsa ilova ishga tushganda fon
vazifasi `BACKUP_INTERVAL_HOURS` da bir marta zaxira oladi va eng oxirgi
`BACKUP_KEEP` donasini saqlab, qolganini o'chiradi.

Serverdan tashqariga nusxalash: har bir muvaffaqiyatli zaxiradan so'ng fayl
avtomatik ravishda mavjud, ulangan Telegram guruhga (`_send_offsite`,
`app/telegram.py::TelegramBot.send_document`) hujjat sifatida yuboriladi —
alohida bulut/S3 hisobi kerak emas. Telegram HTTPS orqali ishlaydi, bu
zaxira fayli (mijoz arizalari — Lead — bilan) uchun maxfiy kanal talabini
qondiradi. Bot sozlanmagan bo'lsa — jim o'tkazib yuboriladi, zaxiraning o'zi
baribir diskda saqlanadi.
"""
from __future__ import annotations

import asyncio
import gzip
import logging
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

log = logging.getLogger("promtchi.backup")

_PREFIX = "promtchi-"
_SUFFIX = ".sqlite.gz"


def sqlite_path() -> Path | None:
    """DATABASE_URL'dan SQLite fayl yo'li (Postgres bo'lsa None)."""
    if not settings.is_sqlite:
        return None
    url = settings.DATABASE_URL
    _, _, tail = url.partition(":///")
    return Path(tail) if tail else None


def backup_dir() -> Path:
    d = Path(settings.BACKUP_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_backups() -> list[Path]:
    """Eng yangisi birinchi bo'lgan zaxira fayllari."""
    return sorted(
        (p for p in backup_dir().glob(f"{_PREFIX}*{_SUFFIX}") if p.is_file()),
        key=lambda p: p.name,
        reverse=True,
    )


def _create_sync(db: Path, out: Path) -> Path:
    tmp = out.with_suffix(out.suffix + ".tmp")
    snapshot = out.parent / (out.name.replace(_SUFFIX, "") + ".snapshot")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        # VACUUM INTO — izchil nusxa; maqsad fayl mavjud bo'lmasligi kerak
        snapshot.unlink(missing_ok=True)
        conn.execute("VACUUM INTO ?", (str(snapshot),))
    finally:
        conn.close()
    try:
        with open(snapshot, "rb") as src, gzip.open(tmp, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        tmp.replace(out)  # atomik: yarim yozilgan fayl zaxira deb hisoblanmaydi
    finally:
        snapshot.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)
    return out


def prune(keep: int | None = None) -> list[Path]:
    """Eng yangi `keep` donadan tashqarisini o'chiradi, o'chirilganlarni qaytaradi."""
    keep = settings.BACKUP_KEEP if keep is None else keep
    removed = []
    for old in list_backups()[max(keep, 1):]:
        old.unlink(missing_ok=True)
        removed.append(old)
    return removed


async def create_backup() -> Path | None:
    """Zaxira oladi. Postgres yoki baza fayli topilmasa — None."""
    db = sqlite_path()
    if db is None:
        log.info("backup: Postgres — zaxira server darajasida olinadi (pg_dump), bu yerda emas")
        return None
    if not db.exists():
        log.warning("backup: baza fayli topilmadi: %s", db)
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = backup_dir() / f"{_PREFIX}{stamp}{_SUFFIX}"
    path = await asyncio.to_thread(_create_sync, db, out)
    removed = prune()
    log.info(
        "backup: %s (%.1f MB) tayyor%s",
        path.name, path.stat().st_size / 1048576,
        f", {len(removed)} ta eski o'chirildi" if removed else "",
    )
    await _send_offsite(path)
    return path


async def _send_offsite(path: Path) -> None:
    """Zaxirani serverdan tashqariga (Telegram guruhga) nusxalaydi — TZ 20-bo'lim:
    "zaxirani serverdan tashqariga nusxalash". Mavjud, allaqachon ulangan
    Telegram guruh ishlatiladi (alohida bulut/S3 hisobi talab qilinmaydi).
    Xato yuborishni to'xtatmasin — zaxiraning o'zi baribir diskda saqlanadi."""
    try:
        from .telegram import bot
        if not bot.token or not bot.group_chat_id:
            log.info("backup: Telegram sozlanmagan — tashqariga nusxalash o'tkazib yuborildi")
            return
        size_mb = path.stat().st_size / 1048576
        caption = f"🗄 Kunlik zaxira ({size_mb:.1f} MB)"
        data = await asyncio.to_thread(path.read_bytes)
        ok = await bot.send_document(bot.group_chat_id, data, path.name, caption)
        if not ok:
            log.warning("backup: Telegram'ga yuborilmadi: %s", bot.last_error)
    except Exception:
        log.exception("backup: Telegram'ga yuborishda xato")


async def scheduler_loop() -> None:
    """Fon vazifasi: har `BACKUP_INTERVAL_HOURS` da bir marta zaxira.

    2026-09-23 bug: navbatdagi zaxira vaqti ILGARI process ishga tushgan
    vaqtidan (5 daqiqa kutib) hisoblanardi — deploy har push'da xizmatni
    qayta ishga tushirgani uchun bir kunda o'nlab marta zaxira olinib,
    har biri Telegram guruhga yuborilardi ("1 kunda 1 marta" o'rniga).
    Endi navbatdagi vaqt diskdagi ENG OXIRGI zaxira faylining nomidagi
    vaqt tamg'asidan hisoblanadi — restartlar soniga bog'liq emas: xizmat
    necha marta qayta ishga tushmasin, haqiqiy interval o'tmaguncha yangi
    zaxira olinmaydi va Telegram'ga yuborilmaydi.
    """
    interval = max(1, settings.BACKUP_INTERVAL_HOURS) * 3600
    while True:
        existing = list_backups()
        elapsed = interval
        if existing:
            try:
                stamp = existing[0].name[len(_PREFIX):-len(_SUFFIX)]
                last_dt = datetime.strptime(stamp, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
            except Exception:
                pass  # fayl nomi kutilgan formatda emas — darhol zaxira olamiz
        wait = interval - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
            continue
        try:
            await create_backup()
        except asyncio.CancelledError:
            raise
        except Exception:  # zaxira xatosi ilovani to'xtatmasligi kerak
            log.exception("backup: zaxira olishda xato")
        await asyncio.sleep(interval)


def restore_sync(archive: Path) -> Path:
    """Zaxiradan tiklaydi. Joriy bazani `.before-restore` bilan saqlaydi."""
    db = sqlite_path()
    if db is None:
        raise SystemExit("Tiklash faqat SQLite uchun — Postgres'da pg_restore ishlating.")
    if not archive.exists():
        raise SystemExit(f"Fayl topilmadi: {archive}")
    tmp = db.with_suffix(db.suffix + ".restoring")
    with gzip.open(archive, "rb") as src, open(tmp, "wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    # tiklangan fayl haqiqatan SQLite ekanini tekshiramiz
    conn = sqlite3.connect(tmp)
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise SystemExit("Zaxira buzuq — tiklash to'xtatildi.")
    finally:
        conn.close()
    if db.exists():
        keep = db.with_suffix(db.suffix + ".before-restore")
        keep.unlink(missing_ok=True)
        db.replace(keep)
    tmp.replace(db)
    # Eski WAL/SHM tiklangan bazaga tegishli emas — qolsa, SQLite ularni
    # shu bazaning jurnali deb o'qib, tiklangan holatni buzishi mumkin.
    for side in (db.with_name(db.name + "-wal"), db.with_name(db.name + "-shm")):
        side.unlink(missing_ok=True)
    return db


def _cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    if cmd == "create":
        path = asyncio.run(create_backup())
        print(path or "Zaxira olinmadi (Postgres yoki baza fayli yo'q).")
    elif cmd == "list":
        items = list_backups()
        if not items:
            print(f"Zaxira yo'q ({backup_dir()})")
        for p in items:
            print(f"{p.name}  {p.stat().st_size / 1048576:.1f} MB")
    elif cmd == "restore" and len(args) > 1:
        archive = Path(args[1])
        print("DIQQAT: joriy baza almashtiriladi (nusxasi *.before-restore sifatida saqlanadi).")
        if input(f"'{archive.name}' dan tiklansinmi? [yes/NO]: ").strip().lower() != "yes":
            raise SystemExit("Bekor qilindi.")
        print(f"Tiklandi: {restore_sync(archive)}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    _cli()
