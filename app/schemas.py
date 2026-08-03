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


class CaseIn(BaseModel):
    """Loyiha + uning case-study tafsilotlari (bitta yozuvda).

    video — yuklangan fayl yo'li yoki YouTube/Vimeo havolasi; loyiha
    modalida rasm o'rniga/rasmdan keyin ko'rsatiladi.
    """

    title: str = Field(min_length=1, max_length=140)
    cat: str = Field(min_length=1, max_length=60)
    client: str = Field(default="", max_length=140)
    duration: str = Field(default="", max_length=60)
    short: str = Field(default="", max_length=600)
    problem: str = Field(default="", max_length=2000)
    solution: str = Field(default="", max_length=2000)
    result: str = Field(default="", max_length=2000)
    tech: str = Field(default="", max_length=400)
    image: str = Field(default="", max_length=1000)
    video: str = Field(default="", max_length=1000)
    link: str = Field(default="", max_length=500)  # jonli loyiha havolasi

    _v_image = field_validator("image")(_validate_media_url)


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


class ContentDoc(BaseModel):
    """To'liq kontent hujjati — PUT /api/admin/content shu shaklni kutadi.

    contacts/socials ixtiyoriy: eski mijozlar (yoki eski saqlangan hujjat)
    ularsiz yuborsa ham qabul qilinadi.
    """

    packages: list[PackageIn] = Field(max_length=12)
    team: list[TeamIn] = Field(max_length=30)
    testimonials: list[TestimonialIn] = Field(max_length=50)
    cases: list[CaseIn] = Field(max_length=100)
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
    tasdiqlagach hisob darhol shu parol bilan faollashadi)."""

    new_email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=8, max_length=200)

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
    """Blog/yangilik posti. video — yuklangan fayl yoki YouTube havolasi."""

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=20000)
    image: str = Field(default="", max_length=1000)
    video: str = Field(default="", max_length=1000)
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
DEFAULT_CONTENT: dict = {
    "packages": [
        {
            "name": "Boshlang'ich",
            "price": "300$ dan",
            "popular": False,
            "features": [
                "Landing sahifa",
                "Oddiy Telegram bot",
                "Avto javob beruvchi",
                "Umumiy kichik loyihalar",
                "14 kunlik texnik yordam",
            ],
        },
        {
            "name": "Standart",
            "price": "800$ dan",
            "popular": True,
            "features": [
                "Ko'p sahifali korporativ veb-sayt yoki web-app",
                "Professional Telegram bot",
                "Admin panel",
                "Mijozlar bazasi",
                "Buyurtma va arizalarni boshqarish",
                "Foydalanuvchilarni ro'yxatdan o'tkazish",
                "Telegram, email yoki SMS bildirishnomalari",
                "CRM integratsiyasi",
                "To'lov tizimi integratsiyasi",
                "Asosiy statistika va hisobotlar",
                "Domen, hosting va serverga joylashtirish",
                "30 kunlik texnik yordam",
            ],
        },
        {
            "name": "Maxsus",
            "price": "Kelishilgan holda",
            "popular": False,
            "features": [
                "Individual CRM yoki ERP tizimi",
                "Kompaniya jarayonlariga mos admin panel",
                "Sotuv bo'limini boshqarish",
                "Mijozlar va xodimlar boshqaruvi",
                "Moliya, tushum, xarajat va ish haqi modullari",
                "KPI va bonuslarni avtomatik hisoblash",
                "Ombor va mahsulotlar nazorati",
                "Real vaqt rejimidagi dashboard",
                "API ishlab chiqish",
                "Ma'lumotlarni himoyalash va zaxiralash",
                "Serverga joylashtirish va texnik sozlash",
                "90 kunlik texnik yordam",
            ],
        },
    ],
    "contacts": [
        {"label": "Telegram", "value": "@promtchi", "url": "https://t.me/promtchi", "icon": "telegram"},
        {"label": "Email", "value": "hello@promtchi.uz", "url": "mailto:hello@promtchi.uz", "icon": "email"},
        {"label": "Telefon", "value": "+998 90 000 00 00", "url": "tel:+998900000000", "icon": "phone"},
    ],
    "socials": [
        {"name": "Telegram", "url": "https://t.me/promtchi", "icon": "telegram"},
        {"name": "Instagram", "url": "https://instagram.com/promtchi", "icon": "instagram"},
    ],
    "team": [
        {"name": "G'iyosiddin Tursunxo'jayev", "role": "Founder", "photo": "", "role_type": "founder"},
        {"name": "Jamolxon Yo'ldashaliyev", "role": "Co-Founder", "photo": "", "role_type": "co_founder"},
        {"name": "Abbos Setdarov", "role": "IT Specialist", "photo": "", "role_type": "member"},
        {"name": "Samandar Orifjonov", "role": "IT Specialist", "photo": "", "role_type": "member"},
    ],
    "testimonials": [
        {
            "text": "Jamoa g'oyani tez tushundi va MVP'ni kelishilgan muddatda yetkazdi. Aloqa doim ochiq edi.",
            "name": "Rustam A.",
            "role": "Startap asoschisi",
            "photo": "",
        },
        {
            "text": "Avtomatlashtirish orqali qo'lda ishlarimiz sezilarli kamaydi. Natijadan juda mamnunmiz.",
            "name": "Malika S.",
            "role": "Marketing rahbari",
            "photo": "",
        },
        {
            "text": "Professional yondashuv va toza kod. Loyihadan keyin ham qo'llab-quvvatlashdi.",
            "name": "Sardor K.",
            "role": "Biznes egasi",
            "photo": "",
        },
    ],
    "cases": [
        {
            "title": "Chindan Group",
            "cat": "Avtomatlashtirish",
            "client": "Chindan Group",
            "duration": "20 kun",
            "short": "To'liq avtomatlashtirilgan sotuv oqimi — leaddan to'lovgacha.",
            "problem": "Leadlar qo'lda yig'ilar, sotuv jarayoni tarqoq va kuzatib bo'lmas edi.",
            "solution": "Lead → CRM → sotuv sayti → to'lov + hisobot zanjirini yagona tizimga birlashtirdik.",
            "result": "Qo'lda ishlar ~70% kamaydi, leaddan to'lovgacha vaqt sezilarli qisqardi.",
            "tech": "FastAPI, PostgreSQL, Telegram Bot API, Redis",
            "image": "",
        },
        {
            "title": "Notiq AI",
            "cat": "AI yechimlar",
            "client": "Notiq",
            "duration": "25 kun",
            "short": "Ovozni matnga aylantiruvchi mobil ilova — o'zbek tili uchun optimallashtirilgan.",
            "problem": "Mavjud yechimlar o'zbek tilida past aniqlik berardi.",
            "solution": "O'zbek tiliga moslashtirilgan STT modeli va toza mobil UI ishlab chiqdik.",
            "result": "Yuqori aniqlikdagi transkripsiya va tez, qulay foydalanuvchi tajribasi.",
            "tech": "Flutter, Python, ASR pipeline",
            "image": "",
        },
        {
            "title": "BotSmith Platform",
            "cat": "Web & ilova",
            "client": "BotSmith",
            "duration": "30 kun",
            "short": "Prompt orqali Telegram botlarini avtomatik yaratib, deploy qiluvchi web-platforma.",
            "problem": "Bot yaratish uchun har safar dasturchi yollash qimmat va sekin edi.",
            "solution": "Foydalanuvchi prompt va token kiritadi — tizim botni o'zi generatsiya qilib, serverga joylaydi.",
            "result": "Bot yaratish soatlab emas — daqiqalarda. Texnik bilimsiz foydalanuvchilar mustaqil ishlaydi.",
            "tech": "Django DRF, aiogram 3, Docker, PostgreSQL, Redis",
            "image": "",
        },
    ],
}
