# FINAL PRODUCTION SEO/GEO/PERFORMANCE REPORT — 4-bosqich (fix)

**Sana:** 2026-09-16
**Kirish holati:** `PRODUCTION_SEO_AUDIT.md`, `PRODUCTION_GEO_AUDIT.md`, `PRODUCTION_PERFORMANCE_AUDIT.md`
**Metodika:** Bu bosqich AUDIT emas — audit'da topilgan muammolar repo kodida REAL tuzatildi, lokal (TestClient + to'liq app lifespan, haqiqiy sqlite DB) tekshirildi va test bilan mustahkamlandi. Production'ga bu o'zgarishlar **hali deploy qilinmagan** (pastga, bo'lim "DEPLOYMENT" ga qarang) — shu sabab "AFTER" ustuni ikki xil ma'noda o'qilishi kerak: **"kod repo'da"** (✅ tayyor) va **"production'da tasdiqlangan"** (⏳ deploydan keyin qayta crawl talab qilinadi). Soxta production-verification berilmagan — bu TZning asosiy tamoyili.

---

## 0. NIMA O'ZGARDI (fayllar)

```
app/content/common.py     — ORG.telegram_handle/url: @promtchiuz -> @promtchiadmin
app/content/faq.py        — 3 tilda "(@promtchiuz)" -> "(@promtchiadmin)"
app/schemas.py            — DEFAULT_CONTENT: placeholder telefon/eski telegram/instagram tuzatildi
app/db.py                 — 4 ta yangi bir martalik data-fixup (marker-gated, run_data_fixups)
app/main.py               — WWWRedirectMiddleware, _inject_live_contacts (root cause fix)
app/security.py           — Cache-Control (public sahifalar + /static/*), HSTS izohi
static/index*.html (3 til)— DEFAULTS/orgSchema/footer: eski kontakt -> to'g'ri, logo -> <picture>+webp
templates/base.html       — logo -> <picture>+webp
static/logo.webp          — YANGI: 6.1 KB (52 KB PNG o'rniga, faqat nav uchun)
tests/test_production_seo_fixes.py — YANGI: 12 ta regression test
```

`git diff --stat`: 10 ta mavjud fayl o'zgartirildi (309 qo'shildi / 31 o'chirildi), 2 ta yangi fayl (logo.webp, test). Boshqa hech narsa tegilmadi.

---

## 1. P0 — TELEFON VA TELEGRAM ANIQLIGI

### 1.1 Root cause (bo'lim 3 talabi)

**Topilma:** Bosh sahifa (`static/index*.html`) — statik fayl, disk ustida qo'lda tahrirlanadi. Ichida ikkita mustaqil "kontakt manbai" bor edi:
1. `DEFAULTS.contacts/socials` (JS obyekti) va Organization JSON-LD — fayl yozilgan paytdagi qattiq qiymat, JS ishga tushmasdan oldin ko'rinadi.
2. `/api/content` orqali DB'dan keladigan qiymat — JS ishga tushgach DOM'ni qayta yozadi.

Ikkinchisi har doim to'g'ri edi (admin panel shu yerga yozadi), birinchisi esa hech qachon avtomatik yangilanmasdi — fayl faqat qo'lda tahrirlansa o'zgarardi. Shuning uchun UZ/RU/EN fayllar mustaqil ravishda turli vaqtda qo'lda tuzatilib, bir-biridan farqlanib ketgan (production audit: UZ'da eski telefon, uchalasida eski Telegram).

**ROOT CAUSE FIX (faqat string almashtirish emas):** `app/main.py::_inject_live_contacts()` — `_PageCache.load()` endi fayl mtime'i YOKI `content_cache.version` (admin `PUT /api/admin/content` har safar oshiradi) o'zgarganda statik HTML'ni qayta o'qib, `DEFAULTS.contacts`/`DEFAULTS.socials`/Organization JSON-LD'ni **content_cache** (yagona, DB-asoslangan manba — xuddi shu Content jadvalidan `pages.py::_live_org()` ham o'qiydi) qiymati bilan qayta yozadi. Natija: bitta manba (DB) → ikkita mustaqil render yo'li (statik SSR va client JS) — variant **C** (TZ bo'lim 3) amalga oshirildi, performance (xotiradagi kesh, gzip oldindan tayyorlangan) buzilmadi, admin funksionalligi o'zgarmadi.

