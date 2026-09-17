"""Pydantic sxemalar — frontend DATA tuzilmasiga birebir mos validatsiya."""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from . import crm_constants as crm

# Frontend rasm/avatar maydonlarini style="...url('${esc(v)}')" ichiga qo'yadi.
# esc() faqat HTML uchun xavfsiz — HTML atributi brauzerda dekod qilingach,
# ' yoki ) saqlangan bo'lsa CSS qiymatidan chiqib ketish (CSS injection)
# mumkin bo'ladi. Shu sabab bunday maydonlarni saqlashdan oldin qat'iy
# formatga (oddiy http(s) havola yoki /static/uploads/ fayli) cheklaymiz.
_SAFE_MEDIA_URL = re.compile(r"^(https?://[^\s'\"()<>]+|/static/uploads/[A-Za-z0-9._-]+)$")


def _validate_media_url(v: str) -> str:
    v = (v or "").strip()
    if v and not _SAFE_MEDIA_URL.match(v):
        raise ValueError(
            "Rasm manzili noto'g'ri — faqat http(s):// havola yoki yuklangan fayl bo'lishi kerak"
        )
    return v


_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(v: str) -> str:
    v = (v or "").strip().lower()
    if not _SLUG_RE.match(v):
        raise ValueError("Slug faqat lotin harf/raqam va '-' belgisidan iborat bo'lishi kerak")
    return v


class PackageIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    price: str = Field(min_length=1, max_length=60)
    popular: bool = False
    features: list[str] = Field(min_length=1, max_length=30)


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    photo: str = Field(default="", max_length=1000)
    # founder/co_founder — Jamoa bo'limida alohida yuqori qatorda chiqadi
    role_type: Literal["founder", "co_founder", "member"] = "member"

    _v_photo = field_validator("photo")(_validate_media_url)


class TestimonialIn(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)
    photo: str = Field(default="", max_length=1000)

    _v_photo = field_validator("photo")(_validate_media_url)


def _validate_key(v: str) -> str:
    v = (v or "").strip().lower()
    if not _KEY_RE.match(v):
        raise ValueError("Key faqat lotin harf/raqam va '-' belgisidan iborat bo'lishi kerak")
    return v


def _validate_faq_pairs(items: list) -> list[list[str]]:
    """FAQ — [[savol, javob], ...] juftliklar shaklida (app/content/faq.py,
    seo.faq_schema() va templates/*.html'dagi `for q, a in faq` bilan bir xil
    shakl — bu yerda {"q":..,"a":..} obyekt EMAS, aynan 2 elementli ro'yxat)."""
    out = []
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("FAQ juftligi [savol, javob] shaklida bo'lishi kerak")
        q, a = (str(item[0]).strip(), str(item[1]).strip())
        if not q or not a:
            raise ValueError("Savol va javob bo'sh bo'lmasligi kerak")
        if len(q) > 200 or len(a) > 2000:
            raise ValueError("Savol yoki javob juda uzun")
        out.append([q, a])
    return out


class ServiceLangIn(BaseModel):
    """Bitta xizmat sahifasining bitta tildagi to'liq kontenti
    (templates/service_detail.html shu maydonlarga tayanadi)."""

    slug: str = Field(min_length=1, max_length=140)
    nav: str = Field(min_length=1, max_length=60)
    h1: str = Field(min_length=1, max_length=140)
    title: str = Field(min_length=1, max_length=200)
    meta: str = Field(min_length=1, max_length=300)
    value: str = Field(min_length=1, max_length=600)
    for_whom: str = Field(default="", max_length=600)
    problem: str = Field(default="", max_length=1200)
    solution: str = Field(default="", max_length=1200)
    includes: list[str] = Field(default_factory=list, max_length=20)
    features: list[str] = Field(default_factory=list, max_length=20)
    integrations: list[str] = Field(default_factory=list, max_length=20)
    process: list[str] = Field(default_factory=list, max_length=20)
    tech: list[str] = Field(default_factory=list, max_length=20)
    price_note: str = Field(default="", max_length=500)
    faq: list[list[str]] = Field(default_factory=list, max_length=10)

    _v_slug = field_validator("slug")(_validate_slug)
    _v_faq = field_validator("faq")(_validate_faq_pairs)


