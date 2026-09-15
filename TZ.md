# PROMTCHI.UZ — MUKAMMAL TEXNIK TOPSHIRIQ (TZ)

Web-sayt • SEO • GEO/AI • 3 til • Kontent • CRM/ERP • Ishonch • Performance • Analytics

Versiya: 2.0 | Sana: 15.09.2026

## 1. Loyiha maqsadi

Promtchi.uz — Toshkentdagi IT/digital mahsulotlar studiyasi sifatida web, mobil, CRM/ERP, AI, Telegram bot va biznes avtomatlashtirish xizmatlarini taqdim etadigan zamonaviy, ishonchli va qidiruv tizimlari hamda AI tizimlari tomonidan oson tushuniladigan sayt bo'lishi kerak.

Asosiy maqsad: xizmatlarni tushunarli ko'rsatish va sifatli lead olish.

- Google/Yandex uchun texnik va semantik SEO'ni to'liq yo'lga qo'yish.
- AI/GEO uchun kompaniya, xizmatlar, mutaxassislik va real loyihalar haqidagi aniq faktlarni strukturalash.
- UZ/RU/EN tillarida alohida indexable URL'lar yaratish.
- Mobil qurilmalarda tez, qulay va accessibility talablariga mos ishlash.
- Kontentni admin panel orqali dasturchisiz yangilash imkonini berish.
- Portfolio, yangiliklar va FAQ orqali ekspertlik va ishonchni kuchaytirish.

## 2. Hozirgi sayt bo'yicha majburiy tuzatishlar

- Agar statistik ko'rsatkichlarda foydalanuvchiga 0 Loyiha, 0 Mijoz, 0 Qoniqish, 0 kun kabi placeholderlar ko'rinsa — ularni real ma'lumot bilan almashtirish yoki blokni vaqtincha yashirish. Soxta 0 ko'rsatkich qoldirilmasin.
- Hero'dagi "14 kun" va jarayon muddatlari bir-biriga zid bo'lmasin. 14 kun faqat real kafolatlanadigan MVP/loyihalarga nisbatan ishlatilsin.
- "0 KUN — MVP tayyor" va "0 KUN — To'liq loyiha" kabi placeholderlar olib tashlansin. Real diapazon yoki "loyiha hajmiga qarab" yozilsin.
- "qadriyat dir" kabi imlo xatosi "qadriyatdir"ga tuzatilsin.
- Jamoa bo'limi bo'sh holda qoldirilmasin. Real jamoa ma'lumoti bo'lsa ko'rsatiladi; bo'lmasa "Mutaxassislarimiz / Ekspertiza" blokiga aylantiriladi.
- FAQ javoblari buyurtmachidan olingandan keyin yakuniy joylashtiriladi; javoblar taxminan yozilmasin.
- "Kod huquqi to'liq mijozga tegishli" kabi qat'iy huquqiy da'volar shartnoma va uchinchi tomon litsenziyalariga mos professional matnga almashtirilsin.
- "3 oy bepul o'zgartirishlar" faqat barcha tegishli loyihalarda real majburiyat bo'lsa umumiy va'da sifatida qoldirilsin; aks holda loyiha/paket shartlariga bog'lansin.

## 3. Sayt arxitekturasi va URL

### 3.1. Til struktura

```
https://promtchi.uz/uz/
https://promtchi.uz/ru/
https://promtchi.uz/en/
```

Root / sahifa x-default yoki foydalanuvchi tilini aniqlaydigan xavfsiz yo'naltirish nuqtasi bo'lishi mumkin, lekin barcha asosiy kontent til papkalarida indexable bo'lishi kerak.

### 3.2. Tavsiya etiladigan route'lar