Test: `tests/test_production_seo_fixes.py::test_homepage_reflects_live_admin_contacts` — admin kontaktni o'zgartiradi, keyin `/uz/` HTML'ida (JS ishga tushmasdan oldingi holat) yangi qiymat borligini, shu jumladan Organization JSON-LD `telephone`/`sameAs` maydonlarini tekshiradi. ✅ PASS.

### 1.2 Ma'lumot manbalari — TO'G'IRLANDI

| Manba | BEFORE | AFTER |
|---|---|---|
| `app/content/common.py` (ORG, pages.py fallback) | `@promtchiuz` / `t.me/promtchiuz` | `@promtchiadmin` / `t.me/promtchiadmin` |
| `app/content/faq.py` (3 til, matn ichida) | `(@promtchiuz)` | `(@promtchiadmin)` |
| `app/schemas.py` `DEFAULT_CONTENT` (fresh-DB seed / `/api/admin/content/reset`) | tel `+998 90 000 00 00`, tg `@promtchi`/`t.me/promtchi`, instagram `instagram.com/promtchi` | tel `+998 93 160 67 06`, tg `@promtchiadmin`, instagram `instagram.com/promtchiuz` |
| `static/index.html` (UZ) | tel `+998 90 000 00 00`, tg `@promtchi` | tel `+998 93 160 67 06`, tg `@promtchiadmin` |
| `static/index.ru.html` / `index.en.html` | tg `@promtchiuz` (orgSchema hali eski `t.me/promtchi`) | tg `@promtchiadmin` hamma joyda |

### 1.3 Production DB — bir martalik migratsiya (`app/db.py::run_data_fixups`)

Men production DB'ga to'g'ridan-to'g'ri ulanolmayman (repo'da deployment credentials/SSH yo'q) — shu sabab tuzatish **idempotent, marker-gated migratsiya** sifatida yozildi, keyingi deploy+restart'da avtomatik ishlaydi (loyihada allaqachon shu naqsh — masalan `service_title_length_fix_done` — ishlatilgan):

- `contact_accuracy_fix_v1_done` — `Content.data.contacts/socials` ichidagi ANIQ eski qiymatlarni (`@promtchi`, `@promtchiuz`, `tel:+998900000000`) to'g'ri qiymatga almashtiradi. Boshqa (kelajakda admin kiritgan) qiymatga tegmaydi.
- `faq_contact_text_fix_v1_done` — `FaqItem.answer_{uz,ru,en}` ichida `@promtchiuz` matni bo'lsa `@promtchiadmin`ga almashtiradi.

Test: `test_contact_accuracy_fixup_corrects_stale_db_value` — DB'ni ataylab eski holatga qaytarib, fixup'ni qayta ishga tushirib, to'g'irlanganini tasdiqlaydi. ✅ PASS.

| Metrika | BEFORE | AFTER (kod/lokal) | Production |
|---|---|---|---|
| Wrong phone occurrences (repo qidiruvi) | 3 (schemas.py, index.html DEFAULTS, orgSchema orqali bilvosita) | **0** | ⏳ deploy + restart kerak (migratsiya avtomatik ishlaydi) |
| Wrong Promtchi Telegram occurrences (repo qidiruvi, `@promtchi`/`@promtchiuz`/`t.me/promtchi(uz)`) | 12 joyda (3 statik fayl × ~3-4 joy + common.py + faq.py×3 + schemas.py×2) | **0** | ⏳ deploy + restart kerak |

