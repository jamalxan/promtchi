# promtchi® — Backend (FastAPI)

V3 landing sayti uchun to'liq backend: kontent boshqaruvi, arizalar (lead) qabul qilish, Telegram xabarnoma, JWT admin.

## Tuzilma

```
promtchi-backend/
├── app/
│   ├── main.py      # FastAPI ilova, barcha endpointlar
│   ├── config.py    # .env sozlamalari
│   ├── db.py        # Async SQLAlchemy: Content + Lead modellari
│   ├── schemas.py   # Pydantic validatsiya + boshlang'ich kontent
│   └── auth.py      # JWT login / himoya
├── static/
│   └── index.html   # V3 sayt — API bilan ulangan varianti
├── requirements.txt
├── .env.example
└── README.md
```

## Ishga tushirish

```bash
cd promtchi-backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # va JWT_SECRET'ni o'zgartiring!
uvicorn app.main:app --reload
```

Ochish: http://127.0.0.1:8000 — sayt · http://127.0.0.1:8000/docs — Swagger.

Birinchi ishga tushishda SQLite bazasi (`promtchi.db`) yaratiladi va saytdagi
boshlang'ich kontent bilan avtomatik to'ldiriladi.

## Qanday ishlaydi

- Sayt ochilganda kontent `GET /api/content` dan yuklanadi (server yiqiq bo'lsa,
  ichki DEFAULTS bilan ishlayveradi).
- Saytdagi **⚙ admin tugmasi** endi localStorage emas — `POST /api/auth/login`
  orqali JWT oladi va har bir tahrirni 0.5s debounce bilan
  `PUT /api/admin/content` ga yozadi. Tahrirlar **barcha foydalanuvchilarga**
  ko'rinadi (avvalgidek faqat bitta brauzerda emas).
- Aloqa formasi `POST /api/leads` ga yuboriladi: baza + (sozlansa) Telegram.

## Endpointlar

| Metod  | Yo'l                         | Himoya | Tavsif |
|--------|------------------------------|--------|--------|
| GET    | /api/health                  | —      | Server holati |
| GET    | /api/content                 | —      | Sayt kontenti (packages/team/testimonials/cases) |
| POST   | /api/auth/login              | —      | `{password}` → `{token}` |
| PUT    | /api/admin/content           | Bearer | To'liq kontentni saqlash (validatsiya bilan) |
| POST   | /api/admin/content/reset     | Bearer | Boshlang'ich kontentga qaytarish |
| POST   | /api/leads                   | — (rate-limit) | Ariza: `{name, phone, project_type, message}` |
| GET    | /api/admin/leads             | Bearer | Arizalar ro'yxati (yangi birinchi) |
| DELETE | /api/admin/leads/{id}        | Bearer | Arizani o'chirish |

## Telegram xabarnoma

Yangi ariza kelganda guruhga xabar tushishi uchun `.env` da:

```
TELEGRAM_BOT_TOKEN=123456:ABC...   # @BotFather dan
TELEGRAM_CHAT_ID=-1001234567890    # guruh/kanal ID
```

Bot guruhga qo'shilgan bo'lishi kerak. Sozlanmagan bo'lsa — jim o'tadi, ariza
baribir bazaga tushadi.

## PostgreSQL'ga o'tish

```
pip install asyncpg
# .env:
DATABASE_URL=postgresql+asyncpg://user:parol@localhost:5432/promtchi
```

Boshqa hech narsa o'zgarmaydi — jadvallar avtomatik yaratiladi.

## Production eslatmalari

- `JWT_SECRET` ni albatta almashtiring: `openssl rand -hex 32`
- `ADMIN_PASSWORD` ni kuchli parolga o'zgartiring
- `CORS_ORIGINS=https://promtchi.uz` qilib qo'ying
- HTTPS ortida ishga tushiring (Nginx/Caddy reverse-proxy), masalan:
  `uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2`
- systemd servis yoki Docker bilan doimiy ishlatish tavsiya etiladi

## Tezkor test (curl)

```bash
# login
curl -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"password":"promtchi2026"}'

# ariza
curl -X POST localhost:8000/api/leads -H 'Content-Type: application/json' \
  -d '{"name":"Ali","phone":"+99890...","project_type":"CRM / ERP","message":"Salom"}'
```
