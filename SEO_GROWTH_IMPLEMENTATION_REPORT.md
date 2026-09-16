# SEO_GROWTH_IMPLEMENTATION_REPORT.md — promtchi.uz

**Bosqich:** 2-bosqich — SEO + AI/GEO Growth Implementation (organik trafik, search intent, AI/GEO ko'rinuvchanlik).
**Sana:** 2026-09-16.
**Asos:** `SEO_AUDIT.md` va `SEO_IMPLEMENTATION_REPORT.md` (1-bosqich, texnik SEO audit) o'qib chiqilgach boshlangan.

**Fake-data siyosati (qat'iy amal qilindi):** yangi statistika, mijoz, sharh, case natija yoki LocalBusiness schema QO'SHILMADI. Yangi kontentning barchasi — allaqachon saytning boshqa joylarida tasdiqlangan real faktlar (Chindan Group ~70%, Tizimly 150+ kompaniya, Notiq AI STT, AmoCRM/Bitrix24/UTEL/Meta Ads integratsiyalari) yoki umumiy, uydirilmagan xizmat/jarayon tavsifi.

---

## 1. Oldingi holat (1-bosqichdan keyin)

- 7 ta xizmat sahifasi allaqachon mavjud edi (web, mobile, crm, erp, ai, telegram-bot, automation) — barchasi to'liq SEO infratuzilmaga ega (title/meta/canonical/hreflang/breadcrumb/schema).
- Portfolio case'larda `industry`/`goal`/`features`/`integrations`/`process` maydonlari DB'da bor edi, lekin bo'sh (real ma'lumot kutilmoqda).
- Blog tizimi (Post modeli, admin CRUD) bor edi, lekin **yangi maqolalar yo'q** edi.
- Xizmat sahifalarida "Integratsiyalar" va "Ish jarayoni" bo'limlari **yo'q** edi.
- 5 ta xizmatning (CRM, ERP, AI, Telegram bot, Automation) meta description'ida "Toshkent" so'zi yo'q edi (faqat Web va Mobil'da bor edi).
- **Bosh sahifaning asosiy navigatsiyasi (top nav, mobil menyu, footer, "Xizmatlar" bo'limidagi 4 ta karta) faqat sahifa ichidagi anchor'larga (`#xizmat`, `#aloqa`, `#faq`) havola berardi — haqiqiy indexable sahifalarga (`/uz/xizmatlar/`, `/uz/yechimlar/`, `/uz/faq/`, `/uz/biz-haqimizda/`, `/uz/aloqa/`) BIRORTA HAM havola yo'q edi.** Bu — eng yuqori PageRank'ga ega sahifaning o'zi shu muhim sahifalarga deyarli hech qanday link equity o'tkazmasligini anglatardi.
- Blog va xizmat/portfolio sahifalari orasida dinamik ichki bog'lanish (topical cluster) yo'q edi.
- Blog posti matni oddiy `white-space:pre-wrap` bilan chiqardi — sarlavha (H2), ro'yxat yoki ichki havola bo'lishi mumkin emas edi.
- "Biz haqimizda" sahifasida AI/GEO uchun aniq strukturalangan "Promtchi nima/qayerda/kimlar uchun" Q&A bloki yo'q edi.

## 2. Nima qilindi

### 2.1 Xizmat sahifalari — yangi bo'limlar va search intent kengaytmasi

- Har bir xizmat (`app/content/services.py`, DB `Service.data_{lang}`) uchun yangi **`integrations`** va **`process`** maydonlari qo'shildi:
  - Integratsiyalar — faqat allaqachon tasdiqlangan real imkoniyatlar (masalan CRM: AmoCRM, Bitrix24, UTEL, Meta Ads, Telegram Bot API — Tizimly case'idan va mavjud FAQ javobidan).
  - Ish jarayoni — 5 bosqichli umumiy, uydirilmagan jarayon tavsifi (konsultatsiya → dizayn/reja → ishlab chiqish → test/joylashtirish → qo'llab-quvvatlash), har xizmat uchun moslashtirilgan.
  - `templates/service_detail.html`ga yangi "Integratsiyalar" / "Ish jarayoni" bo'limi qo'shildi (raqamlangan `process-list` uslubi, `static/site.css`).
  - `app/schemas.py::ServiceLangIn`ga `integrations`/`process` maydonlari qo'shildi — admin panel orqali tahrirlash saqlanadi.
  - `static/admin.html`ga mos forma maydonlari qo'shildi (xizmat tahrirlash formasida).
- **Location SEO**: CRM, ERP, AI, Telegram bot, Automation xizmatlarining `meta` va `for_whom` matniga "Toshkentda" / "Toshkent va O'zbekiston bo'ylab" semantik qamrovi tabiiy qo'shildi (RU/EN uchun ham mos tarzda). Barcha meta description 160 belgidan oshmasligi tekshirildi va tuzatildi.
- **DB migratsiya** (`app/db.py::run_data_fixups`, bo'lim 7): allaqachon seed qilingan production `Service` qatorlariga yangi `meta`/`for_whom`/`integrations`/`process` bir martalik, `Setting` markeri (`service_geo_content_v1_done`) bilan himoyalangan holda qo'llaniladi — avvalgi `_TITLE_FIXES` naqshi bilan bir xil.

### 2.2 Blog — 7 ta yangi original maqola (topical authority)

`app/content/blog_seed.py` (yangi fayl) — TZda so'ralgan barcha 7 mavzu, o'zbek tilida, original va inson o'qiydigan uslubda yozildi:

1. Biznesingizga CRM kerakligini ko'rsatuvchi 7 ta belgi
2. CRM va Excel: qaysi biri biznes uchun yaxshiroq?
3. ERP nima va CRM'dan qanday farq qiladi?
4. AI biznes jarayonlarini qanday avtomatlashtiradi?
5. Telegram bot biznesga nima beradi?
6. Biznes uchun mobil ilova qachon kerak?
7. Biznesni avtomatlashtirishni nimadan boshlash kerak?

Har biri: H1(title)/SEO title/meta description/answer-first kirish/H2 bo'limlar/ro'yxatlar/amaliy misollar (faqat real case'larga — Chindan Group, Tizimly, Notiq AI — havola qilingan)/qisqa FAQ bloki/ichki havolalar (tegishli xizmat + portfolio + aloqa sahifasiga) bilan.

`app/db.py::run_data_fixups` bo'lim 8 — bir martalik seed (`blog_seo_articles_v1_done` markeri), admin keyinchalik tahrirlasa/o'chirsa qayta yaratilmaydi.

**Xavfsiz matn render'i** — `app/content/markdown_lite.py` (yangi modul): admin yozgan oddiy matnni avval **to'liq escape qiladi** (XSS'dan himoya), so'ng FAQAT whitelist qilingan minimal belgilashni (`## sarlavha`, `- band`, `**qalin**`, `[matn](/ichki-havola/)` — faqat http(s)/ ichki yo'llar) xavfsiz HTML'ga aylantiradi. `templates/blog_detail.html` endi haqiqiy `<h2>`/`<ul>`/`<a>` bilan render qiladi (oldin faqat pre-wrap oddiy matn edi).

### 2.3 Topical cluster — blog ↔ xizmat dinamik ichki bog'lanish

- Har bir maqola `tags`ida BITTA asosiy xizmat `key`i bor (masalan `crm`) — bu orqali:
  - Xizmat sahifasida yangi **"Mavzu bo'yicha maqolalar"** bo'limi (`app/pages.py::_posts_tagged`) — shu xizmatga tegishli maqolalarni dinamik ko'rsatadi (id'ga bog'liq emas, tag orqali).
  - Maqola sahifasida **"tegishli xizmat"** CTA (`related_service`, `app/pages.py::blog_detail`) — maqolaning birinchi mos tag'i asosida to'g'ri xizmat sahifasiga yo'naltiradi.
- Zanjir: **Blog → Xizmat → Portfolio → Aloqa** endi to'liq ishlaydi (masalan CRM maqolasi → CRM xizmati → Chindan Group case → Aloqa).

### 2.4 Bosh sahifa — orphan-page va internal-linking tuzatishi (eng muhim topilma)

Barcha 3 tilda (`static/index.html`, `.ru.html`, `.en.html`):

- "Xizmatlar" bo'limidagi 4 ta katta karta endi `#aloqa` o'rniga tegishli **haqiqiy xizmat sahifasiga** (`/uz/xizmatlar/veb-sayt-yaratish/`, `/avtomatlashtirish/`, `/ai/`, `/crm/` va RU/EN mos slug'lar) olib boradi.
- Footer'ga yangi "Sahifalar" navigatsiya bloki qo'shildi — `/xizmatlar/`, `/yechimlar/`, `/portfolio/`, `/blog/`, `/faq/`, `/biz-haqimizda/`, `/aloqa/` ga to'g'ridan-to'g'ri havolalar (avval bular FAQAT ichki SSR sahifalarning o'zaro navigatsiyasida bor edi, bosh sahifadan yo'q edi).

Natija: eng ko'p tashrif buyuriladigan sahifa (bosh sahifa) endi barcha muhim indexable sahifalarga real link equity beradi.

### 2.5 AI/GEO — "Biz haqimizda" entity Q&A bloki

`app/content/about.py`ga `entity_qa` (5 ta savol-javob, 3 tilda) qo'shildi: "Promtchi nima?", "Qayerda joylashgan?", "Qanday xizmatlar?", "Kimlar uchun?", "Qanday texnologiyalar?" — barchasi allaqachon tasdiqlangan faktlar asosida (2023, Toshkent, 7 xizmat, FastAPI/Django/PostgreSQL/Flutter/aiogram). `templates/about.html`ga chiqarildi va `FAQPage` JSON-LD schema qo'shildi (`app/pages.py::about_page`) — AI qidiruv tizimlari (ChatGPT, Perplexity, Google AI Overviews) uchun kompaniya identifikatsiyasini aniqlashtiradi.

## 3. O'zgargan/yaratilgan fayllar

**Yangi:** `app/content/blog_seed.py`, `app/content/markdown_lite.py`, `SEO_GROWTH_IMPLEMENTATION_REPORT.md`

**O'zgartirilgan:** `app/content/services.py`, `app/content/about.py`, `app/content/common.py`, `app/db.py`, `app/pages.py`, `app/schemas.py`, `static/admin.html`, `static/index.html`, `static/index.ru.html`, `static/index.en.html`, `static/site.css`, `templates/about.html`, `templates/blog_detail.html`, `templates/service_detail.html`

## 4. Search intent / semantic coverage xulosasi

Har xizmat uchun asosiy va ikkinchi darajali kalit so'zlar mavjud kontent tuzilmasiga (title/meta/h1/value/for_whom/includes/features/integrations) tabiiy tarqatilgan edi (1-bosqichda allaqachon qurilgan); bu safar qo'shildi:

- **CRM**: +"Toshkentda CRM", +AmoCRM/Bitrix24/UTEL/Meta Ads integratsiya ro'yxati, +2 ta yangi blog maqola (CRM belgilari, CRM vs Excel).
- **ERP**: +"Toshkentda ERP", +buxgalteriya/ombor integratsiya ro'yxati, +1 blog maqola (ERP vs CRM — ikkala xizmat sahifasida ham ko'rinadi).
- **AI**: +"Toshkentda AI yechimlar", +Telegram/mobil integratsiya ro'yxati, +1 blog maqola.
- **Telegram bot**: +"Toshkentda Telegram bot", +1 blog maqola.
- **Automation**: +"Toshkentda avtomatlashtirish", +1 blog maqola.
- **Web/Mobile**: allaqachon Toshkent qamrovi bor edi — endi +integratsiya/jarayon bo'limlari, +1 blog maqola (mobil vs veb, ikkala sahifada ham ko'rinadi).

## 5. Schema / Sitemap / Canonical / Hreflang

- Yangi blog postlari avtomatik `sitemap.xml`ga qo'shiladi (`app/pages.py::_all_urls`/`sitemap` — o'zgarishsiz, mavjud DB-based logika allaqachon buni qamrab olgan).
- Har bir xizmat sahifasi `Service`/`FAQPage` JSON-LD'ni saqlab qoldi, endi integratsiya/jarayon matni ham schema `description`ga bilvosita ta'sir qilmaydi (schema alohida `service_schema()`dan keladi — o'zgarmadi).
- "Biz haqimizda" sahifasiga yangi `FAQPage` schema qo'shildi.
- Canonical/hreflang — o'zgarishsiz, mavjud infratuzilma barcha yangi sahifalarni ham avtomatik qamrab oladi (blog postlari `hreflang_paths={lang: own_path}` bilan — tarjima yo'qligi haqida yolg'on va'da qilinmaydi, 1-bosqichdagi siyosatga mos).

## 6. Test natijalari

- `pytest tests/` — **23/23 o'tdi** (o'zgarishlardan keyin qayta ishga tushirildi, xatosiz).
- `python -c "ast.parse(...)"` — barcha o'zgargan/yangi Python fayllar (`db.py`, `pages.py`, `blog_seed.py`, `markdown_lite.py`) sintaksis xatosiz.
- `node --check` — barcha 4 ta HTML fayldagi (`admin.html`, `index.html`, `.ru.html`, `.en.html`) inline JS (JSON-LD bloklari chiqarib tashlab) sintaksis xatosiz.
- **To'liq lokal smoke-test**: bo'sh SQLite baza bilan dev server ishga tushirilib (`ENV=development`), barcha migratsiyalar 0'dan qayta ishlatildi:
  - Barcha 76 ta sitemap URL + bosh sahifa (3 til) + `/admin` + `/robots.txt` = **81/81 URL — 200 OK**.
  - Har bir sahifada aynan 1 ta `<h1>`, `canonical`, kamida 1 ta JSON-LD schema — **0 ta muammo**.
  - 7 ta yangi blog maqola to'g'ri slug bilan yaratildi, `/uz/blog/`da ko'rinadi.
  - Xizmat sahifalaridagi "Integratsiyalar"/"Ish jarayoni"/"Mavzu bo'yicha maqolalar" bo'limlari CRM/ERP/AI/Telegram bot/Web/Mobile/Automation — barchasida to'g'ri (tag orqali) ko'rsatildi; CRM sahifasida aynan CRM'ga tegishli 3 maqola chiqishi tag mapping tuzatilgandan keyin tasdiqlandi.
  - Bosh sahifadagi 4 ta xizmat kartasi va yangi footer havolalari — barchasi to'g'ri sahifaga olib borishi tasdiqlandi (UZ/RU/EN).
  - Meta description uzunligi (HTML entity artefaktisiz) barcha xizmatlarda ≤160 belgi ekanligi alohida tekshirildi.
  - Test tugagach lokal baza ORIGINAL holatiga qaytarildi (production'ga hech qanday to'g'ridan-to'g'ri ta'sir qilinmadi — bu faqat lokal `.gitignore`langan sinov nusxasi edi).

## 7. Qolgan qo'lda bajariladigan ishlar

1. **Push va production deploy** — bu o'zgarishlar hali `git push` qilinmagan (foydalanuvchi tasdig'ini kutmoqda, chunki push production'da avtomatik deploy va real DB migratsiyani ishga tushiradi).
2. Google Search Console'ga yangilangan sitemap qayta yuborish (7 ta yangi blog URL uchun).
3. Google Rich Results Test — yangi `FAQPage` (About sahifa) va yangilangan Service schema'larni rasmiy tasdiqlash (bu muhitda tashqi vosita ishlatib bo'lmaydi).
4. Real Lighthouse/PageSpeed o'lchovi — yangi CSS (`process-list`, `article-body`) sahifa og'irligini sezilarli oshirmagani taxmin qilinadi (bir necha KB), lekin real o'lchov tavsiya etiladi.
5. Kelajakda: portfolio case'lariga real `industry`/`goal`/`integrations`/`process` — biznesdan real ma'lumot kelganda (hozir ham bo'sh, uydirilmagan).
6. Kelajakda: yangi blog maqolalari uchun RU/EN tarjima — agar biznes talab qilsa (hozir ataylab faqat UZ, sayt siyosatiga mos — "tarjima yo'qligini yolg'on da'vo qilmaslik").
