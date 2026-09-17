# SEO_IMPLEMENTATION_REPORT.md — promtchi.uz

> **2-BOSQICH (2026-09-17)** quyida. Avvalgi bosqich (2026-09-15/16) o'zgarishsiz saqlangan — "1-BOSQICH ARXIVI" sarlavhasidan boshlab o'qing.

---

# 2-BOSQICH — LIVE AUDIT ASOSIDAGI TUZATISHLAR (2026-09-17)

**Kirish holati:** production'dagi 77 URL bo'yicha jonli crawl. Texnik poydevor (robots, sitemap, canonical,
hreflang, JSON-LD, redirectlar, 404, Googlebot kirishi, gzip, H1) PASS edi — ular QAYTA YOZILMADI,
faqat aniqlangan P0/P1/P2 kamchiliklar tuzatildi va har bir o'zgarishdan keyin regression crawl qilindi.

**Deploy holati:** o'zgarishlar repo'da; production'da HALI YO'Q. Quyidagi "VERIFIED" natijalar
lokal serverda (`uvicorn`, haqiqiy DB, 76 URL) olingan — production tasdiqlash deploydan keyin
qayta crawl talab qiladi. Soxta production-verification berilmagan.

---

## FIXED — repo'da real tuzatilgan

| # | Muammo (audit) | Nima qilindi | Fayl |
|---|----------------|--------------|------|
| 1 | 29 ta title 30 belgidan qisqa, kalit so'zsiz | 30 ta URL uchun search-intent'ga mos `<title>`; H1 tegilmadi (`<title>` alohida `seo_title` o'zgaruvchisida) | `app/pages.py`, `static/index*.html` |
| 2 | 5 juft takroriy title (portfolio/blog) | Case title endi case'ning O'Z `cat` maydoni bilan farqlanadi (DB'dagi tasdiqlangan kategoriya, uydirma emas) | `app/pages.py` |
| 3 | og:image = 256x256 logotip | 1200x630 brend banneri + `og:image:width/height` (faqat standart banner uchun) + `twitter:card=summary_large_image` | `static/og-cover.png`, `tools/make_og_image.py`, `templates/base.html`, `static/index*.html` |
| 4 | `/favicon.ico` 404 | Ildizdan `image/x-icon` bilan 200 qaytaradigan route + `<link rel="icon" href="/favicon.ico">` | `app/pages.py`, `static/favicon.ico` |
| 5 | sitemap'da lastmod faqat 8 URL'da | Real `updated_at` bo'lgan sahifalarga lastmod (xizmat/portfolio/ular indeksi/blog) — statik kontentga SUN'IY sana yozilmadi | `app/pages.py`, `app/db.py` |
| 6 | JSON-LD'da har sahifada yarim ma'lumotli takroriy "promtchi" tugunlari | `@id` grafi: bitta `Organization` tuguni, `WebSite.publisher` / `Service.provider` / `Article.author+publisher` unga havola qiladi; `logo` → `ImageObject` | `app/seo.py`, `static/index*.html` |
| 7 | GSC tasdiqlash uchun kod tayyor emas | `SEARCH_CONSOLE_VERIFICATION` env → ichki sahifalarda `base.html`, statik bosh sahifalarda `_inject_verification()` splice. Token yo'q bo'lsa meta umuman chiqmaydi | `app/config.py`, `app/main.py`, `templates/base.html` |
| 8 | `/docs`, `/redoc`, `/openapi.json` production'da ochiq va indekslanishi mumkin | robots.txt'ga `Disallow` + `X-Robots-Tag: noindex, nofollow` (`/api/*`, `/admin*`, docs yo'llari) | `app/pages.py`, `app/security.py` |
| 9 | `/ru/blog/` description 69 belgi (juda qisqa) | Uch tilda ham qiymat va'dasi bilan kengaytirildi | `app/pages.py` |

## VERIFIED — lokal serverda o'lchandi (76 URL crawl)

| Tekshiruv | Natija |
|---|---|
| HTTP status | 76/76 = 200 |
| Canonical o'zini ko'rsatadi | 76/76 |
| hreflang + x-default | 76/76 |
| Sahifada bitta H1 | 76/76 |
| JSON-LD parse xatolari | 0 |
| Noyob title | 76/76 (takroriy 0) |
| Noyob description | 76/76 (takroriy 0) |
| Title > 65 belgi | 0 |
| Title < 30 belgi | 2 (faqat EN huquqiy sahifalar — qidiruv maqsadi emas) |
| og:image | 76/76 → 1200x630 banner |
| `/favicon.ico` | 200, `image/x-icon`, 3031 bayt |
| sitemap.xml | XML valid, 76 URL, 46 tasida real `lastmod` |
| `X-Robots-Tag` | `/docs`, `/openapi.json`, `/api/*`, `/admin` → noindex; ommaviy sahifalarda YO'Q |
| pytest | 41/41 PASS |

**Ilova javob vaqti (lokal, tarmoqsiz):** `/uz/` 4 ms · `/uz/faq/` 5 ms · xizmat sahifasi 11 ms · `/sitemap.xml` 14 ms.

## PENDING MANUAL ACTION — kod bilan bajarib bo'lmaydi

| # | Ish | Nima kerak |
|---|-----|-----------|
| 1 | **SEARCH_CONSOLE_VERIFICATION_PENDING** | GSC → property qo'shish → HTML-tag usuli → tokenni `SEARCH_CONSOLE_VERIFICATION` env'ga yozib deploy qilish. Token TAXMIN QILINMADI |
| 2 | Sitemap submit | GSC → Sitemaps → `sitemap.xml` (faqat foydalanuvchi bajaradi) |
| 3 | Request indexing | GSC → URL Inspection → bosh sahifa + muhim sahifalar |
| 4 | **MANUAL_ACTION_REQUIRED** — Bing Webmaster | robots/sitemap mos; property tasdiqlash va sitemap yuborish qo'lda |
| 5 | **MANUAL_ACTION_REQUIRED** — Yandex Webmaster | UZ bozori uchun muhim; tasdiqlash + sitemap qo'lda |
| 6 | **GA4 Measurement ID** | `GA_MEASUREMENT_ID` env o'rnatilmagan → saytda analitika umuman yo'q. Kod tayyor (`_inject_ga` + `base.html`), faqat ID kerak. Soxta ID qo'yilmadi |
| 7 | **BUSINESS_DATA_REQUIRED** — LocalBusiness/ProfessionalService | Ko'cha manzili va ish vaqti ma'lum emas. Ular berilmaguncha `ProfessionalService` qo'shilmadi: manzilsiz LocalBusiness Google talablariga javob bermaydi va Search Console'da xato beradi. Hozir `Organization` + `PostalAddress(addressLocality=Tashkent, UZ)` + telefon + `sameAs` — hammasi tasdiqlangan ma'lumot |
| 8 | **ENV=production o'rnatilmagan (production'da)** | Dalil: `/docs`, `/redoc`, `/openapi.json` jonli saytda 200 qaytaradi (`ENABLE_DOCS` default `ENV != production`) va `Strict-Transport-Security` header yo'q (`security.py` uni faqat `is_production`da qo'shadi). Bu, shuningdek, `auth.py` admin cookie'sini `secure=False` qiladi. Server env'ida `ENV=production` qo'yilishi kerak |
| 9 | HSTS | **DO_NOT_FAKE** — kod tayyor (`HSTS_SECONDS=31536000`), faqat `ENV=production` yetishmayapti. nginx konfiguratsiyasi repo'dan boshqarilmaydi |

## CANNOT VERIFY — platforma/deploy cheklovlari

- **Google indeks holati.** `site:promtchi.uz` bo'yicha ishlatilgan qidiruv vositasi (Google emas) saytdan hech narsa qaytarmadi — bu "indekslanmagan" degani EMAS. Aniq javob faqat Search Console'da.
- **Production headerlari** (HSTS, X-Robots-Tag) va yangi title'lar — deploydan keyin qayta crawl kerak.
- **Core Web Vitals (LCP/CLS/INP)** — real foydalanuvchi maydon ma'lumoti; GA4/CrUX ulanmagani uchun o'lchanmadi.
- **Google Rich Results / Schema validator** — tashqi xizmat; JSON-LD lokal sxema bo'yicha valid (0 parse xatosi), Google'ning o'z tekshiruvi deploydan keyin.

## REMAINING — qolgan texnik ish (ustuvorlik bo'yicha)

1. **TTFB ~1.2 s — sabab tarmoq, ilova emas.** O'lchov: TCP connect 468 ms, TLS 785 ms, TTFB 1439 ms; lokal ilova esa 4–14 ms. Vaqt RTT'da ketmoqda. Yechim: sayt oldiga CDN (masalan Cloudflare) yoki foydalanuvchilarga yaqinroq hosting. **Blind optimizatsiya qilinmadi** — ilova kodida bottleneck yo'q.
2. **HTTP/2 yoqilmagan** — jonli sayt HTTP/1.1 (`nginx/1.24.0`). Yuqori RTT'da h2 sezilarli yordam beradi (`listen 443 ssl http2;`).
3. **Statik fayllar keshi** — `max-age=86400, must-revalidate`. `?v=<hash>` bilan yuklanadigan `site.css`/`site.js` uchun `max-age=31536000, immutable` mumkin (`_STATIC_ASSET_CACHE`).
4. **4 ta xizmat sahifasining description'i 160+ belgi** (`mobil-ilova-yaratish`, `crm`, `erp`, `avtomatlashtirish`). Matn DB'da (admin panel) — kod seed'ini o'zgartirish production'ga ta'sir qilmaydi, shuning uchun admin panel orqali qisqartirish kerak.
5. **Kontent chuqurligi** — `CONTENT_DEPTH_AUDIT.md`ga qarang: portfolio keyslari (~180 so'z) va yechim sahifalari (~270 so'z) eng kam. Tavsiya etilgan bo'limlar faqat REAL ma'lumot bilan to'ldirilishi kerak (skrinshot, integratsiyalar, jarayon) — uydirma natija/mijoz/ko'rsatkich qo'shilmaydi.
6. **Blog post title'lari** qisqa (`CRM nima? — promtchi®`). `Post.seo_title` maydoni mavjud — admin panel orqali har bir post uchun alohida SEO title yozish mumkin.
7. **FAQ sahifasi uchun `lastmod`** — `FaqItem.updated_at` store orqali chiqarilmagan; kerak bo'lsa qo'shiladi.

## Yangilangan/yaratilgan fayllar

```
app/pages.py           — title'lar, portfolio case title, sitemap lastmod, /favicon.ico, robots Disallow, og default, gsc_token
app/seo.py             — ORG_ID/@id grafi, OG_DEFAULT, logo -> ImageObject
app/security.py        — X-Robots-Tag (api/admin/docs)
app/config.py          — SEARCH_CONSOLE_VERIFICATION
app/main.py            — _inject_verification() (statik bosh sahifalar uchun)
app/db.py              — Service/PortfolioCase as_dict() ichida updated_at (sitemap lastmod uchun)
templates/base.html    — GSC meta, og:image o'lchamlari, twitter summary_large_image, favicon.ico
static/index*.html     — title/og:title/twitter:title, og-cover, favicon.ico, JSON-LD @id grafi
static/og-cover.png    — YANGI 1200x630 banner
static/favicon.ico     — YANGI (16/32/48)
tools/make_og_image.py — YANGI generator (bannerni qayta ishlab chiqarish uchun)
SEO_TITLE_AUDIT.md     — YANGI: 84 URL bo'yicha title inventarizatsiyasi
CONTENT_DEPTH_AUDIT.md — YANGI: so'z soni + tavsiya etilgan bo'limlar
```

## Keyingi qadam (tartib bilan)

1. Deploy → `ENV=production` va (token olingach) `SEARCH_CONSOLE_VERIFICATION` env'larini o'rnatish.
2. Deploydan keyin production crawl: 77/77 = 200, title'lar yangilangani, `/favicon.ico` 200, HSTS header, `/docs` yopiqligi.
3. GSC: verify → sitemap submit → Request indexing.
4. GA4 ID berilsa — analitikani yoqish (privacy siyosati allaqachon `/{lang}/maxfiylik-siyosati/` da; cookie-consent talabi qayta ko'rib chiqiladi).

---

## 2-BOSQICH, IKKINCHI TO'PLAM — TZ'dagi qolgan SEO bandlari (2026-09-17)

Birinchi to'plamdan keyin TZ.md bo'lim-bo'lim kod bilan solishtirildi. Quyidagilar
kod bilan bajarilishi mumkin bo'lgan barcha qolgan SEO bandlari:

### FIXED

| # | TZ bandi | Muammo | Yechim |
|---|----------|--------|--------|
| 1 | §2, §22 | **Tasdiqlanmagan statistika hali ko'rinardi**: hero'dagi `32+ Loyiha`, `98% Qoniqish`, `24+ Mijoz` (HTML'da `0`, JS 1.2s da haqiqiy raqamgacha sanaydi). Katta STATS bandi allaqachon `hidden` edi — hero'dagisi e'tibordan chetda qolgan | `.hero-data` ham `hidden` (uch tilda), izoh bilan. Markup **o'chirilmadi** — raqamlar tasdiqlansa `hidden` ni olib tashlash yetarli (TZ §22: "arxitektura tayyor qoldiriladi"). Qo'shimcha: `[hidden]{display:none!important}` — `.hero-data{display:flex}` `hidden` ni bosib ketmasin |
| 2 | §9, §13 | **Bo'sh blog indekslari**: `/ru/blog/` va `/en/blog/` da 0 ta maqola, lekin ular indekslanadigan va sitemap'da edi (thin/bo'sh sahifa) | Maqolasiz blog indeksi `noindex,nofollow`; sitemap'dan chiqariladi; hreflang faqat maqolasi BOR tillarga ishora qiladi. Maqola qo'shilishi bilan avtomatik qaytadi |
| 3 | §9 | FAQ sahifasida `lastmod` yo'q edi | `FaqItem.updated_at` store orqali ochildi, sitemap'ga qo'shildi |
| 4 | §19 | "Blog → service click" hodisasi yo'q edi | `analytics.js`: maqoladan xizmat sahifasiga o'tish `blog_to_service_click`, boshqa joydan `service_click` |
| 5 | §17 | Hash'li statik fayllar ham qisqa kesh bilan berilardi | `?v=<hash>` bo'lgan so'rovga `max-age=31536000, immutable`; versiyasiz URL eski qoidada qoladi |

### TUZATILGAN NOANIQLIK (avvalgi hisobotda xato bo'lgan band)

Birinchi to'plam hisobotida "4 ta xizmat description'i 160+ belgi" deb yozilgan edi.
Bu **noto'g'ri o'lchov** bo'lgan: uzunlik HTML manbasidan olingan, u yerda apostrof
`&#39;` (5 belgi) sifatida yoziladi. Haqiqiy matnda o'lchanganda barcha description'lar
**156–159 belgi** — ya'ni chegaradan oshmaydi va tuzatish talab qilmaydi.

### VERIFIED (lokal, 74 URL)

| Tekshiruv | Natija |
|---|---|
| Crawl | 74/74 = 200 (sitemap 76 → 74: ikkita bo'sh blog indeksi chiqarildi) |
| Canonical / hreflang / bitta H1 / JSON-LD | regressiyasiz (0 xato) |
| `/ru/blog/`, `/en/blog/` | `noindex,nofollow`, sitemap'da yo'q, hreflang faqat `uz-UZ` + `x-default` |
| `/uz/blog/` | indekslanadi, sitemap'da bor |
| FAQ sahifasi | `<lastmod>` bor |
| `site.css?v=…` | `max-age=31536000, immutable`; `site.css` — eski qoida |
| Hero statistikasi | `display:none`, balandlik 0; hero tuzilishi buzilmadi (`.hero-foot` 171px) |
| pytest | **71/71** (7 ta yangi test) |
| ruff | 42 (baseline 39 + 3 ta yangi `E741` — bu `for l in LANGS` konvensiyasi, faylda 25+ marta ishlatilgan) |

### TZ'da qolgan, LEKIN kod bilan bajarib bo'lmaydigan

| TZ bandi | Nima kerak |
|---|---|
| §19 Analytics | **GA4 Measurement ID** — ID berilmaguncha barcha hodisa kodi ishlamaydi (soxta ID qo'yilmaydi) |
| §19 Search Console | Tasdiqlash tokeni (env tayyor) |
| §13, §15 | **Blog RU/EN kontenti** — arxitektura 3 tilni qo'llab-quvvatlaydi, maqolalar faqat uz'da (8 ta). AI-filler yozilmadi (TZ §26 taqiqlaydi) |
| §22, §23 | LocalBusiness — **manzil + ish vaqti**; real statistika — **raqamlar tasdig'i**; jamoa profillari; ko'proq case study; pricing sahifalari; knowledge hub/glossary; real sharhlar (tizim tayyor, hozir 0 ta tasdiqlangan sharh) |
| §20 | Backup/restore — server cron yoki hosting snapshot (kodda endpoint yo'q, ataylab) |
| §9, §17 | `ENV=production` (hozir `/docs` ochiq, HSTS yo'q), HTTP/2, CDN/TTFB |

---

# 1-BOSQICH ARXIVI (2026-09-15 — 2026-09-16)

**Loyiha:** promtchi.uz — FastAPI (Python) backend, Jinja2 SSR ichki sahifalar + statik HTML bosh sahifa (uz/ru/en), SQLite/Postgres (SQLAlchemy async), vanilla JS admin panel. Node/npm build tizimi YO'Q — bu Python loyihasi.

**Sana:** 2026-09-15 — 2026-09-16 (bir necha ketma-ket sessiya, shu jumladan yakuniy to'liq audit).

---

## 1. Nima qilindi (qisqacha)

Loyiha to'liq audit qilindi va TZ.md'dagi (v1 → v3.0) barcha texnik jihatdan bajarilishi mumkin bo'lgan talablar amalga oshirildi:

- URL arxitekturasi, hreflang, canonical, sitemap, robots — tekshirildi, tasdiqlandi.
- Xizmat/Portfolio/Blog/FAQ uchun to'liq DB-based CMS (admin panel CRUD) qurildi — ilgari qisman qattiq-yozilgan Python fayllar edi.
- Homepage (UZ/RU/EN) to'liq trilingual CMS'ga o'tkazildi — admin panel o'zgarishlari endi barcha 3 tilda avtomatik ko'rinadi.
- FAQ tizimi kategoriya/xizmatga bog'lash va "bosh sahifada ko'rsatish" bilan kuchaytirildi.
- Portfolio case'lariga yangi maydonlar (industry/goal/features/integrations/process) qo'shildi.
- Schema.org (Organization) bosh sahifada endi jonli kontakt ma'lumoti bilan sinxron.
- Twitter/X card to'liq qo'shildi.
- 6 ta xizmat sahifasining SEO title'i qisqartirildi.
- Tasdiqlanmagan statistika yashirildi (fake data siyosati).
- Production'da real avtomatlashtirilgan crawl audit o'tkazildi (77/77 URL — natijalar `SEO_AUDIT.md`da).
- **Production'da topilgan, o'zim kiritgan regressiya (bo'sh FAQ) darhol tuzatildi va tasdiqlandi.**

## 2. Qaysi fayllar o'zgardi (shu audit + oldingi sessiyalar davomida)

**Backend (Python):**
`app/main.py`, `app/db.py`, `app/schemas.py`, `app/pages.py`, `app/faq_store.py` (yangi), `app/services_store.py`, `app/content/faq.py`, `app/content/services.py`, `app/content/common.py`

**Templates:** `templates/base.html`, `templates/service_detail.html`, `templates/portfolio_detail.html`, `templates/faq.html`

**Frontend (statik):** `static/index.html`, `static/index.ru.html`, `static/index.en.html`, `static/admin.html`

**Hujjatlar:** `TZ.md` (progress log), `SEO_AUDIT.md` (yangi), `SEO_IMPLEMENTATION_REPORT.md` (yangi)

## 3. Yaratilgan yangi route'lar

- `GET /{lang}/jamoa/` — 301 → `/{lang}/biz-haqimizda/` (real jamoa profillari tayyor bo'lmagani uchun thin-content page emas, redirect).
- `GET /api/admin/content` — admin panel uchun xom (barcha 3 til) kontent hujjati.
- `GET/POST/PUT/DELETE /api/admin/faq[/{id}]` — FAQ to'liq CRUD.

## 4. SEO improvements

- `/api/content?lang=uz|ru|en` — homepage kontenti endi til bo'yicha to'g'ri ajratiladi.
- 6 ta xizmat title'i SERP uchun optimal uzunlikka qisqartirildi.
- Portfolio case'larga industry/goal/features/integrations/process — boy, tuzilgan kontent uchun infratuzilma.
- Xizmat sahifalariga bog'langan umumiy FAQ savollari qo'shilib, sahifa kontenti boyidi (masalan `/xizmatlar/crm/` endi 4 ta FAQ ko'rsatadi).

## 5. AI/GEO improvements

- FAQ endi kategoriya va xizmatga bog'langan — AI/LLM uchun "company → service → FAQ" bog'lanishi aniqroq.
- Har bir xizmat sahifasida "nima/kim uchun/qanday/natija" formatidagi kontent avvaldan mavjud edi — o'zgarishsiz saqlandi (allaqachon TZ'ga mos).

## 6. Technical SEO

- Organization schema.org endi bosh sahifada jonli, admin-boshqariladigan kontakt ma'lumoti bilan mos (ilgari eskirgan/tasdiqlanmagan telefon-email hardcode qilingan edi — TZ 10-bo'lim buzilishi edi).
- Twitter/X card to'liq (`title`/`description`/`image`).
- Sitemap 77/77 to'g'ri indexable URL, barchasi 200.
- Hreflang 69 sahifada to'liq 4-tomonlama, 8 blog postida ataylab qisqartirilgan (tarjima yo'q).

## 7. Performance

- Gzip compression, ETag, `Cache-Control` — barchasi ishlaydi (production headerlar orqali tasdiqlandi).
- Fontlar WOFF2 formatida, `preconnect` bilan.
- Bu sessiyada yangi performance-buzuvchi o'zgarish kiritilmadi (mavjud arxitektura allaqachon optimallashtirilgan edi).

## 8. Accessibility

- `<img>` teglarning barchasida `alt` matni bor (0 ta yetishmovchilik topildi).
- Bitta H1 har sahifada, semantik heading ierarxiyasi.
- (Oldingi sessiyada) global `:focus-visible`, "Skip to content" havolasi qo'shilgan edi.

## 9. Security

- CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, COOP — barchasi production'da tasdiqlandi.
- Admin route'lar `robots.txt`da bloklangan.
- Repo'da hech qanday secret/parol commit qilinmadi (`.env` gitignore'da).

## 10. Analytics

- GA4 (agar `GA_MEASUREMENT_ID` sozlangan bo'lsa) va conversion eventlar (`phone_click`, `email_click`, `telegram_click`, `cta_click`, `portfolio_click`, `generate_lead`, `page_not_found`) — oldingi sessiyada qo'shilgan, o'zgarishsiz.

## 11. Test natijalari

- `pytest tests/` — **23/23 o'tdi** (har bir o'zgarishdan keyin qayta ishga tushirildi).
- Barcha JS fayllar (`static/index*.html`, `static/admin.html`) `node --check` bilan sintaksis tekshiruvidan o'tdi.
- Migratsiyalar (eski→yangi schema, FAQ backfill, Service title fix) sintetik test skriptlari bilan tasdiqlandi: to'g'ri ishlashi VA idempotentligi (ikkinchi marta ishga tushirilganda admin qo'lda kiritgan o'zgarishni buzmasligi) tekshirildi.
- Production'da real crawl audit — natijalar `SEO_AUDIT.md`da.
- **Production regressiya topildi va TUZATILDI shu sessiya davomida**: oldingi deploy bosh sahifadagi FAQ bo'limini bo'sh qoldirgan edi — aniqlandi (Chrome orqali live tekshiruv), tuzatildi, push qilindi, production'da qayta tekshirilib tasdiqlandi.

## 12. Qolgan masalalar (texnik jihatdan bajarib bo'lmaydi, biznes ma'lumotiga bog'liq)

Foydalanuvchi bilan avvalgi sessiyalarda kelishilgan:
- **Statistika** (32+/24+/98%/3+ yil) — real raqamlar tasdiqlanmagan, shu sessiyada **yashirildi** (`hidden`, kod saqlangan).
- **LocalBusiness schema** — aniq ofis manzili/ish vaqti tasdiqlanmagani uchun QO'SHILMAGAN.
- **Jamoa a'zolari** — real ism/foto hozircha public qilinmaydi ("Bizning ekspertiza" bloki bilan almashtirilgan).
- **FAQ javoblari** — mavjud 24 ta savol-javob allaqachon biznes tomonidan tasdiqlangan real kontent (narx/muddat paketlar bilan mos); yangi savollar kelsa admin panel orqali qo'shiladi.

## 13. Qo'lda bajarilishi kerak bo'lgan ishlar

1. **Google Search Console**ga sitemap.xml yuborish (agar hali yuborilmagan bo'lsa).
2. **Google Rich Results Test** va **Schema.org Validator** orqali structured data'ni rasmiy tasdiqlash (bu muhitda tashqi vosita ishlatib bo'lmadi).
3. Real **Lighthouse/PageSpeed Insights** o'lchovi — Core Web Vitals (LCP/INP/CLS) raqamlarini olish uchun.
4. Contact formani **real** ma'lumot bilan qo'lda test qilish (ataylab avtomatik qilinmadi — real Telegram xabarnoma va CRM yozuvi yaratmaslik uchun).
5. Statistika/LocalBusiness/jamoa — real ma'lumot tayyor bo'lganda admin panel orqali qo'shish (infratuzilma tayyor).

## 14. Production deployment checklist

- [x] Barcha o'zgarishlar `git push origin master` orqali yuborildi.
- [x] Production avtomatik deploy qiladi (tekshirildi — push'dan ~1 daqiqa ichida `?lang=` parametri va boshqa o'zgarishlar live saytda ko'rindi).
- [x] Production'da hotfix darhol tasdiqlandi (FAQ bo'sh muammosi).
- [ ] **Tavsiya**: keyingi safar katta schema o'zgarishi (yangi ustun + eski ma'lumotni ko'chirish) qilinganda, deploy'dan keyin **darhol** production'ni tekshirish odatiy protsedura sifatida joriy etilsin (bu safar aynan shu tekshiruv orqali xato topildi).