class ServiceIn(BaseModel):
    """PUT/POST /api/admin/services[/{id}] — bitta xizmat, 3 tilda."""

    key: str = Field(min_length=1, max_length=60)
    order: int = 0
    published: bool = True
    uz: ServiceLangIn
    ru: ServiceLangIn
    en: ServiceLangIn

    _v_key = field_validator("key")(_validate_key)


class CaseLangIn(BaseModel):
    """Bitta portfolio case'ning bitta tildagi to'liq kontenti
    (templates/portfolio_detail.html shu maydonlarga tayanadi).

    `industry`/`goal`/`features`/`integrations`/`process` — TZ 12-bo'lim
    (yangi TZ v3.0) talab qilgan maydonlar; barchasi ixtiyoriy (bo'sh bo'lsa
    shablon o'sha bo'limni ko'rsatmaydi) — mavjud 3 ta case'da hali
    to'ldirilmagan, uydirilmaydi, admin panel orqali qo'shiladi."""

    slug: str = Field(min_length=1, max_length=140)
    title: str = Field(min_length=1, max_length=140)
    cat: str = Field(min_length=1, max_length=60)
    client: str = Field(default="", max_length=140)
    industry: str = Field(default="", max_length=120)
    duration: str = Field(default="", max_length=60)
    short: str = Field(default="", max_length=600)
    problem: str = Field(default="", max_length=2000)
    goal: str = Field(default="", max_length=1000)
    solution: str = Field(default="", max_length=2000)
    features: list[str] = Field(default_factory=list, max_length=20)
    integrations: list[str] = Field(default_factory=list, max_length=20)
    process: list[str] = Field(default_factory=list, max_length=20)
    result: str = Field(default="", max_length=2000)
    tech: str = Field(default="", max_length=400)
    meta: str = Field(default="", max_length=300)

    _v_slug = field_validator("slug")(_validate_slug)


class PortfolioCaseIn(BaseModel):
    """PUT/POST /api/admin/portfolio[/{id}] — bitta case, 3 tilda.

    `image` — skrinshot (TZ 13-bo'lim), tilga bog'liq emas — bitta umumiy URL."""

    key: str = Field(min_length=1, max_length=60)
    order: int = 0
    published: bool = True
    image: str = Field(default="", max_length=1000)
    uz: CaseLangIn
    ru: CaseLangIn
    en: CaseLangIn

    _v_key = field_validator("key")(_validate_key)
    _v_image = field_validator("image")(_validate_media_url)


class FaqLangIn(BaseModel):
    """/{lang}/faq/ sahifasidagi bitta savol-javobning bitta tildagi matni."""

    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(min_length=1, max_length=3000)


class FaqAdminIn(BaseModel):
    """PUT/POST /api/admin/faq[/{id}] — bitta savol-javob, 3 tilda (TZ 14/19-bo'lim).

    `service_key` — bo'sh bo'lsa umumiy savol; aks holda mavjud xizmat
    key'iga ishora qiladi va o'sha xizmat sahifasida ham ko'rsatiladi.
    `show_on_home` — bosh sahifadagi qisqa "Savol-javob" bo'limida ham chiqsinmi.
    """

    key: str = Field(min_length=1, max_length=60)
    order: int = 0
    published: bool = True
    category: str = Field(default="", max_length=80)
    service_key: str = Field(default="", max_length=60)
    show_on_home: bool = False
    uz: FaqLangIn
    ru: FaqLangIn
    en: FaqLangIn

    _v_key = field_validator("key")(_validate_key)


class ContactIn(BaseModel):
    """Aloqa havolasi — "Bog'lanish" bo'limida chiqadi."""

    label: str = Field(min_length=1, max_length=60)      # Telegram, Email, Telefon…
    value: str = Field(default="", max_length=160)       # @promtchi, hello@…
    url: str = Field(min_length=1, max_length=500)       # https://t.me/…, mailto:…
    icon: str = Field(default="link", max_length=24)     # ikonka kaliti


class SocialIn(BaseModel):
    """Footer'dagi ijtimoiy tarmoq havolasi."""

    name: str = Field(min_length=1, max_length=40)       # ko'rinadigan nom
    url: str = Field(min_length=1, max_length=500)
    icon: str = Field(default="link", max_length=24)     # telegram/instagram/…


