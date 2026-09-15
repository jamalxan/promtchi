"""«Biz haqimizda» sahifasi — real jamoa (/api/content) va tasdiqlangan faktlar
(Est. 2023, Toshkent) asosida. AI/GEO uchun yagona canonical kompaniya tavsifi
(TZ 10-bo'lim).

`team_title`/`team_lead` — jamoa a'zolarining ISMLARI EMAS, umumiy ekspertiza
bloki (TZ 12-bo'lim: "Agar jamoa profillari tayyor bo'lmasa... 'Bizning
ekspertiza' blokini ko'rsatish"). Real ism/rasm/bio ko'rsatish uchun roziligi
biznes tomonidan hali tasdiqlanmagan (TZ 29-bo'lim) — tasdiqlangach shu yerga
emas, alohida TeamIn (app/schemas.py) ro'yxatiga qo'shiladi."""

ABOUT = {
"uz": dict(
    title="Biz haqimizda — promtchi® raqamli mahsulotlar studiyasi",
    meta="promtchi — 2023-yildan Toshkentda faoliyat yuritayotgan raqamli mahsulotlar studiyasi. Veb, mobil, AI va CRM/ERP yechimlari ishlab chiqamiz.",
    h1="Biz haqimizda",
    lead="promtchi — 2023-yildan Toshkentda faoliyat yuritayotgan raqamli mahsulotlar studiyasi. Bizneslar uchun veb-sayt, mobil ilova, AI yechimlar va CRM/ERP tizimlarini MVP'dan to'liq mahsulotgacha ishlab chiqamiz.",
    mission="Bizning maqsadimiz — shunchaki sayt yoki ilova emas, balki biznesga real daromad va samaradorlik olib keladigan tizimlar qurish. Har bir loyihada dizayn, kod va avtomatlashtirishni bitta uzluksiz jarayonga birlashtiramiz.",
    what_we_do_title="Nima qilamiz",
    what_we_do=["Veb-sayt va web-app yaratish", "Android/iOS mobil ilova ishlab chiqish", "CRM va ERP tizimlari qurish", "Telegram bot dasturlash", "AI yechimlar (chatbot, ovozni matnga aylantirish)", "Biznes jarayonlarini avtomatlashtirish"],
    team_title="Bizning ekspertiza",
    team_lead="promtchi jamoasi — asoschilar va IT-mutaxassislardan iborat kichik, ammo tajribali jamoa. Har bir loyihada to'g'ridan-to'g'ri jamoa a'zolari ishlaydi, vositachi yo'q.",
    facts_title="Raqamlarda",
    facts=[("2023", "Tashkil topgan yil"), ("Toshkent", "Asosiy shahar"), ("14 kun", "MVP tayyor bo'lish muddati")],
),
"ru": dict(
    title="О нас — студия цифровых продуктов promtchi®",
    meta="promtchi — студия цифровых продуктов, работающая в Ташкенте с 2023 года. Разрабатываем веб, мобильные, AI и CRM/ERP решения.",
    h1="О нас",
    lead="promtchi — студия цифровых продуктов, работающая в Ташкенте с 2023 года. Разрабатываем сайты, мобильные приложения, AI-решения и CRM/ERP системы для бизнеса — от MVP до готового продукта.",
    mission="Наша цель — не просто сайт или приложение, а система, приносящая бизнесу реальный доход и эффективность. В каждом проекте мы объединяем дизайн, код и автоматизацию в единый непрерывный процесс.",
    what_we_do_title="Чем мы занимаемся",
    what_we_do=["Разработка сайтов и веб-приложений", "Разработка мобильных приложений Android/iOS", "Создание CRM и ERP систем", "Разработка Telegram-ботов", "AI-решения (чат-боты, распознавание речи)", "Автоматизация бизнес-процессов"],
    team_title="Наша экспертиза",
    team_lead="Команда promtchi — небольшая, но опытная команда основателей и IT-специалистов. В каждом проекте работают непосредственно члены команды, без посредников.",
    facts_title="В цифрах",
    facts=[("2023", "Год основания"), ("Ташкент", "Основной город"), ("14 дней", "Срок готовности MVP")],
),
"en": dict(
    title="About Us — promtchi® Digital Product Studio",
    meta="promtchi is a digital product studio operating in Tashkent since 2023. We build web, mobile, AI and CRM/ERP solutions.",
    h1="About Us",
    lead="promtchi is a digital product studio operating in Tashkent since 2023. We build websites, mobile apps, AI solutions and CRM/ERP systems for businesses — from MVP to a finished product.",
    mission="Our goal isn't just a website or an app — it's a system that brings your business real revenue and efficiency. On every project we unite design, code and automation into one continuous process.",
    what_we_do_title="What we do",
    what_we_do=["Website and web app development", "Android/iOS mobile app development", "CRM and ERP system development", "Telegram bot development", "AI solutions (chatbots, speech-to-text)", "Business process automation"],
    team_title="Our expertise",
    team_lead="The promtchi team is small but experienced — founders and IT specialists. Every project is worked on directly by the team, with no middlemen.",
    facts_title="By the numbers",
    facts=[("2023", "Founded"), ("Tashkent", "Home base"), ("14 days", "MVP delivery time")],
),
}
