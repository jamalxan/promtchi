# SEO_AUDIT.md — promtchi.uz avtomatlashtirilgan crawl audit

**Sana:** 2026-09-16
**Usul:** Production (`https://promtchi.uz`) `sitemap.xml`dagi barcha 77 ta indexable URL avtomatik skript bilan crawl qilindi (`GET` so'rovlar, real Chrome orqali qo'shimcha tekshiruv). Har bir URL uchun: HTTP status, `<title>`, meta description, canonical, hreflang, H1 soni, JSON-LD schema turlari, OG/Twitter teglar, `<img alt>` mavjudligi tekshirildi.

## 1. Umumiy natija

| Ko'rsatkich | Natija |
|---|---|
| Sitemap status | 200 |
| Robots.txt status | 200 |
| Jami tekshirilgan URL | 77 / 77 |
| 200 qaytargan URL | **77 / 77** ✅ |
| Noyob `<title>`ga ega sahifalar | 77 / 77 ✅ |
| Noyob meta description'ga ega sahifalar | 77 / 77 ✅ |
| Canonical mavjud va o'ziga mos | 77 / 77 ✅ |
| Aynan bitta `<h1>` | 77 / 77 ✅ (0 ta multi-H1, 0 ta H1-siz) |
| `<img>` alt matnisiz | 0 ta ✅ |
| Twitter card to'liq (title+desc+image) | 77 / 77 ✅ |
| JSON-LD schema mavjud | 77 / 77 ✅ |

**Sahifalar bo'yicha taqsimot** (sitemap'dagi 77 URL):

| Bo'lim | URL soni |
|---|---|
| Bosh sahifa (uz/ru/en) | 3 |
| Xizmatlar (index + 7 xizmat × 3 til) | 24 |
| Yechimlar (index + 3 yechim × 3 til) | 12 |
| Portfolio (index + 3 case × 3 til) | 12 |
| Blog (index + 8 maqola) | 11 |
| FAQ | 3 |
| Biz haqimizda | 3 |
| Aloqa | 3 |
| Maxfiylik siyosati / Foydalanish shartlari (har biri 3 tilda, sluglar lokalizatsiya qilingan) | 6 |

## 2. Hreflang

- 69 sahifada to'liq 4 ta hreflang (`uz-UZ`, `ru-RU`, `en`, `x-default`) — **to'g'ri**.
- 8 ta blog maqolasida faqat 2 ta (o'z tili + `x-default` agar uz bo'lsa) — bu **XATO EMAS, ATAYLAB SHUNDAY**: har bir maqola bitta tilga tegishli mustaqil kontent, tarjimasi yo'q, shuning uchun mavjud bo'lmagan "tarjima"ga yolg'on hreflang berilmaydi (TZ 9-bo'lim: "Tarjima qilinmagan sahifa boshqa til sifatida ko'rsatilmasin").

## 3. Xavfsizlik headerlari (production, `curl -I` orqali tekshirildi)

```
content-security-policy: default-src 'self'; base-uri 'self'; object-src 'none'; ...
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: strict-origin-when-cross-origin
permissions-policy: geolocation=(), microphone=(), camera=(), interest-cohort=()
cross-origin-opener-policy: same-origin
x-xss-protection: 0
```
Barchasi mavjud va to'g'ri sozlangan. `/api/content` javobida `ETag` + `Cache-Control: public, max-age=60, stale-while-revalidate=300` + gzip compression ishlayapti.

## 4. Topilgan va TUZATILGAN muammolar (shu audit davomida)