class StatIn(BaseModel):
    """Bosh sahifadagi statistika katagi (masalan "32+" / "Loyiha").

    TZ 2 va 22-bo'lim: bu raqamlar BIZNES tomonidan tasdiqlanmaguncha
    ko'rsatilmaydi — shuning uchun sukut bo'yicha ro'yxat BO'SH va bo'lim
    umuman render qilinmaydi. Admin panelga qiymat kiritilganda blok
    avtomatik paydo bo'ladi (soxta raqam kodda saqlanmaydi).
    """

    value: str = Field(min_length=1, max_length=12)      # "32+", "98%", "3+"
    label: str = Field(min_length=1, max_length=48)      # "Loyiha", "Qoniqish"


class StatsByLang(BaseModel):
    uz: list[StatIn] = Field(default_factory=list, max_length=6)
    ru: list[StatIn] = Field(default_factory=list, max_length=6)
    en: list[StatIn] = Field(default_factory=list, max_length=6)


class PackagesByLang(BaseModel):
    """Paketlar — 3 tilda, RU/EN bosh sahifasi endi shu yerdan avtomatik
    o'qiydi (ilgari alohida qattiq yozilgan edi — TZ 1-bo'lim: admin panel
    orqali 3 til kontentini boshqarish)."""

    uz: list[PackageIn] = Field(default_factory=list, max_length=12)
    ru: list[PackageIn] = Field(default_factory=list, max_length=12)
    en: list[PackageIn] = Field(default_factory=list, max_length=12)


class TeamByLang(BaseModel):
    """Jamoa/ekspertiza kartalari — rol/lavozim 3 tilda tarjima qilinadi,
    ism/rasm har tilda takrorlanadi (soddalik uchun)."""

    uz: list[TeamIn] = Field(default_factory=list, max_length=30)
    ru: list[TeamIn] = Field(default_factory=list, max_length=30)
    en: list[TeamIn] = Field(default_factory=list, max_length=30)


class TestimonialsByLang(BaseModel):
    """Mijozlar fikri (kontentdagi zaxira, real fikrlar Review orqali) — 3 tilda."""

    uz: list[TestimonialIn] = Field(default_factory=list, max_length=50)
    ru: list[TestimonialIn] = Field(default_factory=list, max_length=50)
    en: list[TestimonialIn] = Field(default_factory=list, max_length=50)


class ContentDoc(BaseModel):
    """To'liq kontent hujjati — PUT /api/admin/content shu shaklni kutadi.

    `packages`/`team`/`testimonials` endi til bo'yicha saqlanadi (uz/ru/en) —
    TZ 1-bo'lim: "kontentni admin panel orqali... 3 tilda" talabi RU/EN bosh
    sahifalariga ham tegishli, ilgira faqat UZ saqlanardi.
    `cases`/`faq` ATAYLAB yo'q — homepage "Loyihalar" gridi Portfolio
    bazasidan (services_store), bosh sahifadagi qisqa FAQ esa FaqItem
    bazasidan (faq_store, `show_on_home=True` bo'lganlar) to'g'ridan-to'g'ri
    o'qiydi — ikkinchi parallel manba yo'q (TZ audit'ida topilgan edi).
    contacts/socials tilga bog'liq EMAS (bitta umumiy ro'yxat, TZ 4.6/4.9-bo'lim
    — telefon/telegram/email raqami tilga qarab o'zgarmaydi).
    """

    packages: PackagesByLang
    team: TeamByLang
    testimonials: TestimonialsByLang
    # Sukut bo'yicha bo'sh — tasdiqlanmagan statistika ko'rsatilmaydi (TZ 2/22)
    stats: StatsByLang = Field(default_factory=StatsByLang)
    contacts: list[ContactIn] = Field(default_factory=list, max_length=12)
    socials: list[SocialIn] = Field(default_factory=list, max_length=12)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(v: str) -> str:
    v = (v or "").strip()
    if not _EMAIL_RE.match(v):
        raise ValueError("Email formati noto'g'ri")
    return v


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)

    _v_email = field_validator("email")(_validate_email)


class ForgotPasswordIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)

    _v_email = field_validator("email")(_validate_email)


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=10, max_length=100)
    new_password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=8, max_length=200)

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, v: str, info) -> str:
        if info.data.get("new_password") is not None and v != info.data["new_password"]:
            raise ValueError("Parollar mos kelmadi")
        return v


