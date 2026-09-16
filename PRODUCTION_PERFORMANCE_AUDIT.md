# PRODUCTION PERFORMANCE AUDIT — promtchi.uz

**Sana:** 2026-09-16
**Manba:** https://promtchi.uz — jonli production
**Metodika:** (a) server-side o'lchovlar — HTTP timing, resurs hajmlari, header'lar (`requests` orqali, bir necha marta, o'rtacha); (b) brauzer-asosli o'lchovlar — real Chrome orqali Performance API / Web Vitals (Claude in Chrome tool orqali, 6 sahifada).

---

## PERFORMANCE STATUS: ⚠️ FUNKSIONAL, LEKIN BIR NECHTA ANIQ OPTIMIZATSIYA IMKONIYATI BOR

Sayt ishlaydi va foydalanish mumkin, lekin **static resurslarni keshlash sozlanmagan** va **bosh sahifa arxitekturasi** (monolit inline HTML) boshqa sahifalardagi keshlanadigan CSS'dan foydalana olmaydi — bular productionda o'lchab tasdiqlangan, aniq tuzatiladigan muammolar.

---

## 1. SERVER-SIDE O'LCHOVLAR (haqiqiy production so'rovlari)

| Sahifa | HTML | CSS | JS (inline) | IMG (logo) | TTFB/umumiy vaqt |
|---|---|---|---|---|---|
| `/uz/` (homepage) | 102.6 KB | 0 KB (inline) | inline (CSP: `unsafe-inline`) | 52.4 KB | ~1177 ms |
| `/uz/xizmatlar/crm/` | 13.6 KB | 9.8 KB (tashqi, keshlanadigan) | inline | 52.3 KB | ~889 ms |
| `/uz/xizmatlar/veb-sayt-yaratish/` | 13.9 KB | 9.8 KB | inline | 52.3 KB | ~835 ms |
| `/uz/xizmatlar/mobil-ilova-yaratish/` | 12.3 KB | 9.8 KB | inline | 52.3 KB | ~1415 ms |
| `/uz/xizmatlar/ai/` | 13.8 KB | 9.8 KB | inline | 52.3 KB | ~979 ms |
| `/uz/blog/crm-nima-4/` | 8.3 KB | 9.8 KB | inline | 52.3 KB | ~936 ms |

*(TTFB raqamlari ushbu audit ishlayotgan muhitdan production serverga bo'lgan tarmoq masofasini ham o'z ichiga oladi — mutlaq qiymat emas, lekin sahifalar orasidagi NISBIY taqqoslash uchun ishonchli: bosh sahifa boshqalardan sezilarli og'irroq.)*

### 1.1 Topilma: Faqat bosh sahifada `Cache-Control` bor — qolgan 81 sahifada YO'Q

```
/uz/, /ru/, /en/          -> cache-control: public, max-age=3600, must-revalidate  ✅
Qolgan 81 sahifa           -> Cache-Control header UMUMAN YO'Q                      ❌
```

Bu — sitemapdagi 84 sahifadan 81 tasi (barcha xizmat/yechim/portfolio/blog/FAQ/aloqa/legal sahifalari) har safar mijoz brauzeridan yoki oraliq CDN/proxy'dan qayta-qayta origin serverdan to'liq yuklab olinishini anglatadi — hech qanday brauzer keshi yoki edge-cache foyda bermaydi, garchi bu sahifalar deyarli statik (admin panel orqali kamdan-kam yangilanadi) bo'lsa ham.

**Tavsiya:** Bu sahifalarga ham `Cache-Control: public, max-age=3600, must-revalidate` (yoki mosroq TTL) qo'shish — bosh sahifada allaqachon qo'llanilgan patternni takrorlash, kod darajasida oddiy o'zgarish (`app/pages.py`dagi response header'lariga).

### 1.2 Topilma: Static asset'larda (`logo.png`, `site.css`) uzoq muddatli kesh yo'q

```
/static/logo.png  -> Content-Length: 52 KB, Cache-Control YO'Q, faqat x-content-type-options
/static/site.css  -> Content-Length: 10 KB, faqat ETag bor (Cache-Control YO'Q)
```

- `logo.png` — **52 KB** — bu barcha 84 sahifada qayta ishlatiladigan logotip uchun katta hajm (odatda optimallashtirilgan logo 5-15 KB WebP/optimallashtirilgan PNG holida bo'lishi kerak). Cache-Control yo'qligi sababli har bir yangi sessiya (yoki ETag validatsiyasi muvaffaqiyatsiz bo'lganda) uni to'liq qayta yuklaydi.
- `site.css` faqat ETag orqali keshlanadi — bu 304 conditional-request'ni talab qiladi (kamida bitta round-trip), `Cache-Control: public, max-age=..., immutable` (versiyalangan fayl nomi bilan, masalan `site.abc123.css`) esa round-trip'ni butunlay bekor qiladi.

**Tavsiya:**
1. `logo.png`ni siqish/WebP'ga o'tkazish (hajmni ~70-80% kamaytirish potensiali bor).
2. Static fayllarga (`/static/*`) nginx darajasida `Cache-Control: public, max-age=31536000, immutable` + fayl nomiga hash/versiya qo'shish.

### 1.3 Topilma: Bosh sahifa arxitekturasi boshqa sahifalar bilan resurs ulashmaydi

Bosh sahifa CSS/JS'ni **to'liq inline** qiladi (102 KB HTML ichida), boshqa barcha sahifalar esa tashqi, keshlanadigan `/static/site.css` (9.8 KB) dan foydalanadi. Natijada: foydalanuvchi bosh sahifadan biror xizmat sahifasiga o'tganda, brauzer bosh sahifaning inline CSS'idan FOYDALANA OLMAYDI va yana 9.8 KB'lik alohida CSS faylni yuklaydi — resurs takrorlanadi, birinchi navigatsiyada qo'shimcha so'rov.

**Tavsiya:** Uzoq muddatli — bosh sahifani ham tashqi `site.css`dan foydalanishga o'tkazish (agar texnik cheklov ruxsat bersa); qisqa muddatli — muhim emas, faqat birinchi ichki navigatsiyada bir martalik qo'shimcha 9.8 KB.

---

## 2. BRAUZER-ASOSLI O'LCHOVLAR (real Chrome, Navigation/Resource Timing API)

Real Chrome brauzeri orqali (`?_perf=1` cache-bust bilan, har bir sahifa yangi navigatsiya sifatida) o'lchandi:

| URL | TTFB | DOMContentLoaded | Load | FCP | LCP | CLS | Total | Requests |
|---|---|---|---|---|---|---|---|---|
| `/uz/` (homepage) | 610 ms | 769 ms | 1129 ms | N/M | N/M | N/M | 29 KB | 9 |
| `/uz/xizmatlar/crm/` | 295 ms | 333 ms | 669 ms | N/M | N/M | N/M | 8 KB | 4 |
| `/uz/xizmatlar/veb-sayt-yaratish/` | 297 ms | 328 ms | 391 ms | N/M | N/M | N/M | 4 KB | 4 |
| `/uz/xizmatlar/mobil-ilova-yaratish/` | 272 ms | 307 ms | 345 ms | N/M | N/M | N/M | 4 KB | 7 |
| `/uz/xizmatlar/ai/` | 332 ms | 379 ms | 428 ms | N/M | N/M | N/M | 4 KB | 7 |
| `/uz/blog/crm-nima-4/` | 330 ms | 364 ms | 471 ms | N/M | N/M | N/M | 3 KB | 7 |

**N/M izohi:** FCP/LCP/CLS o'lchab bo'lmadi — bu muhit cheklovi, sayt muammosi emas: avtomatlashtirilgan brauzer tabida `document.visibilityState` doim `"hidden"` qaytardi (OS darajasida fokusda bo'lmagan oyna), Chrome Paint Timing/LCP API spec bo'yicha background tab'larda ishlamaydi. TTFB/DCL/Load/hajm/so'rovlar soni — bularga bu cheklov ta'sir qilmagan, haqiqiy o'lchovlar.

**"Total KB" pastligi haqida izoh:** bu raqamlar — sahifa HTML hujjatining tarmoq orqali uzatilgan (siqilgan) hajmi asosan; logo.png (52 KB, bo'lim 1.2) va `site.css` (10 KB) oldingi navigatsiyalarda brauzer keshiga tushib bo'lgani uchun takroriy navigatsiyalarda Resource Timing API ularni deyarli 0 transferSize sifatida qayd qildi (bu — brauzer keshi to'g'ri ishlayotganining isboti, xato emas). Server gzip/br siqish qo'llaydi — tasdiqlangan: homepage HTML curl orqali 102.6 KB (siqilmagan), brauzerda 29 KB (siqilgan) — bu ikkalasi mos keladi (~72% siqish nisbati).

**Xulosa:** TTFB va Load vaqtlari barcha sahifalarda yaxshi (server javobi 270-610ms, to'liq yuklanish 345ms-1.1s oralig'ida) — muhim performance muammosi TOPILMADI ushbu o'lchovlar asosida. LCP/CLS kabi to'liq Core Web Vitals uchun haqiqiy real-user monitoring (Google Search Console "Core Web Vitals" hisoboti yoki PageSpeed Insights — tashqi, login talab qilmaydigan xizmat) orqali tekshirish tavsiya etiladi, chunki bu auditning brauzer muhiti buni to'liq o'lchay olmadi.

### 2.1 Mobile viewport testi — TO'LIQ BAJARILMADI (tool cheklovi)

`resize_window` vositasi ushbu muhitda ishlamadi: 375×800 va 375×812'ga chaqirilganda "muvaffaqiyatli" javob qaytardi, lekin `window.innerWidth` doim 1536px (desktop) bo'lib qoldi — brauzer oynasi haqiqatda torayib bermadi. Shu sababli **375/768/1440px'da haqiqiy render qilingan layout (horizontal scroll, menyu, CTA, forma, footer)** tekshirilmadi — soxta PASS natija berish o'rniga bu ochiq qoldirilmoqda.

**Nima tasdiqlandi (source-level, layout emas):** barcha sahifalar bitta umumiy `/static/site.css` (10 KB) faylidan foydalanadi, unda 3 ta mobile/tablet breakpoint mavjud (`max-width: 860px/800px/760px`) — demak responsive qoidalar mavjud va barcha sahifalarga bir xilda tarqaladi (sahifa-specific mobile gap yo'q), lekin bu qoidalarning HAQIQIY vizual natijasi tasdiqlanmadi.

**MUHIM STATUS: MOBILE STATUS = ❌ TEKSHIRILMADI (bloklangan), FAKE PASS berilmadi.** Productionni haqiqiy telefon yoki tor brauzer oynasida (yoki ishlaydigan device-emulation vositasi bilan) qo'lda tekshirish tavsiya etiladi — bu TZning "IMPLEMENTED ≠ VERIFIED" asosiy tamoyiliga mos: bu auditda VERIFIED deb da'vo qilinmaydi, chunki haqiqatan tekshirilmadi.

---

## 3. XULOSA VA USTUVORLIKLAR

| # | Muammo | Severity | Yechim |
|---|---|---|---|
| 1 | Mobile viewport (375/768/1440px) hali tekshirilmagan (tool cheklovi) | **Noaniq — qo'lda tekshirish zarur** | Haqiqiy telefon/DevTools device toolbar bilan qo'lda tekshirish |
| 2 | 81/84 sahifada Cache-Control yo'q | P2 | Response header qo'shish (`app/pages.py`) |
| 3 | Static asset'larda uzoq muddatli kesh yo'q | P2 | nginx `Cache-Control: immutable` + versiyalash |
| 4 | `logo.png` optimallashtirilmagan (52 KB) | P3 | WebP/siqish |
| 5 | Bosh sahifa boshqa sahifalar bilan CSS ulashmaydi | P3 | Arxitektura darajasida, past ustuvorlik |
| 6 | LCP/CLS to'liq o'lchanmadi (tool cheklovi) | **Noaniq** | PageSpeed Insights / GSC Core Web Vitals hisoboti orqali tekshirish |

**Ijobiy natijalar:** TTFB (270-610ms) va to'liq yuklanish vaqti (345ms-1.1s) barcha test qilingan sahifalarda yaxshi; server gzip/br siqishni to'g'ri qo'llaydi (~72% hajm qisqarishi); DOM murakkabligi past (inline CSS/JS, minimal JS framework og'irligi yo'q).