| # | Muammo | Qayerda | Holat |
|---|---|---|---|
| 1 | Bosh sahifadagi qisqa FAQ bo'limi **bo'sh** edi (production'da haqiqiy xato — oldingi deploy FAQ jadvalidagi yangi `show_on_home` ustunini eski qatorlarga tarqata olmagan edi) | `/api/content?lang=*` | ✅ Tuzatildi (`app/db.py` bir martalik backfill) va production'da tasdiqlandi |
| 2 | Bosh sahifadagi Organization JSON-LD schema eskirgan/haqiqiy bo'lmagan telefon+email bilan qattiq yozilgan edi | `static/index*.html` | ✅ Tuzatildi (avvalgi sessiyada) — endi jonli kontaktlar bilan sinxron, production'da tasdiqlandi |
| 3 | Twitter/X card to'liq emas edi (faqat `twitter:card`, `title`/`description`/`image` yo'q) | Barcha sahifalar | ✅ Tuzatildi (avvalgi sessiyada), production'da tasdiqlandi |
| 4 | 6 ta xizmat sahifasining `<title>`si 67–74 belgi (Google SERP'da kesilib qolishi mumkin) | `/ru/xizmatlar/razrabotka-saitov/`, `/en/xizmatlar/web-development/`, `/ru/xizmatlar/ai/`, `/uz\|ru\|en/xizmatlar/avtomatlashtirish\|avtomatizatsiya-biznesa\|business-process-automation/` | ✅ Tuzatildi, ~47-60 belgigacha qisqartirildi |
| 5 | FAQ CMS'da savollar biror xizmat/kategoriyaga bog'lanmagan, bosh sahifada ko'rsatish belgisi yo'q edi | Admin panel / FaqItem | ✅ Tuzatildi (avvalgi sessiyada) — endi har savol kategoriya+xizmatga bog'lanadi, xizmat sahifasida ham ko'rinadi |
| 6 | Portfolio case'larda industry/goal/features/integrations/process maydonlari yo'q edi | PortfolioCase | ✅ Maydonlar qo'shildi (avvalgi sessiyada), hozircha bo'sh (uydirilmagan) |
| 7 | Tasdiqlanmagan statistika (32+/24+/98%/3+) bosh sahifada ko'rinardi | `static/index*.html` | ✅ Yashirildi (`hidden`, kod saqlangan) — foydalanuvchi bilan kelishilgan qaror |

## 5. Tekshirilib, MUAMMO TOPILMAGAN joylar

- Barcha 24 asosiy route (uz/ru/en) — console xatosiz, network xatosiz (Chrome orqali tekshirildi).
- Til almashtirgich joriy sahifani saqlaydi (masalan `/uz/xizmatlar/crm/` → RU tugmasi `/ru/xizmatlar/crm/`ga olib boradi — tekshirildi).
- 404 sahifa haqiqiy 404 status bilan qaytadi, "Bosh sahifaga" tugmasi bor.
- `/uz/jamoa/` → `/uz/biz-haqimizda/`ga 301 redirect ishlayapti.
- `robots.txt` faqat `/admin` va `/api/admin/`ni bloklaydi, muhim sahifalar ochiq.
- Multi-H1 yoki H1-siz sahifa yo'q.
- `<img>` teglarning barchasida `alt` matni bor.

## 6. Chrome orqali tekshirib bo'lmagan / tashqi vosita talab qiladigan narsalar

- Mobil viewport'da real render (bu sessiyada `resize_window` vositasi haqiqiy viewport'ni o'zgartirmadi — muhit cheklovi, CSS kod darajasida mobile-first ekanligi allaqachon tasdiqlangan).
- Google Rich Results Test / Schema.org Validator orqali rasmiy tasdiqlash (tashqi xizmat, bu muhitda ishlatib bo'lmadi).
- Real Lighthouse/PageSpeed Insights o'lchovi (Core Web Vitals raqamlari) — headerlar va resurs hajmlari orqali proksi baholash qilindi (gzip, kesh, WOFF2 fontlar — barchasi joyida), lekin real LCP/INP/CLS raqami yo'q.
- Contact formani REAL submit qilib test qilish — bu ataylab QILINMADI, chunki bu haqiqiy Telegram xabarnoma yuboradi va CRM'ga real (soxta) ariza qo'shadi. Forma logikasi (validatsiya, honeypot, rate-limit) avvalgi sessiyalarda izolyatsiyalangan test nusxasida to'liq tekshirilgan.