class AddEmailRequestIn(BaseModel):
    """Yangi admin taklif qilish — parol shu yerda o'rnatiladi (super admin
    tasdiqlagach hisob darhol shu parol bilan faollashadi). role — CRM
    huquqlar matritsasi uchun ("manager" = sotuv bo'limi, standart)."""

    new_email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=8, max_length=200)
    role: Literal["admin", "manager"] = "manager"

    _v_email = field_validator("new_email")(_validate_email)

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, v: str, info) -> str:
        if info.data.get("password") is not None and v != info.data["password"]:
            raise ValueError("Parollar mos kelmadi")
        return v


class RemoveEmailRequestIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)

    _v_email = field_validator("email")(_validate_email)


class SetPrimaryRequestIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)

    _v_email = field_validator("email")(_validate_email)


class ConfirmTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=100)


_PHONE_RE = re.compile(r"^\+?\d{7,15}$")
_TG_USERNAME_RE = re.compile(r"^@[A-Za-z0-9_]{5,32}$")


class LeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=120)
    project_type: str = Field(default="other", max_length=60)
    message: str = Field(default="", max_length=4000)
    # Honeypot — ko'zga ko'rinmas maydon, faqat botlar to'ldiradi (odam ko'rmaydi
    # va CSS bilan yashirilgan). To'ldirilgan bo'lsa main.py buni jimgina
    # e'tiborsiz qoldiradi (botga "aniqlandik" signalini bermaslik uchun).
    website: str = Field(default="", max_length=200)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:  # faqat probeldan iborat ism o'tmasin
            raise ValueError("Ism bo'sh bo'lishi mumkin emas")
        return v

    @field_validator("phone")
    @classmethod
    def _phone_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Telefon raqami yoki Telegram username kiritilishi shart")
        cleaned = re.sub(r"[\s\-()]", "", v)
        if _TG_USERNAME_RE.match(cleaned) or _PHONE_RE.match(cleaned):
            return v
        raise ValueError(
            "Telefon raqamini (+998901234567) yoki Telegram @username'ni to'g'ri kiriting"
        )

    @field_validator("project_type")
    @classmethod
    def _project_type_slug(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in crm.PROJECT_TYPE_SLUGS else "other"


class LeadStatusIn(BaseModel):
    """Ariza holatini o'zgartirish: new (yangi) / replied (javob berilgan)."""

    status: Literal["new", "replied"]


class PostIn(BaseModel):
    """Blog/yangilik posti (TZ 6-bo'lim). video — yuklangan fayl yoki YouTube havolasi.
    `lang` — post qaysi tilga tegishli (tarjima emas, mustaqil maqola);
    /{lang}/blog/ faqat o'sha tilga tegishli postlarni ko'rsatadi."""

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=20000)
    excerpt: str = Field(default="", max_length=300)
    image: str = Field(default="", max_length=1000)
    video: str = Field(default="", max_length=1000)
    category: str = Field(default="", max_length=80)
    tags: str = Field(default="", max_length=300)
    author: str = Field(default="", max_length=120)
    lang: Literal["uz", "ru", "en"] = "uz"
    seo_title: str = Field(default="", max_length=200)
    seo_description: str = Field(default="", max_length=300)
    noindex: bool = False
    published: bool = True

    _v_image = field_validator("image")(_validate_media_url)


class ReviewIn(BaseModel):
    """Mijoz yozadigan fikr. `code` — admin bergan bir martalik kod."""

    code: str = Field(min_length=3, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)
    text: str = Field(min_length=10, max_length=1200)
    rating: int = Field(default=5, ge=1, le=5)

    @field_validator("name", "text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Bo'sh bo'lishi mumkin emas")
        return v


class ReviewCodeIn(BaseModel):
    """Yangi kod yaratish — mijoz nomi ixtiyoriy izoh."""

    client: str = Field(default="", max_length=160)


class TelegramSettingsIn(BaseModel):
    """Telegram sozlamalari.

    bot_token=None — o'zgartirilmaydi (maskalangan qiymat qaytarilgani uchun
    admin uni qayta yubormasligi mumkin); bo'sh satr — o'chirish.
    """

    bot_token: str | None = Field(default=None, max_length=200)
    chat_id: str = Field(default="", max_length=64)