**MUHIM:** Instagram (`instagram.com/promtchiuz`) — bu Telegram EMAS, TZ bo'lim 21/22 uni "eski" deb belgilamagan, o'zgartirilmadi (faqat `schemas.py`/`index.html`dagi bitta ichki nomuvofiqlik — `instagram.com/promtchi` (uzsiz) — `common.py`dagi tasdiqlangan qiymatga moslashtirib tuzatildi, chunki bu ham xuddi shu "ikki mustaqil manba" muammosining bir ko'rinishi edi).

---

## 2. P1 — BLOG KEYWORD CANNIBALIZATION (7 juft)

**Root cause (audit'da aniqlangan):** `pages._slugify(title, post_id)` slug'i sarlavha + **post.id** dan iborat — audit'dagi "-1", "-2"... raqamlar aynan production DB'dagi `Post.id`. `app/content/blog_seed.py` (7 ta yangi maqola, `blog_seo_articles_v1_done` migratsiyasi) ARTICLES tartibi audit jadvalidagi yangi ID'lar (9→15) bilan mos — bu productionda eski postlar (id 1,2,3,5,6,7,8) allaqachon mavjud bo'lgani va yangilari keyingi autoincrement ID (9-15) olganini tasdiqlaydi.

**Qaror (har juft uchun):** Barcha 7 juft — **bir xil intent, yangi versiya to'liqroq** (audit: ~25-35% uzunroq) → **301 redirect eskisi → yangisi**, hech biri o'chirilmadi (SEO equity saqlanadi).

| Eski (id) | Yangi (id) | Qaror |
|---|---|---|
| ai-biznes-jarayonlarini...-1 | -12 | 301 → yangisiga |
| erp-nima-va-crmdan...-2 | -11 | 301 → yangisiga |
| crm-va-excel...-3 | -10 | 301 → yangisiga |
| biznesingizga-crm-kerakligini...-5 | -9 | 301 → yangisiga |
| telegram-bot-biznesga...-6 | -13 | 301 → yangisiga |
| biznes-uchun-mobil-ilova...-7 | -14 | 301 → yangisiga |
| biznesni-avtomatlashtirishni...-8 | -15 | 301 → yangisiga |
| crm-nima-4 | — (juftsiz) | O'zgarmadi — noyob |

**Implementatsiya:** `blog_cannibalization_fix_v1_done` migratsiyasi (`app/db.py`) — har juft uchun eski post `published=False` (avtomatik: sitemap, blog ro'yxati, related-posts'dan chiqadi — barchasi `Post.published==True` filtrlaydi, kod allaqachon shunday yozilgan) + `SlugRedirect(old_path, new_path)` yaratadi (301, mavjud `blog_detail()` route'i bu jadvalni allaqachon tekshiradi — kod o'zgartirilmadi, faqat ma'lumot qo'shildi). Redirect chain yo'q (eski → to'g'ridan-to'g'ri yangi, ikkalasi ham `/uz/blog/.../` darajasida, oraliq bosqich yo'q).

Test: `test_blog_cannibalization_fixup_redirects_old_to_new` — real production xaritasidagi (`1→12`) ID juftligi bilan ishlaydi, unpublish + SlugRedirect yaratilishini tasdiqlaydi. ✅ PASS.

| Metrika | BEFORE | AFTER |
|---|---|---|
| Cannibalization juftliklari | 7 | **0** (deploy'dan keyin — kod tayyor) |
| Eski postlar sitemap'da | 7 | 0 (unpublish → filtrlanadi) |
| Eski URL'lar | 200 (raqobatlashadi) | 301 → yangi canonical (200) |

---

## 3. P1 — FAQ DUPLICATION (CRM/AI, 6 URL)

**Cheklov:** Bu dublikat **DB-only** (seed faylida — `app/content/services.py` — yo'q, ya'ni admin panel orqali production'da qo'shilgan). Men production DB matnini o'qiy olmayman — UZ matni audit'da so'zma-so'z keltirilgan (yuqori ishonch), RU/EN uchun ehtimoliy matn TAXMIN qilindi.

`service_faq_dedupe_v1_done` migratsiyasi — **ANIQ MATN MOS KELGANDAGINA** o'chiradi (hech narsa UYDIRILMAYDI/qo'shilmaydi):

| Xizmat | Til | O'chiriladigan savol | Ishonch |
|---|---|---|---|
| CRM | uz | "Mavjud CRM yoki boshqa tizimlarga integratsiya qilasizmi?" | Yuqori (audit'dan so'zma-so'z) |
| AI | uz | "AI chatbotni Telegram yoki saytga integratsiya qilasizmi?" | Yuqori (audit'dan so'zma-so'z) |
| CRM/AI | ru/en | bir nechta ehtimoliy variant (kodga qarang) | **Taxmin — production'da mos kelmasligi mumkin** |

| Metrika | BEFORE | AFTER |
|---|---|---|
| FAQ duplicate URL (UZ) | 2 (CRM, AI) | **0** (deploydan keyin) |
| FAQ duplicate URL (RU/EN) | 4 | ⚠️ Faqat matn mos kelsa tuzatiladi — **admin panelda qo'lda tekshirish tavsiya etiladi** agar migratsiya mos kelmasa |

**Manual tekshirish kerak:** Deploy'dan keyin `/ru/xizmatlar/crm/`, `/en/xizmatlar/crm/`, `/ru/xizmatlar/ai/`, `/en/xizmatlar/ai/` FAQ bo'limini ko'rib, agar hali ham integratsiya savoli ikki marta chiqsa — admin panel → Xizmatlar → tegishli tilni tahrirlab, dublikat savolni qo'lda o'chirish kerak (FAQ schema = faqat visible content, admin CRUD orqali boshqariladi, kod o'zgartirish shart emas).

---

## 4. P1 — HSTS

**Topilma:** Kod allaqachon to'g'ri (`app/security.py::SecurityHeadersMiddleware` — `settings.is_production and settings.HSTS_SECONDS > 0` bo'lsa `Strict-Transport-Security: max-age=31536000; includeSubDomains` qo'shadi, default `HSTS_SECONDS=31536000`). Production'da HSTS yo'qligi kod xatosi EMAS — `settings.is_production` `ENV=production` bo'lishini talab qiladi.

**ROOT CAUSE:** Production serverning `.env`ida `ENV` `production`ga o'rnatilmagan bo'lishi kerak (yoki umuman yo'q — default `development`). Bu FAQAT HSTS'ga emas, `settings.validate()` orqali boshqa production xavfsizlik tekshiruvlariga ham ta'sir qiladi (`JWT_SECRET`, `ADMIN_PASSWORD_HASH`, `CORS_ORIGINS`, SQLite/Postgres, `ENCRYPTION_KEY` — hammasi `is_production` bo'lganda qat'iy tekshiriladi).

**Taxmin qilinmadi, kodga workaround qo'shilmadi** — bu MANUAL DEPLOYMENT ACTION:
```
# production serverdagi .env faylida:
ENV=production
```
va servisni qayta ishga tushirish. `includeSubDomains` xavfsiz (www va apex bir xil TLS/sertifikatda — audit tasdiqlagan), `preload` QO'SHILMADI (preload ro'yxatiga topshirish qaytarib bo'lmaydigan qadam — TZ "taxmin qilma" talabiga ko'ra o'tkazib yuborildi).

| Metrika | BEFORE | AFTER |
|---|---|---|
| HSTS | Yo'q (kod tayyor, `ENV` noto'g'ri) | Kod: ✅ tayyor. Production: ⏳ `.env` da `ENV=production` qo'yilishi va restart kerak (MANUAL) |

---

## 5. P1 — WWW → APEX 301

Repo'da nginx/Caddy konfiguratsiyasi YO'Q (deployment repo tashqarisida boshqariladi) — shu sabab bu ilova darajasida (`app/main.py::WWWRedirectMiddleware`) implementatsiya qilindi: `www.<CANONICAL_HOST>` (GET/HEAD, istalgan scheme) → to'g'ridan-to'g'ri `https://<CANONICAL_HOST><path>?<query>` — **bitta hop**, zanjir yo'q. Boshqa metodlar (POST va h.k.) tegilmaydi (301 metodni saqlamasligi xavfi — real trafik www orqali faqat brauzer navigatsiyasi bo'ladi).

Test: `test_www_redirects_to_apex_https`, `test_www_redirect_preserves_query_string`, `test_non_www_host_not_redirected`. ✅ 3/3 PASS.

| Metrika | BEFORE | AFTER |
|---|---|---|
| `www.promtchi.uz/*` | 200 (mustaqil xizmat qiladi) | 301 → `https://promtchi.uz/*` (kod tayyor, ⏳ deploy kerak) |

---

## 6. P1 — CACHE-CONTROL

`app/security.py::SecurityHeadersMiddleware` kengaytirildi (route-by-route emas — bitta markazlashgan joy, 11+ handler'ga tegilmadi):

- `/api/admin/*`, `/api/auth/*`, `/admin` — o'zgarishsiz `no-store`.
- `/static/uploads/*` — `public, max-age=31536000, immutable` (fayl nomlari `secrets.token_hex(8)` bilan — bitta URL hech qachon boshqa kontentga almashmaydi, immutable XAVFSIZ).
- Qolgan `/static/*` (logo, css, admin.html — versiyalanmagan) — `public, max-age=86400, must-revalidate` (immutable EMAS — versiyalash yo'q).
- Boshqa barcha public GET (2xx, `/api/` va `/static/` bo'lmagan — ya'ni 81 ta ichki SEO sahifa) — `public, max-age=3600, must-revalidate` (bosh sahifada allaqachon ishlatilgan naqsh, `STATIC_CACHE_SECONDS` orqali sozlanadi).

Test: `test_public_page_gets_cache_control`, `test_faq_page_gets_cache_control`, `test_admin_api_not_publicly_cached`, `test_admin_html_not_publicly_cached`, `test_static_css_gets_long_cache`. ✅ 5/5 PASS.

| Metrika | BEFORE | AFTER (lokal tasdiqlangan) |
|---|---|---|
| Cache-Control yo'q sahifalar | 81/84 | **0/84** (kod tayyor, ⏳ production re-crawl kerak) |
| `/static/*` uzoq muddatli kesh | Yo'q | `logo.png`/`site.css` va h.k. — 1 kun; `/static/uploads/*` — 1 yil immutable |

---

## 7. LOGO OPTIMIZATION

`static/logo.png` (256×256, RGB, 7447 unique rang — gradient, palette-siqish vizual sifatni buzardi) **3 joyda ishlatiladi**: nav (`30×34px` ko'rinadi), favicon, OG/Organization schema image. Faqat nav uchun haqiqiy ehtiyoj bor (favicon/OG uchun yuqori piksel zichligi FOYDALI).

**Yechim:** `static/logo.webp` (92% sifat, lossless emas, lekin vizual jihatdan farqlanmaydi) qo'shildi — FAQAT nav `<img>` (4 joyda: `templates/base.html` + 3 ta statik bosh sahifa) `<picture><source type="image/webp">...<img ... .png></picture>`ga o'tkazildi. Favicon va OG/schema — PNG'da qoldi (keng qo'llab-quvvatlash, branding o'zgarmadi, vizual sifat buzilmadi).

| Metrika | BEFORE | AFTER |
|---|---|---|
| Nav logo (har sahifada yuklanadi) | 52 KB (PNG) | **6.1 KB** (WebP, ~88% kamaydi) |
| Favicon/OG image | 52 KB PNG | 52 KB PNG (o'zgarmadi — ataylab, moslik uchun) |

---

## 8. P2 — IMAGE OPTIMIZATION (umumiy)

Kod darajasida tekshirildi: `templates/blog_detail.html`, `templates/portfolio_detail.html` — `loading="lazy"`, `decoding="async"` ALLAQACHON qo'llanilgan. Bosh sahifadagi portfolio/blog/team/testimonial kartalari `background-image` + qattiq o'lchamli CSS konteyner orqali render qilinadi (`.pst-img`, `.mp`, `.tav`) — CLS xavfi past (konteyner o'lchami rasm yuklanishidan mustaqil).

**Qolgan bo'shliq (P2, amalga oshirilmadi):** Blog/portfolio detail hero rasmlarida aniq `width`/`height`/`aspect-ratio` yo'q (admin yuklagan rasm o'lchami DB'da saqlanmaydi) — to'g'ri tuzatish uchun yuklashda rasm o'lchamini DB'ga yozish kerak (schema o'zgarishi) — bu TZ doirasidan tashqari (over-engineering bo'lardi), tavsiya sifatida qoldirilmoqda. Admin-yuklangan rasmlar (`static/uploads/`) git-repo qismi emas (`.gitignore`) — production fayllarini bu sessiyadan siqib bo'lmaydi.

---

## 9. MOBILE / PERFORMANCE VERIFICATION

**HOLAT: TEKSHIRILMADI, SOXTA PASS BERILMAYDI.**

Sabab: bu sessiyada kod repo'sida ishlandi, production'ga HALI DEPLOY QILINMAGAN (bo'lim "DEPLOYMENT"ga qarang). Production'ni hozir qayta crawl qilish faqat ESKI (tuzatilmagan) holatni ko'rsatardi — bu oldingi audit hujjatlarida (`PRODUCTION_SEO_AUDIT.md`, `PRODUCTION_PERFORMANCE_AUDIT.md`) allaqachon batafsil hujjatlashtirilgan, qayta takrorlash yangi ma'lumot bermaydi va TZning "faqat real, yangi natija yoz" tamoyiliga zid bo'lardi.

Lokal darajada (kod to'g'riligi, FCP/LCP emas) tasdiqlangan: `TestClient` orqali barcha o'zgargan sahifalar 200/301 qaytaradi, header'lar to'g'ri (yuqoridagi testlar).

**Deploy'dan KEYIN qilinishi kerak** (bo'lim 19 talabi): Lighthouse/PageSpeed Insights (real, login talab qilmaydigan) + haqiqiy qurilma/DevTools device toolbar orqali 375/768/1440px.

---

## 10. INTERNAL LINKING / SCHEMA / SITEMAP / ROBOTS — LOKAL REVALIDATSIYA

TestClient orqali (to'liq app lifespan, real migratsiyalar ishlagan holda):

- `GET /sitemap.xml` → 200, valid XML, 32991 belgi (o'zgarish: eski 7 blog post `published=False` bo'lgach avtomatik chiqib ketadi — kod filtri o'zgarmadi, ma'lumot o'zgardi).
- `GET /robots.txt` → o'zgarmadi (`Allow: /`, `Disallow: /admin`, `Disallow: /api/admin/`, sitemap satri) — audit ham buni "to'g'ri" deb tasdiqlagan, tegilmadi.
- `GET /uz/xizmatlar/crm/` → canonical tag mavjud, 200.
- Organization JSON-LD (bosh sahifa) — `telephone`/`sameAs` endi to'g'ri (bo'lim 1).
- FAQPage schema — visible content bilan 1:1 (o'zgartirilmadi, faqat matn ichidagi eski Telegram almashtirildi — struktura teginilmadi).
- Orphan pages: eski blog postlar unpublish qilingach avtomatik ravishda "kam link oladigan sahifa" muammosi ham yo'qoladi (ular endi umuman public ro'yxatda emas, faqat 301 orqali topiladi — bu meros/tarixiy havolalar uchun to'g'ri xatti-harakat).

**Production re-crawl — ⏳ deploy'dan keyin qilinishi kerak** (yangi sonlar bilan, bu hujjatga qo'shimcha qilib emas, alohida keyingi audit sifatida — soxta raqam yozilmaydi).

---

## 11. TESTING

```
python -m pytest -q
35 passed (23 mavjud + 12 yangi), 0 failed
```

Yangi testlar (`tests/test_production_seo_fixes.py`): www→apex redirect (3), Cache-Control (5), bosh sahifa live-contact injection (1), DEFAULT_CONTENT seed to'g'riligi (1), contact-accuracy migratsiyasi (1), blog cannibalization migratsiyasi (1).

---

## 12. DEPLOYMENT

Repo'da CI/CD, Dockerfile yoki nginx konfiguratsiyasi YO'Q — `README.md`ga ko'ra production systemd/uvicorn + tashqi nginx/Caddy orqali qo'lda boshqariladi, bu sessiyadan production serverga SSH/deploy huquqi YO'Q.

**BAJARILGAN:** Barcha kod o'zgarishlari repo'da tayyor, test qilingan, commit qilishga tayyor.

**QOLGAN MANUAL QADAMLAR (production egasi bajarishi kerak):**
1. `git push` (agar so'ralsa — bu sessiyada avtomatik bajarilmadi, tasdiq kerak).
2. Production serverda: `git pull`, `pip install -r requirements.txt` (o'zgarish yo'q, lekin xavfsizlik uchun), servisni **restart** qilish — restart paytida `run_data_fixups()` avtomatik ishlaydi va production DB'dagi eski kontakt/FAQ/blog ma'lumotlarini bir martalik tuzatadi (bo'lim 1.3, 2, 3).
3. Production `.env` faylida `ENV=production` borligini tasdiqlash/qo'shish (bo'lim 4 — HSTS va boshqa xavfsizlik tekshiruvlari uchun MAJBURIY).
4. `www.promtchi.uz` uchun DNS/sertifikat www subdomeni uchun ham ishlashini tasdiqlash (301 ilova darajasida ishlaydi, lekin TLS handshake www uchun avval muvaffaqiyatli bo'lishi kerak — audit buni allaqachon tasdiqlagan: "www va apex bir xil sertifikat").
5. Deploy'dan keyin: production re-crawl (sitemap, contact, redirect, HSTS header, Cache-Control header, mobile, Lighthouse) — yangi, alohida hujjat sifatida.

---

## 13. FINAL SUMMARY (kod darajasida, bu sessiyada tekshirilgan)

| Metrika | BEFORE | AFTER (repo) |
|---|---|---|
| Wrong phone occurrences (kod+seed) | 3 | **0** |
| Wrong Promtchi Telegram occurrences (kod+seed) | 12 | **0** |
| Homepage/static cache divergence (root cause) | Present | **Resolved** (DB-asoslangan, admin edit avtomatik propagatsiya qiladi) |
| Blog cannibalization juftliklari | 7 | **0** (migratsiya tayyor) |
| FAQ duplicate URL (UZ, yuqori ishonch) | 2 | **0** (migratsiya tayyor) |
| FAQ duplicate URL (RU/EN) | 4 | ⚠️ Taxminiy fix — qo'lda tasdiqlash tavsiya etiladi |
| HSTS (kod) | Yo'q emas — sozlash muammosi | Kod: ✅. Production: `.env` `ENV=production` kerak |
| www → apex | Yo'q | ✅ (ilova darajasida, bitta hop) |
| Cache-Control (81 sahifa) | Yo'q | ✅ (barcha public sahifa + /static/*) |
| Logo (nav) | 52 KB | 6.1 KB (WebP) |
| Testlar | 23 | 35 (0 failed) |
| Sitemap/robots/canonical/hreflang/schema | To'g'ri edi | O'zgarmadi (buzilmadi), faqat kontent to'g'irlandi |

**Hali ochiq / manual tekshirish kerak bo'lgan narsalar** (soxta "ALL GOOD" berilmaydi):
- Production deploy — manual (bo'lim 12).
- FAQ RU/EN dedup — taxminiy, admin panelda tasdiqlash tavsiya etiladi (bo'lim 3).
- HSTS production'da faol bo'lishi — `.env` tuzatilib restart qilingandan keyin tekshirilishi kerak.
- Mobile/Lighthouse real o'lchov — faqat deploy'dan KEYIN, yangi sessiya/hujjat sifatida.
- Blog/portfolio hero rasmlar uchun aniq width/height (CLS) — kichik P2, schema o'zgarishi talab qiladi, bu bosqichda amalga oshirilmadi (over-engineering bo'lardi).
