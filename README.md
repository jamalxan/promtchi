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
- HTTPS ortida ishga tushiring (Nginx/Caddy reverse-proxy)
- Nginx/Caddy/Cloudflare ortida **`TRUST_PROXY=true`** qo'ying — aks holda
  hamma bitta IP bo'lib ko'rinadi va rate-limit butun saytni bloklaydi
- systemd servis yoki Docker bilan doimiy ishlatish tavsiya etiladi

## Yuqori yuklama (10 000+ so'rov, 1000+ bir vaqtdagi ariza)

Kod allaqachon shunga mo'ljallangan: kontent va bosh sahifa xotiradan
(oldindan gzip qilingan holda) beriladi, rate-limit DB'dan oldin ishlaydi,
Telegram xabarnomalar navbatda yuboriladi. Server tomonda esa:

```bash
# 1) PostgreSQL (SQLite yozuvni ketma-ket qiladi — 1000+ parallel yozuv uchun shart)
DATABASE_URL=postgresql+asyncpg://user:parol@localhost:5432/promtchi

# 2) CPU yadrolari soniga mos workerlar (Linux'da uvloop avtomatik yoqiladi)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --backlog 4096

# 3) Nginx oldida: gzip'ni o'chirish shart emas (backend o'zi beradi),
#    /static/ ni to'g'ridan-to'g'ri nginx'dan berish yanada tezlashtiradi
```

Eslatma: rate-limit xotirada, har worker o'z hisobini yuritadi — limitlar
worker soniga ko'paytiriladi deb hisoblang (yoki qat'iy global limit kerak
bo'lsa Redis backend qo'shiladi). `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` ham har
worker uchun alohida — Postgres `max_connections` ni shunga moslang.

## Tezkor test (curl)

```bash
# login
curl -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"password":"promtchi2026"}'

# ariza
curl -X POST localhost:8000/api/leads -H 'Content-Type: application/json' \
  -d '{"name":"Ali","phone":"+99890...","project_type":"CRM / ERP","message":"Salom"}'
```