- `/uz/` `/ru/` `/en/` — bosh sahifa
- `/uz/xizmatlar/` `/ru/services/` `/en/services/` — xizmatlar katalogi
- `/uz/xizmatlar/web-sayt/` — web sayt
- `/uz/xizmatlar/web-ilova/` — web application
- `/uz/xizmatlar/mobil-ilova/` — mobil ilova
- `/uz/xizmatlar/crm/` — CRM
- `/uz/xizmatlar/erp/` — ERP
- `/uz/xizmatlar/ai/` — AI yechimlar
- `/uz/xizmatlar/telegram-bot/` — Telegram bot
- `/uz/xizmatlar/avtomatlashtirish/` — biznes avtomatlashtirish
- `/uz/portfolio/` — portfolio
- `/uz/portfolio/{slug}/` — alohida case study
- `/uz/yangiliklar/` — blog/news katalogi
- `/uz/yangiliklar/{slug}/` — alohida maqola
- `/uz/biz-haqimizda/` — kompaniya haqida
- `/uz/jamoa/` — jamoa (real profillar mavjud bo'lsa)
- `/uz/faq/` — FAQ
- `/uz/aloqa/` — kontakt

Muhim: SEO qiymatiga ega kontent faqat #anchor ichida yashirilmasin. Anchorlar UX uchun ishlatiladi; asosiy xizmat va maqolalar alohida indexable URL'larda bo'lsin.

### 3.3. Til almashtirish

Til switcher foydalanuvchini aynan shu kontentning boshqa tiliga olib o'tishi kerak. Masalan:

`/uz/xizmatlar/crm/` → `/ru/services/crm/` → `/en/services/crm/`

Agar tarjima mavjud bo'lmasa, avtomatik ravishda homepage'ga tashlashdan ko'ra tegishli tilning mos sahifasi yoki 404/alternativ yo'l belgilanadi.

Har bir indexable sahifa reciprocal hreflang bilan bog'lanadi.

URL'lar bir xil ma'nodagi kontentni ifodalashi kerak.

## 4. Homepage — aniq bloklar

### 4.1. Header

- Logo: Promtchi.
- Navigatsiya: Xizmatlar, Loyihalar, Yangiliklar, Biz haqimizda/Jamoa, FAQ, Aloqa.
- Til: UZ / RU / EN.
- Asosiy CTA: "Loyiha haqida gaplashamiz" yoki "Konsultatsiya olish".
- Header mobil menyuda ham to'liq ishlashi kerak.

### 4.2. Hero

Tavsiya etiladigan mazmun:

```
H1: Biznesingizni bitta tizimda jonlantiramiz

MVP'dan to'liq mahsulotgacha — dizayn, ishlab chiqish,
avtomatlashtirish va AI yechimlarini yaratamiz.

CTA 1: Loyihani boshlash
CTA 2: Xizmatlarni ko'rish
```

"14 kun" ishlatilsa, u aniq shart bilan berilsin: masalan, "mos MVP loyihalarida 14 kungacha". Universal kafolat sifatida yozilmasin.

### 4.3. Xizmatlar

- Web va mobil dasturlash — Sayt, Web App, Mobil ilova.
- Biznes avtomatlashtirish — CRM, leadlar, to'lovlar, integratsiyalar.
- AI yechimlar — AI chatbot, AI integratsiya, STT, kontent va avtomatlashtirish.
- CRM / ERP tizimlar — Moliya, ombor, KPI, dashboard.

Har bir xizmat kartasi alohida SEO sahifasiga olib boradi.

### 4.4. Ishlash jarayoni

- 01 — Konsultatsiya / talablarni aniqlash
- 02 — UX/UI dizayn
- 03 — Ishlab chiqish
- 04 — Test & QA
- 05 — Ishga tushirish + qo'llab-quvvatlash

Muddatlar faqat real loyiha diapazonlari bilan ko'rsatiladi.

### 4.5. Portfolio

Har bir case: Muammo → Maqsad → Yechim → Funksiyalar → Texnologiyalar → Integratsiyalar → Natija. Natija raqam bilan berilsa, faqat tekshirilgan real raqam ishlatiladi.

### 4.6. Ishonch bloklari

- Real mijozlar/logotiplar — ruxsat mavjud bo'lsa.
- Real testimonial — ism, lavozim/kompaniya faqat ruxsat bilan.
- Real jamoa yoki ekspertiza.
- Kompaniya haqida aniq faktlar.
- Aloqa ma'lumotlari va Toshkent joylashuvi.

### 4.7. Yangiliklar

Homepage'da 3–6 ta so'nggi maqola ko'rsatiladi. "Barcha maqolalar" tugmasi /yangiliklar/ sahifasiga olib boradi.

- CRM va biznes avtomatlashtirish
- ERP va ichki tizimlar
- AI va chatbotlar
- Telegram botlar
- Web va mobil dasturlash
- MVP va startap
- SEO/GEO va raqamli mahsulotlar

### 4.8. FAQ

FAQ buyurtmachining real javoblari kelgach to'ldiriladi. Savol-javoblar homepage'da qisqa ko'rinishi va /faq/ sahifasida to'liq ko'rinishi mumkin.

### 4.9. Aloqa

- Loyiha turi select: Web sayt, Web App, Mobil ilova, CRM, ERP, Telegram bot, AI, Avtomatlashtirish, Boshqa.
- Ism.
- Telefon/Telegram/email.
- Loyiha tavsifi.
- Budjet (ixtiyoriy).
- CTA: "Konsultatsiya olish".

Yuborilgandan keyin muvaffaqiyatli holat va xatolik holati ko'rsatiladi.

## 5. Xizmat sahifalari uchun standart

Har bir xizmat alohida sahifa bo'lishi shart. Har bir sahifada boshqa sahifalardan ko'chirilmagan, o'ziga xos kontent bo'lsin.

- H1 — aniq xizmat nomi.
- 1–2 jumlalik qisqa answer-first ta'rif.
- Muammo: mijozda qanday muammo bor?
- Yechim: Promtchi nimani ishlab chiqadi?
- Asosiy funksiyalar.
- Kimlar uchun.
- Ishlash jarayoni.
- Integratsiyalar.
- Texnologiyalar — faqat real ishlatiladiganlari.
- Portfolio/case'lar.
- FAQ — shu xizmatga tegishli savollar.
- CTA.

### CRM sahifasi uchun minimum

- CRM nima?
- CRM kimga kerak?
- Lead va sales pipeline.
- Mijozlar bazasi.
- Menejerlar va vazifalar.
- KPI/dashboard.
- Telegram/website/payment integratsiyasi.
- Individual CRM va tayyor CRM farqi.
- Case study.
- CTA.

## 6. Yangiliklar/blog tizimi

### 6.1. Admin maydonlari

- Sarlavha
- Slug
- Rasm URL (ixtiyoriy)
- Qisqa tavsif/excerpt
- To'liq matn
- Kategoriya
- Teglar
- Til
- Muallif
- Yaratilgan sana
- Yangilangan sana
- SEO title
- SEO description
- Index/noindex
- Ko'rinishi (publish/draft)

Hozirgi oddiy forma kamida sarlavha + rasm URL + matn bilan ishlashi mumkin, lekin production darajasida yuqoridagi SEO maydonlari qo'shilishi kerak.

### 6.2. Maqola formati

- Sarlavha savol yoki aniq muammoni ifodalashi.
- Birinchi 2–3 gapda maqolaning qisqa javobi.
- H2/H3 bilan bo'limlash.
- Ro'yxatlar va qisqa paragraf.
- Kerak bo'lsa jadval.
- Tegishli xizmat sahifasiga internal link.
- Tegishli boshqa maqolalarga internal link.
- Oxirida tabiiy CTA.

## 7. SEO — On-page talablar

### 7.1. Har bir indexable sahifa

- Unique title.
- Unique meta description.
- Bitta asosiy H1.
- H2/H3 ierarxiyasi.
- Canonical URL.
- Index/follow holati.
- Open Graph title/description/image.
- Twitter/X card.
- Breadcrumb.
- Internal links.
- Image alt.
- Clean slug.

### 7.2. Keyword strategy

Asosiy klasterlar tabiiy ishlatiladi; kalit so'zlar majburan takrorlanmaydi.

- IT kompaniya / IT agentlik Toshkent
- sayt yaratish / web development
- mobil ilova yaratish
- CRM ishlab chiqish
- ERP tizim
- Telegram bot yaratish
- AI yechimlar / AI chatbot
- biznes avtomatlashtirish
- individual dasturiy ta'minot
- Toshkentdagi dasturlash kompaniyasi

UZ va RU keywordlari alohida semantik xarita bilan boshqariladi; EN sahifada o'zbek/rus kalit so'zlari majburan ishlatilmaydi.

## 8. Technical SEO

- robots.txt to'g'ri sozlansin.
- XML sitemap indexable sahifalarni qamrab olsin.
- 3 til sahifalari sitemap'da mavjud bo'lsin.
- Canonical har sahifada o'zining canonical URL'ini ko'rsatsin.
- 301 redirectlar noto'g'ri/eskirgan URL'lar uchun sozlansin.
- 404 sahifa foydalanuvchini yo'naltirsin va 200 qaytarmasin.
- Noindex faqat kerakli admin, filter, duplicate yoki texnik sahifalarga.
- Pagination/filter URL'lari duplicate kontent hosil qilmasin.
- JS orqali yaratiladigan asosiy SEO matnlar server-side/rendered holatda crawl qilinadigan bo'lsin.
- Favicon, manifest va Open Graph ishlasin.

## 9. Hreflang

Har bir til versiyasi reciprocal hreflang bilan beriladi.

```html
<link rel="alternate" hreflang="uz-UZ" href="https://promtchi.uz/uz/">
<link rel="alternate" hreflang="ru-RU" href="https://promtchi.uz/ru/">
<link rel="alternate" hreflang="en" href="https://promtchi.uz/en/">
<link rel="alternate" hreflang="x-default" href="https://promtchi.uz/uz/">
```

Aniq implementation saytning routing tizimiga mos ravishda qilinadi. Hreflang URL'lari 200 status qaytarishi va bir-birini qaytarib ko'rsatishi kerak.

## 10. Structured Data / Schema.org

- Organization — kompaniyaning nomi, URL, logo, email, telefon, social profillar.
- WebSite — sayt nomi va URL.
- WebPage — sahifa turi.
- Service — xizmat sahifalarida.
- BreadcrumbList — ichki sahifalarda.
- Article yoki BlogPosting — yangiliklarda.
- FAQPage — faqat sahifada haqiqiy ko'rinadigan savol-javob bo'lsa va amaldagi qidiruv tizimi talablari bilan mos bo'lsa.
- LocalBusiness — faqat Promtchi haqiqiy mahalliy biznes sifatida mos bo'lsa va ma'lumotlari aniq bo'lsa.

Schema ichidagi ma'lumotlar sahifada ko'rinadigan haqiqiy kontent bilan mos bo'lishi shart. Fake review, fake rating yoki mavjud bo'lmagan ma'lumot schema'ga qo'shilmaydi.

## 11. AI / GEO optimizatsiya

Maqsad — AI tizimlari Promtchi haqida mustaqil ravishda to'g'ri, qisqa va ishonchli xulosa chiqarishi uchun entity va expertise signalini kuchaytirish.

- Kompaniyaning yagona, izchil ta'rifi barcha tillarda mavjud bo'lsin.
- Promtchi kim? Nima qiladi? Qayerda ishlaydi? Kimlar uchun? — aniq javoblar bo'lsin.
- Xizmatlar alohida sahifalarda semantik jihatdan ajratilsin.
- Har bir xizmat: nima, kim uchun, qanday ishlaydi, qanday natija beradi — formatida tushuntirilsin.
- Real case study'lar problem/solution/result shaklida yozilsin.
- Real mutaxassislar va ularning rollari ko'rsatilishi mumkin.
- AI uchun qisqa answer-first bloklar yaratiladi.
- FAQ va explainer maqolalar savolga to'g'ridan-to'g'ri javob beradi.
- Kontent original tajriba va real loyiha faktlariga asoslanadi.
- AI crawlerlarni asossiz ravishda bloklaydigan robots qoidalari kiritilmasin; xavfsizlik va maxfiylik bundan mustasno.
- AI tomonidan oson parchalanadigan aniq heading, list, jadval va ta'riflar ishlatiladi.

## 12. Jamoa / About / Expertise

Jamoa bo'limi o'chirib yuborilmaydi, agar real jamoa mavjud va ularni ko'rsatishga rozilik bo'lsa.

- Ism-familiya.
- Lavozim.
- Mutaxassislik.
- 1–3 jumlalik professional bio.
- LinkedIn/GitHub kabi professional profil — mavjud bo'lsa.
- Portfolio yoki ishlagan yo'nalish — maxfiylikka zid bo'lmasa.

Agar jamoa profillari tayyor bo'lmasa, homepage'da "Bizning ekspertiza" blokini ko'rsatish va /biz-haqimizda/ sahifasida kompaniya haqida ma'lumot berish.

## 13. Portfolio / Case Study

Portfolio SEO/GEO va conversion uchun asosiy ishonch elementlaridan biri.

### Har bir case uchun

- Loyiha nomi.
- Mijoz/kompaniya nomi — ruxsat bo'lsa.
- Soha.
- Muammo.
- Maqsad.
- Yechim.
- Asosiy funksiyalar.
- Texnologiyalar.
- Integratsiyalar.
- Natija.
- Screenshots.
- CTA.

Natijalar uydirilmasin. "+35%", "2x" kabi raqamlar faqat real o'lchov bilan tasdiqlansa ishlatiladi.

## 14. Ishonch va yuridik matnlar

- Terms of Use / Foydalanish shartlari.
- Privacy Policy / Maxfiylik siyosati.
- Kontakt ma'lumotlari.
- Formalar uchun ma'lumotlardan foydalanish roziligi.
- Cookie/banner talab qilinadigan yurisdiksiyaga moslashtirish.
- Kod va intellectual property masalalari shartnomaga bog'langan holda yozilishi.
- Mijoz logotipi/testimonial ishlatish uchun ruxsat.

## 15. Performance / Core Web Vitals

- Mobile-first.
- LCP, INP, CLS ko'rsatkichlarini optimallashtirish.
- Rasmni WebP/AVIF formatga o'tkazish.
- Lazy loading — fold ostidagi rasmlar uchun.
- Hero image uchun keraksiz lazy loading ishlatilmasin.
- JS bundle va third-party scriptlar minimallashtirilsin.
- Fontlar optimallashtirilsin.
- Cache va compression sozlansin.
- Layout shiftga sabab bo'ladigan dimensionsiz image/video ishlatilmasin.

## 16. Accessibility / UX

- Keyboard navigation.
- Visible focus state.
- Form label'lari aniq.
- Button va linklar semantic HTML bilan.
- Rasm alt matni.
- Yetarli color contrast.
- Hover'ga bog'liq bo'lmagan mobil UX.
- Error va success holatlari tushunarli.
- H1-H2-H3 tartibi.
- Touch targetlar yetarli o'lchamda.

## 17. Analytics va conversion tracking

- Google Analytics 4 yoki tanlangan analitika.
- Google Search Console.
- Yandex Webmaster/Metric — kerak bo'lsa.
- Telegram CTA click.
- Email click.
- Telefon click.
- Contact form submit.
- Project type tanlovi.
- CTA click.
- Portfolio click.
- Service page → contact conversion.
- 404 event.

Tracking foydalanuvchi maxfiyligi va amaldagi qonuniy talablarga mos bo'lishi kerak.

## 18. Xavfsizlik

- HTTPS majburiy.
- Admin panel autentifikatsiyasi.
- Rate limiting / anti-spam.
- Form validation server-side.
- XSS/CSRF/SQL injection himoyasi.
- Upload bo'lsa MIME/type/size tekshiruvi.
- Secrets .env orqali.
- Admin route'lar search engine'dan yopiq.
- Backup va restore jarayoni.
- Dependency security audit.

## 19. Admin panel / CMS

- Sahifa yaratish/tahrirlash.
- 3 til kontentini boshqarish.
- Service CRUD.
- Portfolio CRUD.
- Yangilik CRUD.
- FAQ CRUD.
- Team CRUD.
- SEO title/description.
- OG image.
- Slug.
- Publish/draft.
- Canonical.
- Noindex.
- Image management.
- Order/sort.

## 20. SEO kontent xaritasi

| Sahifa | Asosiy intent | Asosiy mavzu | CTA |
|---|---|---|---|
| Home | Commercial | IT studio / digital products / Tashkent | Konsultatsiya |
| CRM | Commercial | CRM development / individual CRM | CRM buyurtma |
| ERP | Commercial | ERP development / automation | Konsultatsiya |
| Web | Commercial | Website / web app development | Loyiha boshlash |
| Mobile | Commercial | Mobile app development | Ilova buyurtma |
| AI | Commercial | AI solutions / chatbot / STT | AI konsultatsiya |
| Telegram bot | Commercial | Telegram bot development | Bot buyurtma |
| Automation | Commercial | Business automation | Jarayon tahlili |
| Portfolio | Trust | Real cases | Case → Aloqa |
| News | Informational | Expert content | Service → Aloqa |
| About | Trust | Company / expertise | Aloqa |

## 21. Kontent reja — birinchi 20 mavzu

1. CRM nima?
2. Biznesingizga CRM kerakligini ko'rsatuvchi 7 ta belgi
3. CRM va Excel: qaysi biri biznes uchun yaxshiroq?
4. ERP nima va CRM'dan qanday farq qiladi?
5. AI biznes jarayonlarini qanday avtomatlashtiradi?
6. Telegram bot biznesga nima beradi?
7. Biznes uchun mobil ilova qachon kerak?
8. Biznesni avtomatlashtirishni nimadan boshlash kerak?
9. Individual CRM yoki tayyor CRM?
10. CRM joriy qilishda 5 ta xato
11. Leadlarni yo'qotmaslik uchun CRM
12. CRM + Telegram integratsiyasi
13. AI chatbot va oddiy chatbot farqi
14. Web-ilova nima?
15. Landing Page va korporativ sayt farqi
16. Sayt yaratishda 7 ta xato
17. MVP nima?
18. MVP va to'liq mahsulot farqi
19. ERP qachon kerak?
20. Ombor va moliyani avtomatlashtirish

## 22. Copywriting talablari

- Asosiy til: tabiiy o'zbek tili.
- Marketing matni bo'lsa ham faktlar oshirib yuborilmasin.
- "Eng yaxshi", "100%", "№1" kabi isbotsiz da'volardan foydalanilmasin.
- Texnik atamalar birinchi marta kelganda izohlanadi.
- Paragraflar qisqa.
- H1/H2/H3 semantik tartibda.
- CTA aniq va harakatga undovchi.
- Bir xil matn 3 tilda avtomatik tarjima qilib qo'yilmasin; professional lokalizatsiya qilinsin.

## 23. 404, redirect va indeks nazorati

- 404 sahifada foydali navigatsiya bo'lsin.
- Eski URL → yangi URL 301.
- HTTP → HTTPS 301.
- Duplicate URL variantlari canonical/redirect bilan birlashtiriladi.
- Trailing slash siyosati yagona bo'lsin.
- www/non-www yagona variantga keltirilsin.
- HTTP statuslar audit qilinsin.

## 24. QA — topshirishdan oldingi test

- Desktop Chrome/Edge/Firefox/Safari.
- Android va iOS.
- 3 tilning barcha asosiy route'lari.
- Til switcher current page'ni saqlashi.
- Barcha CTA va anchorlar ishlashi.
- Contact form valid/invalid holatlari.
- Admin CRUD.
- Sitemap.
- Robots.
- Canonical.
- Hreflang.
- Schema validation.
- Open Graph preview.
- 404/301.
- Mobile responsive.
- Core Web Vitals.
- Accessibility.
- Analytics events.
- Security headers.
- No placeholder 0/bo'sh bloklar.

## 25. Qabul qilish mezonlari (Acceptance Criteria)

- Sayt 3 tilda to'liq navigatsiya qilinadi.
- Har bir asosiy xizmat alohida indexable sahifaga ega.
- Har bir indexable sahifada unique title, description, H1 va canonical mavjud.
- Hreflang reciprocal va valid.
- Sitemap va robots ishlab turadi.
- Portfolio case'lari real ma'lumot bilan to'ldirilgan.
- Jamoa bo'limida faqat real shaxslar yoki ekspertiza bloki mavjud.
- Yangiliklar admin orqali yaratiladi va alohida URL'ga ega.
- FAQ buyurtmachi tasdiqlagan javoblar bilan joylashtiriladi.
- Hech qanday ko'rinadigan placeholder 0 yoki lorem ipsum qolmaydi.
- 14 kunlik va boshqa xizmat va'dalari real shartlarga mos.
- Formalar ishlaydi va spamdan himoyalangan.
- Mobil UX xatosiz.
- Muhim kontent search engine crawl qilishi mumkin.
- Fake schema, fake review, fake statistic mavjud emas.

## 26. Ishni bajarish ketma-ketligi

1. Audit va mavjud kod/DB arxitekturasini tekshirish.
2. URL va 3 til routing arxitekturasini yakunlash.
3. Homepage UX va kontentini tuzatish.
4. Xizmatlar uchun alohida sahifalarni yaratish.
5. Portfolio/case study tizimini yaratish.
6. Yangiliklar tizimini SEO fieldlar bilan kuchaytirish.
7. Jamoa/About/Expertise blokini to'g'rilash.
8. FAQ javoblari kelgach joylashtirish.
9. SEO meta/canonical/hreflang/sitemap/robots.
10. Schema.org.
11. Performance va accessibility.
12. Analytics va conversion tracking.
13. Security audit.
14. Mobile/desktop QA.
15. Production release.
16. Google Search Console va Yandex/Webmaster monitoring.

## 27. Dasturchiga qat'iy eslatmalar

- SEO uchun matnni CSS display:none bilan yashirish mumkin emas.
- Faqat anchor orqali barcha xizmatlarni bitta sahifada qoldirish yetarli emas — muhim xizmatlar alohida URL bo'lsin.
- Hreflang faqat mavjud va 200 qaytaradigan sahifalarga berilsin.
- Schema sahifadagi real kontentga mos bo'lsin.
- Fake review, fake client, fake statistic, fake project va fake team member ishlatilmasin.
- 14 kun, 3 oy bepul support kabi da'volar faqat biznes tomonidan tasdiqlanganda production'da qolsin.
- Admin paneldagi SEO fieldlar required/optional holatlari aniq belgilanadi.
- Slugs o'zgarsa 301 redirect yaratiladi.
- Maqola o'chirilsa 404 yoki mos maqolaga 301 siyosati bo'lsin.
- Sahifa title'lari bir-biridan farq qilsin.
- Image alt keyword stuffing qilinmasin.
- Core Web Vitals'ni buzadigan animatsiyalar kamaytirilsin.

## 28. Yakuniy kutilayotgan natija

Natijada Promtchi.uz oddiy vizitka sayt emas, balki xizmatlar, portfolio, ekspert kontent, real jamoa, FAQ va aloqa kanallarini birlashtirgan to'liq digital product studio platformasiga aylanishi kerak.

- Google/Yandex uchun texnik jihatdan toza.
- AI/GEO uchun tushunarli entity va expertise tuzilmasiga ega.
- 3 tilda indexable.
- Mijozga xizmatni 10–20 soniyada tushuntira oladigan.
- Real portfolio va real ishonch signallariga ega.
- Maqolalar orqali organik trafik yig'ishga tayyor.
- CRM/ERP/AI/Web/Mobile xizmatlarini alohida landinglar orqali sotishga tayyor.
- Tez, mobil-first va accessibility talablariga mos.
- Admin panel orqali kengaytiriladigan.
- O'lchanadigan conversion funnel'ga ega.

## 29. Biznes tomonidan alohida tasdiqlanishi kerak bo'lgan ma'lumotlar

- Haqiqiy loyiha soni.
- Haqiqiy mijoz soni.
- Haqiqiy jamoa a'zolari va rollari.
- 14 kunlik va'da qaysi loyiha turlariga tegishli.
- Support/kafolat shartlari.
- Kod/IP huquqlari bo'yicha standart shartnoma.
- Mijoz logotiplarini ko'rsatish ruxsati.
- Testimonials.
- Real case study natijalari.
- Rasmiy telefon, email, Telegram va boshqa aloqa kanallari.

## 30. Yakuniy prinsip

Promtchi.uz'da SEO alohida "kalit so'z qo'shish" vazifasi sifatida emas, balki sayt arxitekturasi + foydalanuvchi tajribasi + real ekspertlik + texnik sifat + original kontent + conversion tizimi sifatida amalga oshiriladi. AI/GEO ham SEO'ning o'rnini bosmaydi; u kompaniya haqidagi faktlarni AI tizimlariga tushunarli, izchil va ishonchli ko'rsatish qatlamidir.

---

PROMTCHI.UZ — SEO / GEO / Technical TZ v2.0

---

## Amalga oshirish holati (progress log — shu fayl bilan birga yangilab boriladi)

**2026-09-15/16 kuni bajarildi:**
1. **Maxfiylik siyosati + Foydalanish shartlari** — 3 tilda, `/{lang}/maxfiylik-siyosati/` va boshqa tillardagi mos slug'lar bilan. `app/content/legal.py`, `templates/legal.html`.
2. **GA4 analitika** — `GA_MEASUREMENT_ID` env orqali yoqiladi (bo'sh bo'lsa hech narsa in'ektsiya qilinmaydi). Hodisalar: `phone_click`, `email_click`, `telegram_click`, `cta_click`, `portfolio_click`, `select_project_type`, `generate_lead`, `page_not_found`. `static/analytics.js`, `app/main.py` (`_inject_ga`), `templates/base.html`.

**2026-09-16 kuni bajarildi:**
4. **Services/Portfolio — to'liq DB CRUD'ga o'tkazildi** (TZ 4/19-bo'lim; foydalanuvchi bilan kelishilgan qaror — "to'liq DB CRUD" tanlandi). Tafsilotlar:
   - `app/db.py`: yangi `Service`, `PortfolioCase` (har biri — key, order, published, slug_uz/ru/en, data_uz/ru/en JSON) va `SlugRedirect` (301 uchun) jadvallari.
   - `app/services_store.py` (yangi): xotira keshi + `seed_if_empty()` — `app/content/services.py`/`portfolio.py`dagi haqiqiy 7 xizmat va 3 case'ni bir martalik DB'ga ko'chiradi. Bu ikki Python fayl endi RUNTIME'da O'QILMAYDI — faqat seed manbai (docstringlarda belgilandi).
   - `app/main.py`: `GET/POST/PUT/DELETE /api/admin/services[/{id}]` va `.../portfolio[/{id}]` — slug o'zgarganda avtomatik `SlugRedirect` yozuvi yaratiladi (TZ 27: "Slugs o'zgarsa 301 redirect yaratiladi").
   - `app/pages.py`: xizmat/portfolio/yechim sahifalari va sitemap endi `services_store` orqali DB'dan o'qiydi; slug topilmasa avval redirect jadvali tekshiriladi, keyin 404.
   - `static/admin.html`: yangi "Xizmatlar" va "Portfolio" bo'limlari — har biri (key/order/published + 3 til tab: uz/ru/en) to'liq forma bilan, avtomatik saqlash (~0.7s debounce), qo'shish/o'chirish.
   - Test qilindi: barcha 7×3 xizmat va 3×3 portfolio sahifasi, yechim sahifalari, admin CRUD (create/update/slug-redirect/delete) — httpx orqali to'liq smoke-test o'tkazildi, hammasi ishlayapti.
   - **Team** — alohida DB jadvali qo'shilmadi: `Content.data.team` orqali CRUD allaqachon mavjud edi (admin panelda tab bor), faqat real a'zolar tasdiqlanmagani uchun saytda yashirilgan (0d42c7b) — TZ 19-band shu qismda avvaldan bajarilgan hisoblanadi.
6. **Yangiliklar (blog) tizimi SEO fieldlar bilan kuchaytirildi** (TZ 6-bo'lim). Tafsilotlar:
   - `app/db.py` Post jadvaliga qo'shildi: `lang` (post BITTA tilga tegishli — tarjima emas, mustaqil maqola), `excerpt`, `category`, `tags`, `author`, `seo_title`, `seo_description`, `noindex`.
   - `/{lang}/blog/` va `/{lang}/blog/{slug}/` endi faqat SHU tilga tegishli postlarni ko'rsatadi (ilgari barcha 3 til bir xil postlarni — hatto tarjima qilinmagan holda — ko'rsatardi, bu duplicate-content xavfi edi). Boshqa tilda "tarjimasi bor" deb yolg'on hreflang berilmaydi — til almashtirgich shunchaki o'sha tilning blog ro'yxatiga tushadi (`app/pages.py::_base_ctx` yangi `hreflang_paths` parametri).
   - `noindex` post — `<meta name="robots" content="noindex,nofollow">` (`templates/base.html`) va sitemap'dan chiqarib tashlanadi.
   - `templates/blog_detail.html`: bo'sh `<img alt="">` tuzatildi (endi sarlavha bilan), kategoriya/muallif/teglar ko'rsatiladi.
   - Bosh sahifa (`static/index.html/.ru.html/.en.html`): "Yangiliklar" bo'limi endi (a) faqat o'z tiliga tegishli postlarni ko'rsatadi (ilgari RU/EN sahifalarida bu bo'lim butunlay o'chirilgan edi — "hozircha faqat o'zbekcha" izohi bilan), (b) JS modal o'rniga TO'G'RIDAN-TO'G'RI `/​{lang}/blog/{slug}/` sahifasiga link beradi (ilgari kontent faqat modalda ko'rinardi, indekslanadigan sahifaga hech qanday havola yo'q edi — crawlability muammosi), (c) "Barcha maqolalar →" tugmasi qo'shildi (TZ 4.7).
   - `static/admin.html` Postlar formasiga yangi maydonlar: Til (select), Kategoriya, Teglar, Muallif, Qisqa tavsif, SEO title/description, Noindex checkbox, "↗ Sahifani ko'rish" havolasi.
   - Test qilindi: uz/ru/en alohida postlar, lang bo'yicha filtrlash, boshqa til yo'lida 404, noindex meta, sitemap'dan chiqarilishi — hammasi httpx orqali tasdiqlandi.
7. **Jamoa/About/Expertise bloki to'g'rilandi** (TZ 12/19-bo'lim). Tafsilotlar:
   - `app/pages.py::about_page()`dagi ISHLATILMAYDIGAN (dead code) 4 ta real ism/rol massivi olib tashlandi — bu ma'lumot `templates/about.html`da hech qachon render qilinmagan edi, lekin kodda turgani chalg'ituvchi edi. Real ismlar hamon KO'RSATILMAYDI (roziligi hali tasdiqlanmagan, TZ 29).
   - O'rniga TZ 12'ning aniq ko'rsatmasi bajarildi: "profillar tayyor bo'lmasa — 'Bizning ekspertiza' blokini ko'rsatish". `app/content/about.py`dagi `team_title`/`team_lead` (ilgari yozilgan, lekin shablonda ISHLATILMAGAN edi) endi `/biz-haqimizda/` sahifasida haqiqatan chiqadi; sarlavha "Jamoa"/"Команда"/"Team" dan "Bizning ekspertiza"/"Наша экспертиза"/"Our expertise" ga o'zgartirildi (ism yo'qligini aniq ko'rsatish uchun).
   - `facts_title` ("Raqamlarda" va h.k., ilgari yozilgan-lekin-ishlatilmagan) ham endi "Raqamlar" bloki ustida chiqadi.
   - Test qilindi: barcha 3 tilda sahifa 200, real ismlar (masalan "Tursunxo'jayev") HTML'da yo'qligi tasdiqlandi.
5. **OG image sahifaga xos qilindi + Portfolio'ga Screenshot maydoni qo'shildi** (TZ 5/13/15-bo'lim; foydalanuvchi bilan kelishilgan qaror — "yangi bog'liqlik (Pillow/WebP) qo'shmasdan, mavjudni tuzatish" tanlandi, avtomatik WebP konvertatsiya keyingi bosqichga qoldirildi). Tafsilotlar:
   - `app/pages.py::_base_ctx()` yangi `og_image` parametri — berilmasa `org.logo`ga qaytadi (`templates/base.html`). Blog posti (`p.image`) va Portfolio case (yangi `image` ustuni) endi o'z rasmini e'lon qiladi.
   - `PortfolioCase`ga `image` ustuni qo'shildi (TZ 13: "Screenshots" — ilgari BUTUNLAY yo'q edi). Tilga bog'liq emas (bitta case — bitta rasm, 3 marta kiritilmaydi). `templates/portfolio_detail.html`da ko'rsatiladi (`loading="lazy"`), admin.html'da "Screenshot rasm URL" maydoni.
   - `templates/blog_detail.html` rasmi endi `loading="lazy" decoding="async"` bilan.
   - **Yon-ta'sirda topilgan haqiqiy xato tuzatildi**: `Service`/`PortfolioCase.as_dict()` `slug`ni faqat top-level `slugs{}`da qaytarardi, har tilning o'z dict'i ichida EMAS — lekin `static/admin.html`dagi forma (`d.slug`) va `app/pages.py` ikkalasi ham `s[lang]["slug"]`ga tayanadi. Bu www admin panelda slug maydoni bo'sh ko'rinishi va saqlashda 422 xatosiga olib kelardi — httpx bilan to'g'ridan-to'g'ri API sinovi buni yashirgan edi (qo'lda to'g'ri payload yuborilgan), faqat admin.html'ning HAQIQIY oqimini (GET → mutatsiya → xom obyektni PUT) simulyatsiya qilgan sinov paytida topildi. Endi `as_dict()` slug'ni ikkala joyga ham qo'yadi.

**Navbatda (audit asosida, ustuvorlik tartibida):**
3. Business sign-off: statistika (32/24/98%/3yr), portfolio natijalari, FAQ javoblari, "3 oy bepul support" shartlari, jamoa bio/foto/LinkedIn — kelsa, `app/content/about.py`ga real profil qo'shish va Content.team'ni qayta yoqish mumkin.

**Audit orqali topilgan, hali ochiq qolgan boshqa masalalar:**
- `/uz/jamoa/` alohida URL sifatida yo'q (hozir `/biz-haqimizda/` ichida).
- Homepage (`static/index*.html`) 3 tilda qo'lda yozilgan, DB/CMS'ga bog'lanmagan — RU/EN UZ'dan orqada qolish xavfi bor.
- Homepage'dagi "Loyihalar" grid (`static/index.html`, `DATA.cases`) hamon ESKI, alohida (bir tilli, admin "Loyihalar" tab) content manbasidan chiqadi — endi yaratilgan yangi Portfolio (`/uz/portfolio/`) bilan bog'lanmagan, ikkita parallel portfolio manbasi mavjud (drift xavfi). Kelajakda birlashtirish kerak.
- LocalBusiness schema yo'q (ixtiyoriy, manzil/ish vaqti aniqlanguncha kutilmoqda).
