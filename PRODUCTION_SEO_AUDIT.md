# PRODUCTION SEO AUDIT — promtchi.uz

**Sana:** 2026-09-16
**Manba:** https://promtchi.uz — jonli production, local emas
**Metodika:** `/sitemap.xml`dan 84 ta indekslanadigan URL olindi → har biri Python/`requests` orqali haqiqiy HTTP so'rov bilan crawl qilindi (status, redirect chain, headerlar, title, meta, H1, canonical, hreflang, JSON-LD, OpenGraph, internal/external linklar). Xom natijalar: `crawl_results.json` (741 KB, 84 sahifa). Bu audit **IMPLEMENTED ≠ VERIFIED** tamoyili asosida — kod committed bo'lgani sahifaning productionda to'g'ri ishlashini anglatmaydi.

---

## 0. TOP-LINE SON'LAR

| Metrika | Qiymat |
|---|---|
| TOTAL INDEXABLE URLS (sitemap) | **84** |
| TOTAL 200 URLs | **84** |
| TOTAL REDIRECTS (sitemap ichida) | **0** |
| TOTAL 404 | **0** (barcha sitemap URL'lar 200; alohida yasama 404-test sahifa to'g'ri 404 qaytardi) |
| TOTAL ORPHAN PAGES | **0** |
| TOTAL MISSING META DESCRIPTION | **0** |
| TOTAL MISSING H1 | **0** |
| TOTAL CANONICAL ISSUES | **0** |
| TOTAL HREFLANG ISSUES | **0** |
| TOTAL SCHEMA FIELD ISSUES | **0** (validatsiya darajasida); **2 ta content-sifat muammosi** (pastda) |
| TOTAL BROKEN LINKS (ichki + tashqi) | **0** |
| **TOTAL CONTENT/DATA MUAMMOLARI (P0)** | **1 (kritik, ko'p joyga ta'sir qiladi)** |
| **TOTAL KEYWORD CANNIBALIZATION juftliklari** | **7** |

**SEO STATUS: ⚠️ YAXSHI, LEKIN 1 TA KRITIK (P0) VA BIR NECHTA P1 MUAMMO BOR.** Texnik SEO fundamenti (sitemap, robots, canonical, hreflang, schema validligi, internal linking) production'da to'liq to'g'ri ishlayapti. Lekin bosh sahifada **haqiqiy mijoz kontakt ma'lumotlari noto'g'ri** — bu texnik SEO emas, lekin GEO/trust signal va konversiyaga bevosita ta'sir qiladi, shuning uchun P0 sifatida bu yerda ham qayd etiladi.

---

## 1. P0 — KRITIK: Bosh sahifada eskirgan/noto'g'ri kontakt ma'lumotlari

**Aniqlanish usuli:** production HTML'ni `app/content/common.py`dagi manba ma'lumotlar va boshqa (pages.py orqali render qilinadigan) ichki sahifalar bilan solishtirish.

### 1.1 Telegram — 3 ta tilning HAMMASIDA noto'g'ri kanalga link

Bosh sahifa (`/uz/`, `/ru/`, `/en/`)dagi Organization JSON-LD (`sameAs`, `contactPoint.url`) va bir nechta CTA'lar **`https://t.me/promtchi`** ga ishora qiladi. Bu URL production'da 200 qaytaradi, LEKIN bu **promtchi bilan aloqasi yo'q, butunlay boshqa kanal — nomi "AI Hub"**:

```
t.me/promtchi     -> og:title = "AI Hub"        (NOTO'G'RI, begona kanal)
t.me/promtchiuz   -> og:title = "Promtchi uz"   (TO'G'RI, haqiqiy kanal)
```

Saytning qolgan barcha sahifalari (`/uz/xizmatlar/crm/`, `/uz/aloqa/` va h.k. — `pages.py` orqali render qilinadi, `_live_org()` bilan) to'g'ri `t.me/promtchiuz`ni ishlatadi. Faqat bosh sahifa (uchala til) noto'g'ri.

**Ta'siri:** Bosh sahifa — eng ko'p tashrif buyuriladigan va Organization schema'ning asosiy manbai bo'lgan sahifa. Google Knowledge Panel, AI/GEO javob dvijoklari (ChatGPT, Perplexity va h.k.) shu schema'dan "Promtchi qanday bog'lanish mumkin?" javobini o'qiydi — hozir ular **begona kanalni** taklif qiladi. Real mijoz "Telegram orqali yozish" tugmasini bossa, noto'g'ri kanalga tushadi.

### 1.2 UZ bosh sahifada yasama/placeholder telefon raqami

`/uz/` (default til, x-default hreflang) sahifasidagi kontakt blokida:

```
value:"+998 90 000 00 00", url:"tel:+998900000000"
```

Bu — klassik placeholder raqam (barcha nollar). Haqiqiy raqam (`app/content/common.py`dagi manba va `/ru/`, `/en/`, hamda BARCHA boshqa ichki sahifalarda ko'ringan qiymat):

```
+998 93 160 67 06
```

`/ru/` va `/en/` bosh sahifalari to'g'ri raqamni ko'rsatadi — faqat `/uz/` (eng ko'p trafik oladigan, default til) xato.

**Root cause (tekshirilgan):** Bosh sahifa `pages.py` orqali emas, `main.py`dagi alohida `_PageCache` (statik `static/index.html` / `index.ru.html` / `index.en.html`) orqali xizmat qiladi (`app/pages.py:1-9` kommentariyasida tasdiqlangan). Bu statik fayllar admin-panel kontenti bilan sinxronlanadigan, lekin **eskirib qolgan** keshdir — `index.html` (uz) eng eski/sinxronlanmagan versiya, `index.ru.html`/`index.en.html`da qisman to'g'irlangan (ular ikkala — eski va yangi — telegram havolasini bir vaqtda saqlab qolgan, bu ham disfunktsiya belgisi).

**Tavsiya:** `static/index.html`, `index.ru.html`, `index.en.html` fayllarini joriy admin-panel/DB kontaktlari asosida qayta generatsiya qilish yoki bosh sahifani ham `pages.py`dagi `_live_org()` mexanizmiga o'tkazish, keyin **productionda qo'lda tekshirish** (bu avtomatlashtirilmagan keshlash zanjiri — kelajakda yana eskirishi mumkin, shuning uchun kontakt ma'lumotlari o'zgarganda bosh sahifa keshini majburiy invalidatsiya qilish jarayoni yo'q bo'lsa, qo'shish tavsiya etiladi).

---

## 2. P1 — YUQORI DARAJALI MUAMMOLAR

### 2.1 Keyword cannibalization: 7 juft deyarli bir xil blog maqola (14/15 post)

Sitemap'da 15 ta UZ blog posti bor, lekin ulardan 14 tasi **7 juft** bo'lib, har bir juftlik xuddi bir xil mavzuni, bir xil (yoki deyarli bir xil) H1/title bilan qamrab oladi:

| # (eski) | # (yangi) | Mavzu | Eski so'z soni (content_length) | Yangi |
|---|---|---|---|---|
| `ai-biznes-jarayonlarini-qanday-avtomatlashtiradi-1` | `-12` | AI biznes jarayonlarini avtomatlashtirishi | 7909 | 10094 |
| `erp-nima-va-crmdan-qanday-farq-qiladi-2` | `-11` | ERP vs CRM | 7746 | 9825 |
| `crm-va-excel-qaysi-biri-biznes-uchun-yaxshiroq-3` | `-10` | CRM vs Excel | 7984 | 10192 |
| `biznesingizga-crm-kerakligini-korsatuvchi-7-ta-belgi-5` | `-9` | CRM kerakligi belgilari | 7938 | 10917 |
| `telegram-bot-biznesga-nima-beradi-6` | `-13` | Telegram bot foydasi | 7713 | 9990 |
| `biznes-uchun-mobil-ilova-qachon-kerak-7` | `-14` | Mobil ilova qachon kerak | 7834 | 10113 |
| `biznesni-avtomatlashtirishni-nimadan-boshlash-kerak-8` | `-15` | Avtomatlashtirishni qayerdan boshlash | 8150 | 10557 |

(`crm-nima-4` — yagona juftsiz post, muammo yo'q.)

Har bir juftda **H1 deyarli bir xil so'zma-so'z**, title'lar bir-biriga juda o'xshash (faqat tire/em-dash va ® belgisi farq qiladi), meta description'lar boshqacha, matn hajmi boshqacha (yangi versiyalar ~25-35% uzunroq). Bu — Google va boshqa qidiruv tizimlari uchun **klassik keyword cannibalization**: bitta kalit so'z bo'yicha ikkita URL raqobatlashadi, ranking signalini bo'lib yuboradi, ikkalasi ham to'liq ranking kuchiga yetolmaydi.

**Ehtimoliy sabab:** So'nggi commit tarixida ("7 ta blog maqola" qo'shilgani) ko'rinib turibdiki, 7 ta maqola qayta yozilib, YANGI slug bilan (9-15) nashr etilgan, lekin **eski versiyalar (1-8, promtchi.db'da hali ham "orphan bo'lmagan holda) sitemapdan/nashrdan olib tashlanmagan yoki 301 bilan yangisiga yo'naltirilmagan**.

**Tavsiya:** Eski 7 ta postni (`-1, -2, -3, -5, -6, -7, -8`) 301 redirect bilan mos yangi versiyaga (`-12, -11, -10, -9, -13, -14, -15`) yo'naltirish, DB'dan noindex qilish yoki sitemapdan chiqarish. Bu — content darajasidagi tuzatish, admin panel orqali amalga oshiriladi (kod bug emas).

### 2.2 CRM va AI xizmat sahifalarida takroriy FAQ savollari (6 URL: uz/ru/en × 2 xizmat)

FAQPage JSON-LD ichida bir xil ma'noni ikki marta so'ragan savol juftlari topildi (matn semantik jihatdan bir xil, javoblar deyarli bir xil):

- **CRM** (`/uz/`, `/ru/`, `/en/xizmatlar/crm/`):
  - "Mavjud CRM (AmoCRM, Bitrix24)ga integratsiya qila olasizmi?" — javob: "...real vaqtli **sinxronizatsiyani** qurganmiz."
  - "Mavjud CRM yoki boshqa tizimlarga integratsiya qilasizmi?" — javob: "...real vaqtli **integratsiyalarni** qurganmiz."
- **AI** (`/uz/`, `/ru/`, `/en/xizmatlar/ai/`):
  - "AI chatbotni Telegram yoki saytga **ulash** mumkinmi?"
  - "AI chatbotni Telegram yoki saytga **integratsiya qilasizmi**?"

**Ta'siri:** FAQPage schema'da 4 ta savoldan 2 tasi aslida bitta savolning ikki varianti — bu foydalanuvchiga ham, AI javob dvijoklariga ham (GEO — bo'lim 3ga qarang) chalkash, sifatsiz signal beradi. Google Rich Results real FAQ farqini kutadi, sinonim-takror savolni emas.

**Tavsiya:** Har bir juftdan bittasini olib tashlash yoki ikkalasini bitta to'liqroq savol/javobga birlashtirish (content darajasida, `app/content/services.py` yoki mos FAQ manba faylida).

### 2.3 `www.promtchi.uz` apex domenga 301 qilmaydi

```
https://www.promtchi.uz/  -> 301 -> https://www.promtchi.uz/uz/   (www saqlanib qoladi)
```

`www` subdomeni to'g'ridan-to'g'ri 200 bilan xizmat qiladi (canonical tegi to'g'ri `https://promtchi.uz/uz/`ga ishora qiladi, shu sababli qidiruv tizimlari duplicate sifatida ko'rmasligi kerak), lekin bu ideal emas — www va apex bir xil server/sertifikatda alohida "domen" sifatida ishlaydi, backlink/ulashish www bilan tarqalsa signal bo'linishi mumkin.

**Tavsiya:** `www.promtchi.uz/*` ni to'g'ridan-to'g'ri `https://promtchi.uz/*`ga 301 qilish (nginx darajasida bitta qoida).

### 2.4 HSTS header yo'q

Production response headerlarida `Strict-Transport-Security` umuman yo'q (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, COOP, X-XSS-Protection — hammasi bor, faqat HSTS yo'q). Bo'lim 15'da batafsil.

### 2.5 Trailing slash'siz URL 301 emas, 404 qaytaradi

```
GET /uz/xizmatlar/crm   (slashsiz) -> 404
GET /uz/xizmatlar/crm/  (slash bilan, kanonik) -> 200
```

Barcha ichki havolalar va sitemap har doim trailing slash bilan yoziladi, shuning uchun bu ichki navigatsiyaga ta'sir qilmaydi (0 ta broken internal link — bo'lim 8). Lekin agar tashqi sayt, ijtimoiy tarmoq yoki foydalanuvchi slashsiz variantga havola qilsa (odatiy holat), ular 404 oladi — 301 bilan kanonik URL'ga yo'naltirilishi kerak edi.

**Tavsiya:** FastAPI/Starlette darajasida trailing-slash normalizatsiyasi (`redirect_slashes` yoki nginx `rewrite`) qo'shish.

---

## 3. P2 — O'RTA DARAJALI MUAMMOLAR

### 3.1 8 ta sahifada title 60 belgidan uzun (SERP'da kesilishi mumkin)

| URL | Uzunlik | Title |
|---|---|---|
| `/uz/xizmatlar/veb-sayt-yaratish/` | 64 | Veb-sayt yaratish — korporativ sayt, landing, web-app \| promtchi |
| `/uz/xizmatlar/telegram-bot/` | 63 | Telegram bot yaratish — buyurtma, CRM, bildirishnoma \| promtchi |
| `/ru/xizmatlar/telegram-bot/` | 63 | Разработка Telegram-ботов — заказы, CRM, уведомления \| promtchi |
| `/en/xizmatlar/telegram-bot/` | 64 | Telegram Bot Development — orders, CRM, notifications \| promtchi |
| `/uz/blog/ai-biznes-jarayonlarini-...-1/` | 61 | AI biznes jarayonlarini qanday avtomatlashtiradi? — promtchi® |
| `/uz/blog/biznesingizga-crm-...-5/` | 65 | Biznesingizga CRM kerakligini ko'rsatuvchi 7 ta belgi — promtchi® |
| `/uz/blog/biznesni-avtomatlashtirishni-...-8/` | 64 | Biznesni avtomatlashtirishni nimadan boshlash kerak? — promtchi® |
| `/uz/blog/biznesni-avtomatlashtirishni-...-15/` | 63 | Biznesni avtomatlashtirishni nimadan boshlash kerak? \| promtchi |

Eslatma: oldingi bosqichda (`SEO_IMPLEMENTATION_REPORT.md`) 6 ta xizmat sahifasi title'i qisqartirilgan edi — lekin yuqoridagi 4 tasi o'sha ro'yxatda bo'lmagan yoki keyinroq qayta uzayib qolgan (masalan, telegram-bot 3 tilda). Qayta tekshirish tavsiya etiladi.

### 3.2 "Duplicate title" — LOJIY IJOBIY (haqiqiy muammo emas), tasdiqlangan

Avtomatik tekshiruv 5 ta "duplicate title" holatini belgiladi (Portfolio index UZ/EN, Blog index UZ/EN, va 3 ta portfolio case-page uz/ru/en). Qo'lda tekshirildi: bular haqiqiy muammo EMAS —
- "Portfolio"/"Blog" so'zlari UZ va EN'da tasodifan bir xil (baynalminal so'zlar); RU versiyasi to'g'ri lokalizatsiya qilingan ("Портфолио", "Блог").
- Case-page nomlari (Chindan Group, Notiq AI, Tizimly) — mijoz/loyiha nomlari, tarjima qilinmasligi kerak.
- Har bir sahifaning canonical'i o'ziga ishora qiladi, hreflang to'g'ri — Google bularni duplicate emas, bir sahifaning tarjima variantlari sifatida tushunadi.

Harakat talab qilinmaydi.

---

## 4. P3 — PAST DARAJALI

7 ta blog post meta description'i 161 belgi (160 chegara + 1 belgi) — amalda SERP'ga deyarli ta'sir qilmaydi, ixtiyoriy tuzatish.

---

## 5. SITEMAP.XML TEKSHIRUVI

```
GET /sitemap.xml -> 200, valid XML (xmlns to'g'ri, xhtml:link namespace bilan)
Jami URL: 84
Duplicate URL: 0
Redirect URL (sitemap ichida): 0
Noindex URL (sitemap ichida): 0
Canonical bilan mos kelmaslik: 0
UZ/RU/EN mavjudligi: UZ=39, RU=24, EN=24 (blog UZ-only, 15 ta post — bu qasddan, RU/EN blog hali yo'q)
```

Har bir `<url>` yozuvida `xhtml:link hreflang` orqali uz-UZ/ru-RU/en/x-default to'g'ri belgilangan (asosiy sahifalar uchun); blog postlari uchun faqat mavjud tildagi o'z-o'ziga hreflang (to'g'ri — mavjud bo'lmagan tarjima va'da qilinmagan, `app/pages.py`dagi qasddan qilingan arxitektura qaroriga mos).

**Xulosa: Sitemap 100% sog'lom.**

---

## 6. ROBOTS.TXT TEKSHIRUVI

```
User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/admin/
Sitemap: https://promtchi.uz/sitemap.xml
```

- Muhim public sahifalar bloklanmagan — tasdiqlangan (`/uz/`, `/xizmatlar/*`, `/yechimlar/*`, `/portfolio/*`, `/blog/*`, `/faq/`, `/biz-haqimizda/`, `/aloqa/` hammasi `Allow: /` ostida, alohida disallow yo'q).
- Faqat admin panel va admin API bloklangan — to'g'ri.
- Sitemap satri to'g'ri ko'rsatilgan.

**Xulosa: robots.txt to'g'ri konfiguratsiya qilingan.**

---

## 7. HREFLANG TEKSHIRUVI

Barcha 84 sahifada hreflang teglari mavjud (0 ta yo'q). Reciprocity avtomatik tekshirildi: har bir sahifadagi hreflang target sahifa productionda 200 qaytaradimi va u orqaga shu sahifaga hreflang bilan bog'lanadimi — **0 ta nomuvofiqlik topilmadi**.

Qo'lda 3 ta chuqur sahifa uchun switcher xatti-harakati production HTML'dan tasdiqlandi (server-rendered, browser kerak emas — havolalar to'g'ridan-to'g'ri HTML'da):

| Sahifa | UZ | RU | EN |
|---|---|---|---|
| `/uz/xizmatlar/crm/` | o'zi | `/ru/xizmatlar/crm/` | `/en/xizmatlar/crm/` |
| `/uz/portfolio/notiq-ai/` | o'zi | `/ru/portfolio/notiq-ai/` | `/en/portfolio/notiq-ai/` |
| `/uz/blog/crm-nima-4/` (faqat UZ'da mavjud) | o'zi | `/ru/blog/` (index'ga fallback) | `/en/blog/` (index'ga fallback) |

Til almashtirgich **joriy sahifani saqlaydi** (tarjima mavjud bo'lganda) va **mavjud bo'lmagan tarjima uchun bosh sahifaga emas, tegishli til bo'limi indeksiga** fallback qiladi (masalan blog post uchun `/ru/blog/`) — bu to'g'ri, ataylab shunday arxitektura qilingan (`app/pages.py` kodidagi kommentariyada tasdiqlangan) va Google'ga mavjud bo'lmagan tarjimani va'da qilmaydi.

**Xulosa: Hreflang 100% to'g'ri va reciprocal.**

---

## 8. INTERNAL LINK GRAPH

- **Orphan pages: 0.** Sitemapdagi barcha 84 sahifa kamida 1 ta ichki havola orqali topiladi.
- **1 ta kiruvchi havolaga ega sahifalar: 8 ta** — barchasi eski (1-8 raqamli) blog postlari, chunki ular endi asosiy blog-related bloklardan chiqarilgan (bo'lim 2.1'dagi cannibalization muammosining bir belgisi ham shu).
- **Broken internal links: 0.** Barcha ichki havola target'lari (mailto:/tel: dan tashqari, ular tekshiruv doirasidan chiqarib tashlandi chunki HTTP emas) 200 qaytardi.
- **Broken external links: 0.** Saytda faqat 2 ta noyob tashqi havola bor: `instagram.com/promtchiuz` (200), `t.me/promtchiuz` (200) — ikkalasi ham productionda ishlaydi. (Bosh sahifadagi noto'g'ri `t.me/promtchi` havolasi "broken" emas — texnik jihatdan 200 qaytaradi, lekin **noto'g'ri entity'ga** ishora qiladi, bo'lim 1.1'ga qarang.)

**Ideal struktura tekshiruvi:** Homepage → Services (`/xizmatlar/`) → Service pages → Blog/Cases → Contact zanjiri productionda mavjud va ishlaydi (har bir xizmat sahifasi 9-16 ta ichki havola oladi, portfolio case'lar contact'ga link beradi). Blog → Service va Service → Blog o'zaro bog'lanishi mavjud (`related` bloklar orqali, yangi 9-15 postlarda ko'proq).

---

## 9. INDEXABILITY MATRIX (qisqartirilgan)

To'liq jadval: `indexability_matrix.tsv` (84 qator). Barcha 84 ustun: **Status=200, Indexable=YES, Canonical_OK=YES, H1=1, Hreflang≥2**. Namuna:

| URL | Status | Indexable | Canonical | H1 | Schema | Hreflang | Internal Links In |
|---|---|---|---|---|---|---|---|
| /uz/ | 200 | YES | YES | 1 | 2 | 4 | 39 |
| /uz/xizmatlar/crm/ | 200 | YES | YES | 1 | 5 | 4 | 16 |
| /uz/blog/crm-nima-4/ | 200 | YES | YES | 1 | 4 | 2 | 1 |
| /uz/blog/...-9/ (yangi) | 200 | YES | YES | 1 | 4 | 2 | 2 |

---

## 10. XAVFSIZLIK HEADERLARI (SEO bilan bog'liq qismi)

```
content-security-policy: mavjud, yaxshi konfiguratsiya qilingan
x-content-type-options: nosniff  ✅
x-frame-options: DENY  ✅
referrer-policy: strict-origin-when-cross-origin  ✅
permissions-policy: mavjud  ✅
cross-origin-opener-policy: same-origin  ✅
x-xss-protection: 0  (zamonaviy standart, to'g'ri)
strict-transport-security: ❌ YO'Q
```

To'liq tahlil `PRODUCTION_GEO_AUDIT.md` bo'lim "Xavfsizlik"da davom etadi (dublikat qilmaslik uchun).

---

## 11. GOOGLE SEARCH CONSOLE / BING — QO'LDA BAJARILADIGAN CHECKLIST

Brauzer orqali GSC/Bing hisobiga kirish authentication talab qiladi — avtomatlashtirilmadi, quyida qo'lda bajariladigan ro'yxat:

**Real tashqi tekshiruv (login talab qilinmaydi):** live web-qidiruv orqali `site:promtchi.uz` va oddiy `promtchi.uz` so'rovlari sinovdan o'tkazildi (2026-09-16) — **domendan birorta ham sahifa natijalarda chiqmadi** (faqat aloqasi yo'q boshqa `.uz` saytlar va loyihaning ochiq GitHub repo'si ko'rindi). Bu — saytning hali qidiruv tizimlari tomonidan indekslanmaganining (yoki indeks bo'sh/eski bo'lganining) real, joriy dalili. Yuqoridagi texnik SEO fundamenti (sitemap, canonical, hreflang, schema) to'g'ri ishlayotgani buni o'zgartirmaydi — **IMPLEMENTED ≠ INDEXED**. Property tasdiqlash va sitemap submit qilish (pastdagi checklist) shuning uchun birinchi navbatdagi amaliy qadam.

Google `google-site-verification`, Bing `msvalidate.01`, Yandex `yandex-verification` meta teglari bosh sahifa `<head>`'ida topilmadi — agar GSC/Bing egalik huquqi tasdiqlangan bo'lsa, bu DNS TXT yozuvi orqali qilingan bo'lishi kerak (tashqaridan HTML orqali tekshirib bo'lmaydi).

**Google Search Console:**
- [ ] Property tasdiqlangan (DNS yoki HTML tag orqali)
- [ ] `sitemap.xml` GSC'ga submit qilingan
- [ ] Bosh sahifa indekslangan
- [ ] Xizmat sahifalari indekslangan
- [ ] Blog sahifalari indekslangan (7 ta eski postni indeksdan chiqarish so'ralishi kerak — bo'lim 2.1)
- [ ] Tasodifiy noindex yo'qligi tasdiqlangan (bu auditda avtomatik tekshirildi — 0 ta noindex topilmadi)
- [ ] Canonical to'g'riligi tasdiqlangan (bu auditda avtomatik tekshirildi — 0 muammo)
- [ ] Hreflang to'g'riligi tasdiqlangan (bu auditda avtomatik tekshirildi — 0 muammo)
- [ ] Core Web Vitals monitoring yoqilgan

**Bing Webmaster Tools:**
- [ ] Sitemap submit qilingan
- [ ] IndexNow ulangan (pastga qarang)
- [ ] robots.txt Bing tomonidan to'g'ri o'qilgani tekshirilgan

### IndexNow

Hozircha implementatsiya qilinmagan. Arxitekturaga mos keladi (FastAPI + admin content DB) — content o'zgarganda (yangi blog post, xizmat sahifasi yangilanishi) IndexNow API'ga POST yuborish oson qo'shiladi (`app/telegram.py`dagi kabi oddiy webhook chaqiruvi). **Tavsiya, majburiy emas** — keyingi bosqichda ko'rib chiqilishi mumkin.

---

## 12. AI CRAWLER ACCESS

Server darajasida User-Agent bo'yicha blocklash yo'qligi tasdiqlandi — barcha asosiy AI/qidiruv botlari 200 oladi:

```
GPTBot          -> 200
ClaudeBot       -> 200
anthropic-ai    -> 200
PerplexityBot   -> 200
Google-Extended -> 200
Bingbot         -> 200
Googlebot       -> 200
```

`/admin` va `/api/admin/*` to'g'ri himoyalangan (`/admin` — `noindex,nofollow` meta bilan SPA login qobig'i, haqiqiy ma'lumot yo'q; `/api/admin/leads` — auth'siz so'rovga 401 qaytaradi). Ochiq `/api/content` — faqat public narx/paket ma'lumotlarini qaytaradi, maxfiy emas.

**Xulosa: AI crawlerlar uchun to'siq yo'q, admin/maxfiy endpointlar to'g'ri himoyalangan.**