class TelegramAdminIn(BaseModel):
    """Sezgir xabarnomalarni (yangi admin paroli va h.k.) olishi kerak bo'lgan
    shaxsiy Telegram chat — guruh/kanaldan farqli, faqat shu odamlarga boradi."""

    chat_id: int
    label: str = Field(default="", max_length=60)


# ══════════ CRM Kanban ══════════

class LeadCreateIn(BaseModel):
    """Admin panel ichidan qo'lda mijoz qo'shish (8.-bo'limdagi sayt formasidan farqli)."""

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(default="", max_length=120)
    project_type: str = Field(default="other", max_length=60)
    message: str = Field(default="", max_length=4000)
    source: str = Field(default="manual", max_length=20)
    assigned_to: str | None = Field(default=None, max_length=200)
    budget: float | None = None

    @field_validator("name")
    @classmethod
    def _name_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Ism bo'sh bo'lishi mumkin emas")
        return v

    @field_validator("project_type")
    @classmethod
    def _pt_ok(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in crm.PROJECT_TYPE_SLUGS else "other"

    @field_validator("source")
    @classmethod
    def _source_ok(cls, v: str) -> str:
        v = (v or "").strip().lower()
        return v if v in crm.SOURCES else "manual"


class LeadUpdateIn(BaseModel):
    """Qisman yangilash — faqat yuborilgan maydonlar o'zgaradi."""

    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=120)
    project_type: str | None = Field(default=None, max_length=60)
    message: str | None = Field(default=None, max_length=4000)
    budget: float | None = None
    next_action_at: str | None = None  # ISO 8601; bo'sh satr = tozalash

    @field_validator("project_type")
    @classmethod
    def _pt_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        return v if v in crm.PROJECT_TYPE_SLUGS else "other"


