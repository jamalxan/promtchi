"""Pydantic sxemalar — frontend DATA tuzilmasiga birebir mos validatsiya."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PackageIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    price: str = Field(min_length=1, max_length=60)
    popular: bool = False
    features: list[str] = Field(min_length=1, max_length=30)


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    photo: str = Field(default="", max_length=1000)


class TestimonialIn(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)
    photo: str = Field(default="", max_length=1000)


class CaseIn(BaseModel):
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


class ContentDoc(BaseModel):
    """To'liq kontent hujjati — PUT /api/admin/content shu shaklni kutadi."""

    packages: list[PackageIn] = Field(max_length=12)
    team: list[TeamIn] = Field(max_length=30)
    testimonials: list[TestimonialIn] = Field(max_length=50)
    cases: list[CaseIn] = Field(max_length=100)


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class LeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(default="", max_length=120)
    project_type: str = Field(default="", max_length=60)
    message: str = Field(default="", max_length=4000)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:  # faqat probeldan iborat ism o'tmasin
            raise ValueError("Ism bo'sh bo'lishi mumkin emas")
        return v


class LeadStatusIn(BaseModel):
    """Ariza holatini o'zgartirish: new (yangi) / replied (javob berilgan)."""

    status: Literal["new", "replied"]


class PostIn(BaseModel):
    """Blog/yangilik posti."""

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=20000)
    image: str = Field(default="", max_length=1000)
    published: bool = True


class TelegramSettingsIn(BaseModel):
    """Telegram sozlamalari.

    bot_token=None — o'zgartirilmaydi (maskalangan qiymat qaytarilgani uchun
    admin uni qayta yubormasligi mumkin); bo'sh satr — o'chirish.
    """

    bot_token: str | None = Field(default=None, max_length=200)
    chat_id: str = Field(default="", max_length=64)


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
    "team": [
        {"name": "G'iyosiddin Tursunxo'jayev", "role": "Founder", "photo": ""},
        {"name": "Jamolxon Yo'ldashaliyev", "role": "Co-Founder", "photo": ""},
        {"name": "Abbos Setdarov", "role": "IT Specialist", "photo": ""},
        {"name": "Samandar Orifjonov", "role": "IT Specialist", "photo": ""},
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
