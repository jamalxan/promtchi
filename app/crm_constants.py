"""CRM voronkasi va Lead maydonlari uchun yagona manba (single source of truth).

Bu modul hech narsani import qilmaydi (SQLAlchemy'siz, FastAPI'siz) — shu
sabab app/db.py, app/schemas.py, app/telegram.py, app/main.py barchasi
bemalol shu yerdan import qila oladi, tsiklik import xavfi yo'q.

Tartib MUHIM: STAGES ro'yxatidagi ketma-ketlik Kanban ustunlari, Telegram
inline tugmalari va hisobotlardagi tartibning yagona manbai — hech qachon
o'zgartirmang (yangi bosqich qo'shish kerak bo'lsa, faqat oxiriga emas,
mantiqiy o'rniga qo'shing va shu faylni yangilagan odam butun loyihani
qidiruv qilib chiqishi kerak).
"""

STAGES: list[dict] = [
    {"slug": "new", "label": "Yangi mijoz", "emoji": "🆕", "color": "#3B82F6"},
    {"slug": "in_work", "label": "Ishga olindi", "emoji": "📞", "color": "#8B5CF6"},
    {"slug": "contacted", "label": "Kontakt o'rnatildi", "emoji": "🤝", "color": "#06B6D4"},
    {"slug": "meeting_set", "label": "Suhbat belgilandi", "emoji": "📅", "color": "#F59E0B"},
    {"slug": "tz_received", "label": "TZ olindi", "emoji": "📄", "color": "#EAB308"},
    {"slug": "prepaid", "label": "Birinchi to'lov olindi", "emoji": "💰", "color": "#22C55E"},
    {"slug": "won", "label": "Muvaffaqiyatli", "emoji": "✅", "color": "#10B981"},
    {"slug": "lost", "label": "Sifatsiz mijoz", "emoji": "❌", "color": "#EF4444"},
]
STAGE_SLUGS: list[str] = [s["slug"] for s in STAGES]
STAGE_BY_SLUG: dict[str, dict] = {s["slug"]: s for s in STAGES}
STAGE_ORDER: dict[str, int] = {s["slug"]: i for i, s in enumerate(STAGES)}
FINAL_STAGES: set[str] = {"won", "lost"}
DEFAULT_STAGE = "new"

# Eski 2-holatli `status` ("new"/"replied") dan yangi 8-bosqichli `stage`ga
# bir martalik ma'lumot ko'chirish uchun (db.py'dagi data-fixup shu yerdan
# o'qiydi — mapping shu faylda saqlansin, ikki joyda takrorlanmasin).
LEGACY_STATUS_TO_STAGE: dict[str, str] = {
    "new": "new",
    "replied": "in_work",
}

PROJECT_TYPES: list[dict] = [
    {"slug": "web", "label": "Web & ilova"},
    {"slug": "automation", "label": "Avtomatlashtirish"},
    {"slug": "ai", "label": "AI yechim"},
    {"slug": "crm_erp", "label": "CRM / ERP"},
    {"slug": "other", "label": "Boshqa"},
]
PROJECT_TYPE_SLUGS: list[str] = [p["slug"] for p in PROJECT_TYPES]
PROJECT_TYPE_BY_SLUG: dict[str, dict] = {p["slug"]: p for p in PROJECT_TYPES}

CONTACT_TYPES: list[str] = ["phone", "telegram", "other"]

SOURCES: list[str] = ["website", "manual", "telegram", "instagram", "referral"]
DEFAULT_SOURCE = "website"

TG_SYNC_STATES: list[str] = ["pending", "synced", "failed"]

# AdminAccount.role — is_primary=True bo'lgan hisob HAR DOIM "superadmin"
# (db.py va auth.py buni saqlaydi); qolganlari orasida "admin"/"manager"
# farqi shu maydon bilan belgilanadi (ruxsatlar matritsasi: 6-bo'lim).
ADMIN_ROLES: list[str] = ["superadmin", "admin", "manager"]
DEFAULT_ADMIN_ROLE = "manager"
