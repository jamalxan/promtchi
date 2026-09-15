"""Real case'lar — /api/content orqali tasdiqlangan (2026-09-15), professional
tarjima qilingan. Fake mijoz yoki fake ko'rsatkich yo'q — faqat haqiqiy natijalar.

DIQQAT: bu fayl endi RUNTIME'da o'qilmaydi — faqat app/services_store.py'ning
bir martalik seed_if_empty()'i uchun manba (`portfolio_cases` jadvali bo'sh
bo'lsa shu yerdagi qiymatlar bilan to'ldiriladi). Saytdagi haqiqiy kontent va
admin CRUD app/db.py PortfolioCase jadvalida (TZ 4/19-bo'lim) — shu faylni
tahrirlash saytga TA'SIR QILMAYDI, admin panel orqali o'zgartiring."""

CASE_KEYS = ["chindan-group", "notiq-ai", "tizimly"]

SLUGS = {
    "chindan-group": {"uz": "chindan-group", "ru": "chindan-group", "en": "chindan-group"},
    "notiq-ai": {"uz": "notiq-ai", "ru": "notiq-ai", "en": "notiq-ai"},
    "tizimly": {"uz": "tizimly", "ru": "tizimly", "en": "tizimly"},
}

CASES = {
"chindan-group": {
  "uz": dict(title="Chindan Group", cat="Avtomatlashtirish", client="Chindan Group", duration="20 kun",
    short="To'liq avtomatlashtirilgan sotuv oqimi — leaddan to'lovgacha.",
    problem="Leadlar qo'lda yig'ilar, sotuv jarayoni tarqoq va kuzatib bo'lmas edi.",
    solution="Lead → CRM → sotuv sayti → to'lov + hisobot zanjirini yagona tizimga birlashtirdik.",
    result="Qo'lda ishlar ~70% kamaydi, leaddan to'lovgacha vaqt sezilarli qisqardi.",
    tech="FastAPI, PostgreSQL, Telegram Bot API, Redis",
    meta="Chindan Group uchun sotuv avtomatlashtirish — lead, CRM, to'lov va hisobotni bitta tizimga birlashtirgan real loyiha."),
  "ru": dict(title="Chindan Group", cat="Автоматизация", client="Chindan Group", duration="20 дней",
    short="Полностью автоматизированная воронка продаж — от лида до оплаты.",
    problem="Лиды собирались вручную, процесс продаж был разрозненным и неотслеживаемым.",
    solution="Мы объединили цепочку лид → CRM → сайт продаж → оплата + отчётность в единую систему.",
    result="Ручной труд сократился примерно на 70%, время от лида до оплаты значительно уменьшилось.",
    tech="FastAPI, PostgreSQL, Telegram Bot API, Redis",
    meta="Автоматизация продаж для Chindan Group — лид, CRM, оплата и отчётность в единой системе."),
  "en": dict(title="Chindan Group", cat="Automation", client="Chindan Group", duration="20 days",
    short="A fully automated sales pipeline — from lead to payment.",
    problem="Leads were collected manually, and the sales process was fragmented and impossible to track.",
    solution="We unified the lead → CRM → sales site → payment + reporting chain into one system.",
    result="Manual work dropped by roughly 70%, and the time from lead to payment shortened significantly.",
    tech="FastAPI, PostgreSQL, Telegram Bot API, Redis",
    meta="Sales automation for Chindan Group — lead, CRM, payment and reporting unified in one system."),
},
"notiq-ai": {
  "uz": dict(title="Notiq AI", cat="AI yechimlar", client="Notiq", duration="25 kun",
    short="Notiqlikni tekshirish va oshirishda yordam beradigan mobil ilova.",
    problem="Juda ko'p insonlarda notiqlik (nutq so'zlash) muammolari bor edi.",
    solution="AI yordamida yechim taqdim etdik va qo'shimcha video-darsliklar orqali nutqni oshirish imkonini berdik.",
    result="Uydan turib ham notiqlik darajasini oshirish imkoni yaratildi.",
    tech="Flutter, Python, ASR pipeline",
    meta="Notiq AI — o'zbek tiliga moslashtirilgan ovozni matnga aylantirish (STT) texnologiyasi bilan qurilgan notiqlik ilovasi."),
  "ru": dict(title="Notiq AI", cat="AI-решения", client="Notiq", duration="25 дней",
    short="Мобильное приложение, помогающее оценивать и улучшать навыки публичной речи.",
    problem="У многих людей есть трудности с публичной речью.",
    solution="Мы предложили решение на основе ИИ, а дополнительные видеоуроки помогают улучшить речь.",
    result="Появилась возможность повышать уровень речи, не выходя из дома.",
    tech="Flutter, Python, ASR pipeline",
    meta="Notiq AI — приложение для развития навыков речи на основе технологии распознавания речи (STT), адаптированной под узбекский язык."),
  "en": dict(title="Notiq AI", cat="AI Solutions", client="Notiq", duration="25 days",
    short="A mobile app that helps assess and improve public speaking skills.",
    problem="Many people struggle with public speaking.",
    solution="We built an AI-powered solution, with extra video lessons to help improve speech.",
    result="Users can now improve their speaking level right from home.",
    tech="Flutter, Python, ASR pipeline",
    meta="Notiq AI — a public-speaking app built on a speech-to-text (STT) technology adapted for the Uzbek language."),
},
"tizimly": {
  "uz": dict(title="Tizimly", cat="Web & ilova", client="Tizimly (o'z mahsulotimiz)", duration="30 kun",
    short="Savdo, ombor, moliya, CRM va analitikani bitta joyda birlashtiruvchi multi-tenant B2B SaaS platforma.",
    problem="Biznes ma'lumotlari tarqoq edi — savdo Excelda, mijozlar CRMda, qo'ng'iroqlar telefoniyada. Hisobot yig'ish qo'lda va kechikib bajarilardi.",
    solution="Barcha jarayonlarni bitta tizimga yig'dik: har bir savdo ombor qoldig'ini avtomatik yangilaydi, AmoCRM, Bitrix24, UTEL va Meta Ads real vaqtda sinxronlanadi, Telegram bot to'lov va qarzdorlik haqida darhol xabar beradi.",
    result="Qo'lda ma'lumot kiritish yo'qoldi — daromad, qarzdorlik va jamoa samaradorligi real vaqtda ko'rinadi. Platformadan 150 dan ortiq kompaniya foydalanmoqda.",
    tech="Django DRF, PostgreSQL, Redis, Docker, Telegram Bot API",
    meta="Tizimly — savdo, ombor, moliya, CRM va analitikani birlashtirgan, 150+ kompaniya foydalanadigan B2B SaaS platforma."),
  "ru": dict(title="Tizimly", cat="Веб и приложение", client="Tizimly (наш собственный продукт)", duration="30 дней",
    short="Мультитенантная B2B SaaS-платформа, объединяющая продажи, склад, финансы, CRM и аналитику в одном месте.",
    problem="Бизнес-данные были разрознены — продажи в Excel, клиенты в CRM, звонки в телефонии. Сбор отчётности выполнялся вручную и с задержками.",
    solution="Мы объединили все процессы в одной системе: каждая продажа автоматически обновляет остатки склада, AmoCRM, Bitrix24, UTEL и Meta Ads синхронизируются в реальном времени, а Telegram-бот мгновенно сообщает об оплатах и задолженностях.",
    result="Ручной ввод данных исчез — доход, задолженность и эффективность команды видны в реальном времени. Платформой пользуются более 150 компаний.",
    tech="Django DRF, PostgreSQL, Redis, Docker, Telegram Bot API",
    meta="Tizimly — B2B SaaS-платформа для продаж, склада, финансов, CRM и аналитики, которой пользуются более 150 компаний."),
  "en": dict(title="Tizimly", cat="Web & App", client="Tizimly (our own product)", duration="30 days",
    short="A multi-tenant B2B SaaS platform that unifies sales, inventory, finance, CRM and analytics in one place.",
    problem="Business data was scattered — sales in spreadsheets, clients in a CRM, calls in a telephony system. Reporting was assembled manually and with delays.",
    solution="We brought every process into one system: each sale automatically updates warehouse stock, AmoCRM, Bitrix24, UTEL and Meta Ads sync in real time, and a Telegram bot instantly reports payments and outstanding debt.",
    result="Manual data entry is gone — revenue, debt and team performance are visible in real time. The platform is used by 150+ companies.",
    tech="Django DRF, PostgreSQL, Redis, Docker, Telegram Bot API",
    meta="Tizimly — a B2B SaaS platform for sales, inventory, finance, CRM and analytics, used by 150+ companies."),
},
}
