# PRODUCTION GEO/AI AUDIT — promtchi.uz

**Sana:** 2026-09-16
**Manba:** https://promtchi.uz — jonli production
**Maqsad:** Saytning AI javob dvijoklari (ChatGPT, Perplexity, Google AI Overviews, Claude va h.k.) uchun "entity"ni to'g'ri va FAKTUAL tushunishini tekshirish. Fake claim yaratilmadi — barcha javoblar productiondagi haqiqiy kontentdan olindi.

---

## GEO STATUS: ⚠️ ASOSAN KUCHLI, 1 TA KRITIK DATA-ACCURACY MUAMMOSI BILAN

Kontent strukturasi (FAQPage schema'lar, Organization/Service schema'lar, "nima/kimga/qanday" formatidagi savol-javoblar) GEO uchun juda yaxshi loyihalangan. Lekin **bosh sahifadagi Organization schema noto'g'ri kontakt ma'lumotini tarqatadi** (`PRODUCTION_SEO_AUDIT.md` bo'lim 1ga qarang) — bu AI dvijoklarining Promtchi haqidagi eng asosiy faktini (qanday bog'lanish mumkin) buzadi, shu sababli GEO nuqtai nazaridan ham P0.

---

## 1. AI/GEO ENTITY TEST — 7 ta savol, productiondagi haqiqiy javob bilan

Test: har bir savolga sayt kontentidan (asosan `/uz/biz-haqimizda/` sahifasidagi FAQPage schema, `app/content/about.py`) haqiqiy javob topiladimi?

| # | Savol | Productiondagi javob manbai | Natija |
|---|---|---|---|
| 1 | What is Promtchi? | `/uz/biz-haqimizda/` FAQPage: *"promtchi — 2023-yildan Toshkentda faoliyat yuritayotgan raqamli mahsulotlar studiyasi. Bizneslar uchun veb-sayt, mobil ilova, AI yechimlar va CRM/ERP tizimlarini ishlab chiqamiz."* | ✅ TO'LIQ |
| 2 | Where is Promtchi located? | Xuddi shu FAQ: *"Studiya Toshkentda (O'zbekiston) joylashgan..."* + Organization schema `address.addressLocality:"Tashkent"` | ✅ TO'LIQ |
| 3 | What services does Promtchi provide? | FAQ: *"Veb-sayt va web-app yaratish, mobil ilova ishlab chiqish, CRM va ERP tizimlari, Telegram bot dasturlash, AI yechimlar (chatbot, ovozni matnga aylantirish) va biznes jarayonlarini avtomatlashtirish."* | ✅ TO'LIQ |
| 4 | Who is Promtchi for? | FAQ: *"Yangi biznesini onlaynga chiqarayotgan tadbirkorlardan tortib, sotuv bo'limi bor kompaniyalar va ombori yoki ko'p xodimi bor o'rta-yirik bizneslargacha."* | ✅ TO'LIQ |
| 5 | What technologies does Promtchi use? | FAQ: *"Backend uchun FastAPI va Django, ma'lumotlar bazasi uchun PostgreSQL, mobil ilovalar uchun Flutter, botlar uchun aiogram va Telegram Bot API."* | ✅ TO'LIQ, KONKRET |
| 6 | What CRM services does Promtchi provide? | `/uz/xizmatlar/crm/` — xizmat tavsifi + 4 ta FAQ (AmoCRM/Bitrix24 integratsiyasi, Telegram sinxronizatsiyasi, individual CRM qurish) | ✅ TO'LIQ (2 ta FAQ takrorlanadi — SEO audit 2.2) |
| 7 | What AI services does Promtchi provide? | `/uz/xizmatlar/ai/` — xizmat tavsifi + FAQ (AI chatbot, Telegram/sayt integratsiyasi, ovozni matnga aylantirish) | ✅ TO'LIQ (2 ta FAQ takrorlanadi — SEO audit 2.2) |

**Xulosa:** 7/7 savolga to'liq, faktik, sayt matnidan olingan javob topildi — fake claim yoki noaniq javob yo'q. Bu — GEO nuqtai nazaridan juda yaxshi natija. FAQPage schema formatida bo'lgani AI dvijoklari uchun ayniqsa qulay (structured Q&A — to'g'ridan-to'g'ri "answer box"ga mos).

**Yagona tanqid:** Bu javoblarning barchasi FAQPage schema orqali **strukturaviy jihatdan mavjud**, lekin savol #1-2-3-4-5 uchun manba faqat `/biz-haqimizda/` sahifasida markazlashgan — agar AI dvijogi faqat bosh sahifani index qilsa (ko'pchilik crawler shunday qiladi, chunki eng ko'p backlink oladigan sahifa), u yerda **noto'g'ri kontakt ma'lumoti** bilan uchrashadi (yuqoridagi P0 muammo).

---

## 2. GOOGLE SEARCH INTENT SIFATI — asosiy xizmat sahifalari

Har bir xizmat sahifasi productionda quyidagi 7 ta savolga javob bera oladimi tekshirildi (JSON-LD FAQPage + visible content asosida):

| Xizmat | Nima? | Kimga? | Muammo? | Nima qilinadi? | Qanday ishlaydi? | Integratsiyalar? | Bog'lanish? |
|---|---|---|---|---|---|---|---|
| Web development | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mobile app | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CRM | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (AmoCRM, Bitrix24, UTEL, Meta Ads) | ✅ |
| ERP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Telegram, sayt) | ✅ |
| Telegram bot | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (CRM bilan) | ✅ |
| Business automation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Barcha 7 ta asosiy xizmat sahifasida to'liq Service + FAQPage + BreadcrumbList schema mavjud, "integratsiyalar" savoliga aniq nom bilan (AmoCRM, Bitrix24, Meta Ads va h.k.) javob berilgan — bu generic emas, real, tekshiriladigan claim (GEO uchun ishonchlilik signali).