class LeadStageChangeIn(BaseModel):
    stage: str

    @field_validator("stage")
    @classmethod
    def _stage_ok(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in crm.STAGE_SLUGS:
            raise ValueError("Noto'g'ri bosqich")
        return v


class LeadAssignIn(BaseModel):
    assigned_to: str | None = Field(default=None, max_length=200)


class SetAdminRoleIn(BaseModel):
    """CRM huquqlar matritsasi: admin <-> manager. Super admin roli
    is_primary bilan sinxron boshqariladi, bu yerdan o'zgartirilmaydi."""

    role: Literal["admin", "manager"]


class LeadNoteCreateIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def _text_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Izoh bo'sh bo'lishi mumkin emas")
        return v


class CrmTelegramSettingsIn(BaseModel):
    """CRM Kanban Telegram sozlamalari.

    bot_token=None — o'zgartirilmaydi (maskalangan qiymat qaytarilgani uchun);
    bo'sh satr — o'chirish. Bitta bot ikkalasi (umumiy bildirishnoma va CRM)
    uchun ham ishlatiladi (2-bo'lim: 409 Conflict xavfi tufayli).
    """

    bot_token: str | None = Field(default=None, max_length=200)
    leads_chat_id: str = Field(default="", max_length=64)
    topic_thread_id: int | None = None
    notify_chat_id: str = Field(default="", max_length=64)
    is_enabled: bool = False
    send_on_create: bool = True
    edit_on_update: bool = True


# ── Boshlang'ich kontent (saytdagi bilan bir xil) ─────────────────────────────
# `packages`/`team`/`testimonials`/`faq` — 3 tilda (uz/ru/en). RU/EN matnlar
# ilgira static/index.ru.html/.en.html'da qattiq yozilgan professional
# tarjimalar edi (TZ 22-bo'lim: avtomatik tarjima emas) — shu yerga ko'chirildi,
# endi admin panel orqali barcha 3 til bitta joydan boshqariladi.
# `cases` ATAYLAB yo'q — homepage "Loyihalar" gridi Portfolio bazasidan o'qiydi.
DEFAULT_CONTENT: dict = {
    "packages": {
        "uz": [
            {
                "name": "Boshlang'ich", "price": "300$ dan", "popular": False,
                "features": [
                    "Landing sahifa", "Oddiy Telegram bot", "Avto javob beruvchi",
                    "Umumiy kichik loyihalar", "14 kunlik texnik yordam",
                ],
            },
            {
                "name": "Standart", "price": "800$ dan", "popular": True,
                "features": [
                    "Ko'p sahifali korporativ veb-sayt yoki web-app", "Professional Telegram bot",
                    "Admin panel", "Mijozlar bazasi", "Buyurtma va arizalarni boshqarish",
                    "Foydalanuvchilarni ro'yxatdan o'tkazish", "Telegram, email yoki SMS bildirishnomalari",
                    "CRM integratsiyasi", "To'lov tizimi integratsiyasi", "Asosiy statistika va hisobotlar",
                    "Domen, hosting va serverga joylashtirish", "30 kunlik texnik yordam",
                ],
            },
            {
                "name": "Maxsus", "price": "Kelishilgan holda", "popular": False,
                "features": [
                    "Individual CRM yoki ERP tizimi", "Kompaniya jarayonlariga mos admin panel",
                    "Sotuv bo'limini boshqarish", "Mijozlar va xodimlar boshqaruvi",
                    "Moliya, tushum, xarajat va ish haqi modullari", "KPI va bonuslarni avtomatik hisoblash",
                    "Ombor va mahsulotlar nazorati", "Real vaqt rejimidagi dashboard", "API ishlab chiqish",
                    "Ma'lumotlarni himoyalash va zaxiralash", "Serverga joylashtirish va texnik sozlash",
                    "90 kunlik texnik yordam",
                ],
            },
        ],
        "ru": [
            {
                "name": "Стартовый", "price": "от $300", "popular": False,
                "features": [
                    "Лендинг", "Простой Telegram-бот", "Автоответчик",
                    "Небольшие типовые проекты", "14 дней техподдержки",
                ],
            },
            {
                "name": "Стандарт", "price": "от $800", "popular": True,
                "features": [
                    "Многостраничный корпоративный сайт или веб-приложение", "Профессиональный Telegram-бот",
                    "Админ-панель", "База клиентов", "Управление заказами и заявками",
                    "Регистрация пользователей", "Уведомления в Telegram, email или SMS",
                    "Интеграция с CRM", "Интеграция платёжной системы", "Базовая статистика и отчёты",
                    "Домен, хостинг и развёртывание на сервере", "30 дней техподдержки",
                ],
            },
            {
                "name": "Индивидуальный", "price": "По договорённости", "popular": False,
                "features": [
                    "Индивидуальная CRM или ERP-система", "Админ-панель под процессы компании",
                    "Управление отделом продаж", "Управление клиентами и сотрудниками",
                    "Модули финансов, доходов, расходов и зарплаты", "Автоматический расчёт KPI и бонусов",
                    "Контроль склада и товаров", "Дашборд в реальном времени", "Разработка API",
                    "Защита и резервное копирование данных", "Развёртывание на сервере и техническая настройка",
                    "90 дней техподдержки",
                ],
            },
        ],
        "en": [
            {
                "name": "Starter", "price": "from $300", "popular": False,
                "features": [
                    "Landing page", "Basic Telegram bot", "Auto-responder",
                    "Small standard projects", "14-day technical support",
                ],
            },
            {
                "name": "Standard", "price": "from $800", "popular": True,
                "features": [
                    "Multi-page corporate website or web app", "Professional Telegram bot",
                    "Admin panel", "Client database", "Order and request management",
                    "User registration", "Telegram, email or SMS notifications",
                    "CRM integration", "Payment system integration", "Basic analytics and reports",
                    "Domain, hosting and server deployment", "30-day technical support",
                ],
            },
            {
                "name": "Custom", "price": "By agreement", "popular": False,
                "features": [
                    "Custom CRM or ERP system", "Admin panel matching company processes",
                    "Sales team management", "Client and staff management",
                    "Finance, revenue, expense and payroll modules", "Automatic KPI and bonus calculation",
                    "Inventory and stock control", "Real-time dashboard", "API development",
                    "Data protection and backups", "Server deployment and technical setup",
                    "90-day technical support",
                ],
            },
        ],
    },
    "contacts": [
        {"label": "Telegram", "value": "@promtchiadmin", "url": "https://t.me/promtchiadmin", "icon": "telegram"},
        {"label": "Email", "value": "hello@promtchi.uz", "url": "mailto:hello@promtchi.uz", "icon": "email"},
        {"label": "Telefon", "value": "+998 93 160 67 06", "url": "tel:+998931606706", "icon": "phone"},
    ],
    "socials": [
        {"name": "Telegram", "url": "https://t.me/promtchiadmin", "icon": "telegram"},
        {"name": "Instagram", "url": "https://instagram.com/promtchiuz", "icon": "instagram"},
    ],
    "team": {
        "uz": [
            {"name": "G'iyosiddin Tursunxo'jayev", "role": "Founder", "photo": "", "role_type": "founder"},
            {"name": "Jamolxon Yo'ldashaliyev", "role": "Co-Founder", "photo": "", "role_type": "co_founder"},
            {"name": "Abbos Setdarov", "role": "IT Specialist", "photo": "", "role_type": "member"},
            {"name": "Samandar Orifjonov", "role": "IT Specialist", "photo": "", "role_type": "member"},
        ],
        "ru": [
            {"name": "G'iyosiddin Tursunxo'jayev", "role": "Основатель", "photo": "", "role_type": "founder"},
            {"name": "Jamolxon Yo'ldashaliyev", "role": "Сооснователь", "photo": "", "role_type": "co_founder"},
            {"name": "Abbos Setdarov", "role": "IT-специалист", "photo": "", "role_type": "member"},
            {"name": "Samandar Orifjonov", "role": "IT-специалист", "photo": "", "role_type": "member"},
        ],
        "en": [
            {"name": "G'iyosiddin Tursunxo'jayev", "role": "Founder", "photo": "", "role_type": "founder"},
            {"name": "Jamolxon Yo'ldashaliyev", "role": "Co-Founder", "photo": "", "role_type": "co_founder"},
            {"name": "Abbos Setdarov", "role": "IT Specialist", "photo": "", "role_type": "member"},
            {"name": "Samandar Orifjonov", "role": "IT Specialist", "photo": "", "role_type": "member"},
        ],
    },
    # TZ 2/22: tasdiqlanmagan statistika ko'rsatilmaydi — sukut bo'yicha BO'SH.
    # Admin panelga qiymat kiritilsa, bosh sahifadagi blok avtomatik chiqadi.
    "stats": {"uz": [], "ru": [], "en": []},
    "testimonials": {
        "uz": [
            {
                "text": "Jamoa g'oyani tez tushundi va MVP'ni kelishilgan muddatda yetkazdi. Aloqa doim ochiq edi.",
                "name": "Rustam A.", "role": "Startap asoschisi", "photo": "",
            },
            {
                "text": "Avtomatlashtirish orqali qo'lda ishlarimiz sezilarli kamaydi. Natijadan juda mamnunmiz.",
                "name": "Malika S.", "role": "Marketing rahbari", "photo": "",
            },
            {
                "text": "Professional yondashuv va toza kod. Loyihadan keyin ham qo'llab-quvvatlashdi.",
                "name": "Sardor K.", "role": "Biznes egasi", "photo": "",
            },
        ],
        "ru": [
            {
                "text": "Команда быстро уловила идею и в срок сдала MVP. На связи были всегда.",
                "name": "Rustam A.", "role": "Основатель стартапа", "photo": "",
            },
            {
                "text": "Благодаря автоматизации объём ручной работы значительно сократился. Мы очень довольны результатом.",
                "name": "Malika S.", "role": "Руководитель отдела маркетинга", "photo": "",
            },
            {
                "text": "Профессиональный подход и чистый код. Поддерживали нас и после завершения проекта.",
                "name": "Sardor K.", "role": "Владелец бизнеса", "photo": "",
            },
        ],
        "en": [
            {
                "text": "The team grasped the idea quickly and delivered the MVP on schedule. Communication was always open.",
                "name": "Rustam A.", "role": "Startup founder", "photo": "",
            },
            {
                "text": "Automation significantly cut down our manual work. We're very happy with the result.",
                "name": "Malika S.", "role": "Head of Marketing", "photo": "",
            },
            {
                "text": "Professional approach and clean code. They kept supporting us even after the project was done.",
                "name": "Sardor K.", "role": "Business owner", "photo": "",
            },
        ],
    },
}