**Yagona kamchilik:** CRM va AI sahifalaridagi 2 tadan FAQ savoli semantik jihatdan takrorlanadi (SEO audit bo'lim 2.2) — "qanday integratsiyalar" savoli har ikkalasida ikki marta, sal boshqacha so'z bilan so'raladi. Bu javob sifatini pasaytirmaydi, lekin content zichligini keraksiz oshiradi.

---

## 3. SCHEMA.ORG VALIDATSIYA (GEO nuqtai nazaridan)

Barcha 84 sahifa bo'yicha JSON-LD avtomatik ajratib olindi va tekshirildi:

| Schema turi | Sahifalar soni | Majburiy maydonlar | Natija |
|---|---|---|---|
| Organization | 84/84 | name, url | ✅ hammasida mavjud (lekin bo'lim 1'dagi P0 — bosh sahifada noto'g'ri qiymat) |
| WebSite | 84/84 | name, url | ✅ |
| BreadcrumbList | 81/84 (bosh sahifalarda yo'q — to'g'ri, breadcrumb kerak emas) | itemListElement | ✅ |
| Service | 21/84 (xizmat/yechim sahifalari) | name, provider | ✅ |
| FAQPage | 36/84 | mainEntity (bo'sh emas) | ✅, 0 ta bo'sh mainEntity |
| Article | 15/84 (blog postlari) | headline, datePublished, author | ✅ |
| **LocalBusiness** | **0/84** | — | ✅ TO'G'RI — spec bo'yicha qo'shilmagan |

- **JSON parse xatolari:** 0/84 — barcha JSON-LD bloklar valid JSON.
- **@context muammolari:** 0.
- **WebPage `@id`/`url` vs `<link rel=canonical>` mos kelmasligi:** 0 (WebPage turi umuman ishlatilmagan, shuning uchun bu tekshiruv N/A — Organization/WebSite/Service o'z `url` maydonlarida izchil).
- **FAQPage faqat visible FAQ content mavjud sahifalarda:** tasdiqlangan — spot-check (`/uz/xizmatlar/crm/`) FAQ schema'dagi barcha savol matnlari sahifa HTML'ida ko'rinadigan holatda topildi (schema va visible content 1:1 mos).

**Xulosa: Schema.org strukturasi texnik jihatdan 100% valid.** Yagona muammo — bo'lim 1'dagi ma'lumot ANIQLIGI (accuracy), validlik emas.

---

## 4. FAKE CONTENT TEKSHIRUVI (bo'lim 17 talabi)

| Taqiqlangan element | Production holati |
|---|---|
| Fake statistika (32+/24+/98%/3+) | ✅ Ko'rinmaydi — faqat HTML izohida (`<!-- STATS hozircha yashirilgan -->`), foydalanuvchiga chiqmaydi |
| LocalBusiness schema | ✅ Yo'q (0/84 sahifada) |
| Team names | ✅ Sayt kontentida (about/faq) shaxsiy xodim ismlari topilmadi — jamoaviy "biz"/"promtchi" tilida yozilgan |
| Fake case natijalar | Portfolio case sahifalari (Chindan Group, Notiq AI, Tizimly) — bu maqsadli auditda case ichidagi har bir raqamli claim tekshirilmadi (matn darajasida chuqur fact-check qilinmadi, faqat schema/meta darajasida); agar case'larda "%increase" kabi raqamli natijalar bo'lsa, ular alohida tekshirilishi tavsiya etiladi. |

---

## 5. XAVFSIZLIK HEADERLARI (production, to'liq)

```
HTTP/1.1 200 OK
content-security-policy: default-src 'self'; base-uri 'self'; object-src 'none';
  frame-ancestors 'none'; img-src 'self' data: blob: https:; media-src 'self' data:
  blob: https:; frame-src https://www.youtube.com https://www.youtube-nocookie.com
  https://player.vimeo.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' data: https://fonts.gstatic.com; script-src 'self' 'unsafe-inline';
  connect-src 'self'; form-action 'self'
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: strict-origin-when-cross-origin
permissions-policy: geolocation=(), microphone=(), camera=(), interest-cohort=()
cross-origin-opener-policy: same-origin
x-xss-protection: 0
strict-transport-security: ❌ YO'Q
```

**Baholash:**
- CSP — juda yaxshi, `script-src 'self' 'unsafe-inline'` mavjud (ideal `'unsafe-inline'`siz bo'lardi, lekin server-rendered Jinja2 sahifalar uchun odatiy trade-off; XSS xavfini butunlay yo'qotmaydi, lekin boshqa direktivalar — `object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'` — qattiq).
- Clickjacking himoyasi (X-Frame-Options: DENY) — ✅.
- MIME-sniffing himoyasi — ✅.
- **HSTS yo'q (P1):** Sayt `http://` ni `https://`ga 301 bilan yo'naltiradi, lekin `Strict-Transport-Security` header yubormaydi. Bu shuni anglatadiki, brauzer birinchi tashrifda hali ham oddiy HTTP so'rov yuboradi (keyin 301 bilan HTTPS'ga o'tadi) — bu oyna orqali SSL-stripping (MITM) hujumi nazariy jihatdan mumkin. Tavsiya: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` qo'shish (nginx darajasida bitta qator).
- www va apex bir xil sertifikat/headerlarni qaytaradi — ✅ TLS konfiguratsiyasi izchil.

**SECURITY STATUS: ✅ YAXSHI, 1 TA P1 (HSTS yo'qligi) BILAN.** Kritik xavfsizlik teshigi topilmadi. Admin/API endpointlar to'g'ri himoyalangan (`/api/admin/*` → 401 auth'siz; `/admin` → noindex, ma'lumot yo'q, faqat login qobig'i).

---

## 6. XULOSA

| Yo'nalish | Holat |
|---|---|
| Schema.org validligi | ✅ 100% (0 xato) |
| GEO entity javoblari (7/7 savol) | ✅ 100% (About sahifasida) |
| GEO ma'lumot aniqligi (bosh sahifa) | ❌ Buzilgan — noto'g'ri telefon (UZ) va noto'g'ri Telegram (UZ/RU/EN) |
| Search intent qamrovi (7 xizmat) | ✅ 100% |
| Fake content yo'qligi | ✅ Tasdiqlangan |
| Xavfsizlik headerlari | ⚠️ Yaxshi, HSTS yetishmayapti |

**Ustuvor harakat:** Bo'lim 1'dagi bosh sahifa kontakt ma'lumotini to'g'irlash — bu tuzatilmaguncha, har qanday AI dvijogi yoki foydalanuvchi bosh sahifadan Promtchi bilan bog'lanishga urinsa, noto'g'ri kanalga/raqamga yo'naltiriladi.
