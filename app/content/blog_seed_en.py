"""Blog maqolalarining INGLIZCHA versiyasi (TZ 15-bo'lim: "RU/EN versiyalar ham
lokalizatsiya qilinadi").

Manba — `blog_seed.py` dagi o'zbekcha 7 maqola; `blog_seed_ru.py` bilan bir xil
tamoyil: bu TARJIMA, yangi da'vo yoki yangi statistika emas.

Ichki havolalar EN slug'lariga moslashtirilgan (app/content/services.py::SLUGS):
web-development, mobile-app-development, business-process-automation;
crm/erp/ai/telegram-bot barcha tillarda bir xil.

`tags` ning birinchi elementi — xizmat `key`i, tarjima qilinmaydi.

Runtime'da o'qilmaydi — app/db.py::run_data_fixups() dagi bir martalik
migratsiya manbai (marker: "blog_i18n_ru_en_v1_done").
"""

ARTICLES_EN = [
    dict(
        title="7 signs your business needs a CRM",
        category="CRM",
        tags="crm,sales,automation",
        excerpt="Leads slip through the cracks, nobody knows who is at which stage, and reports take hours — 7 clear signs it is time for a CRM.",
        seo_title="7 signs your business needs a CRM | promtchi",
        seo_description="Lost leads, scattered reports, duplicate clients — 7 clear signs that your business needs a CRM system, and the way out.",
        body="""CRM (Customer Relationship Management) is a system for managing clients and the sales process. Many companies think "it is too early for us", but if several of the signs below feel familiar, your sales process has already outgrown manual management.

## 1. Leads get lost between Excel, notebooks and Telegram

When a new enquiry lives at the same time in a spreadsheet, a manager's private Telegram chat and a paper notebook, nobody sees the full picture. When the manager leaves, their leads leave with them.

## 2. You cannot say exactly who is at which stage

If the answer to "how many leads are close to payment right now?" is a guess, your sales funnel is not visible.

## 3. Information is passed between managers by hand

When several people work with one client (one takes the enquiry, another signs the contract) and the details are passed verbally or as screenshots, mistakes are inevitable.

## 4. Preparing a report takes hours or days

If a simple end-of-month report — "how many leads came in and how many paid" — requires opening several files and counting by hand, that is lost time.

## 5. Duplicate leads go unnoticed

When a client enquires twice, spotting it manually is hard — and two managers end up calling the same person.

## 6. Orders from Telegram are copied manually

If a manager manually moves an order from a Telegram bot or channel into another system, that step can be automated.

## 7. Onboarding a new employee takes weeks

When the process is not formalised, every new manager is trained by word of mouth — slow, and the result is inconsistent.

## All of these signs share one root cause

Most of the problems above come down to the same thing: there is no central sales system. A [CRM system](/en/xizmatlar/crm/) puts the whole path from incoming lead to accepted payment into a Kanban funnel, syncs with Telegram in both directions and detects duplicate leads automatically.

The [Chindan Group project](/en/portfolio/chindan-group/) had exactly these problems. After the lead → CRM → payment → reporting chain was unified into one system, manual work dropped by roughly 70%.

## Frequently asked questions

- **How is a CRM different from Excel?** A spreadsheet is a static list: no history, no stage tracking, no automatic notifications. A CRM gives a full history per lead, an assigned manager and automated stage management.
- **Does it work with an existing AmoCRM or Bitrix24?** Yes — in real projects we have built synchronisation with AmoCRM, Bitrix24, UTEL and Meta Ads; details on the [CRM service page](/en/xizmatlar/crm/).

If two or three of these signs feel familiar, [get in touch](/en/aloqa/) — we will discuss your project for free.""",
    ),
    dict(
        title="CRM or Excel: which is better for business?",
        category="CRM",
        tags="crm,excel,sales",
        excerpt="Excel is cheap and familiar, but it hits a ceiling as sales grow. We compare when a spreadsheet is enough and when it is time for a CRM.",
        seo_title="CRM or Excel: which is better for business? | promtchi",
        seo_description="Comparing a spreadsheet with a CRM system: when Excel still works and when it is time to move to a CRM. Practical criteria and examples.",
        body="""Many small companies start running sales in Excel — and that makes sense: it is cheap, familiar and fast. But as the number of leads grows, the spreadsheet slowly turns into a problem. Let us look at when Excel is enough and when a CRM is the better answer.

## When Excel is still enough

If you get a few dozen leads a month, one manager handles every client personally and the sales process is simple (single stage), Excel may still be enough. It costs nothing extra and needs no training.

## Where Excel breaks

- **When several people edit at once** — versions clash and data is lost.
- **When you need to track stages** — a "status" column exists, but there is no history, no timestamps and no automatic notifications.
- **When leads should arrive automatically** — a spreadsheet cannot be integrated with your site or Telegram, so everything is typed in by hand.
- **When you need reports and conversion analysis** — formulas have to be written and maintained manually, which invites errors.

## What a CRM adds

A [CRM system](/en/xizmatlar/crm/) gives you a staged Kanban funnel, full history and notes per lead, two-way notifications through Telegram, automatic duplicate detection and real-time statistics (conversion, per-manager breakdown, CSV export).

In practice the difference looks like this: in Excel, answering "how many leads are at the payment stage?" means opening the file and filtering by hand. In a CRM it means glancing at one column on the board.

## When it is time to move

If several of the following are true, a CRM is probably overdue:

- several managers work with leads at the same time;
- leads come from several sources (site, Telegram, calls);
- the monthly report takes a noticeable amount of time;
- the history of communication matters (repeat sales, follow-up).

## Conclusion

Excel is not a bad place to start, but growth brings a ceiling. In a [real project](/en/portfolio/tizimly/) we merged scattered data (Excel, CRM, telephony) into one system and removed manual data entry entirely.

If you want to work out where your sales process stands, [get in touch](/en/aloqa/) — we will give a recommendation based on your situation.""",
    ),
    dict(
        title="What is an ERP and how does it differ from a CRM?",
        category="ERP",
        tags="erp,crm,business",
        excerpt="ERP and CRM are often confused, yet they solve different problems. We explain the difference, who needs which, and how they work together.",
        seo_title="What is an ERP and how does it differ from a CRM? | promtchi",
        seo_description="What is the difference between ERP and CRM? Which business needs which — and how the two work together, explained with clear examples.",
        body="""The terms ERP (Enterprise Resource Planning) and CRM (Customer Relationship Management) are often mixed up, although they solve different problems.

## What a CRM is responsible for

A CRM works with the client and the sales process: where the lead came from, which stage it is at, who spoke to them, when the payment came in. The focus is the **client**.

## What an ERP is responsible for

An ERP manages the company's internal resources: finance (revenue, costs, payroll), stock and inventory, staff and KPIs. The focus is the **company itself**.

## A simple example

The sales team works with the client in the CRM — a lead arrives, negotiations happen, a contract is signed. Once it is signed, the goods have to leave the warehouse, appear in the financial report and count towards an employee's KPI — that is the ERP's job.

## Which business needs which

- If you only need order in the sales process (lead → client), a [CRM](/en/xizmatlar/crm/) is enough.
- If stock, finance or multi-employee processes have become complex (retail, manufacturing, logistics), you will need an [ERP](/en/xizmatlar/erp/).
- If you need both, they are integrated: every sale in the CRM automatically affects stock and finance in the ERP.

## How they work together

In practice ERP and CRM are often connected into one flow: the client pays in the CRM → the event is passed to the ERP → the item is written off stock and lands in the financial report. That is what [business process automation](/en/xizmatlar/business-process-automation/) means.

## Frequently asked questions

- **Does a small business need an ERP?** Usually not — a small team is well served by a CRM and simple reporting. An ERP makes sense for medium and large businesses with a warehouse or a large headcount.
- **Can it work with our existing accounting software?** Yes — integration with systems already in use (accounting, warehouse software) is done through their API.

If you want to work out which solution fits your company, [get in touch](/en/aloqa/).""",
    ),
    dict(
        title="How does AI automate business processes?",
        category="AI",
        tags="ai,automation,chatbot",
        excerpt="Chatbots, speech-to-text, content generation — we look at the points where artificial intelligence genuinely automates business processes.",
        seo_title="How does AI automate business processes? | promtchi",
        seo_description="How AI automates support, content and speech-to-text — the real opportunities and the limits, without inflated expectations.",
        body="""Artificial intelligence has become a buzzword in recent years, but what matters for a business is different: in which specific processes does it actually save time and money.

## 1. Customer support (chatbot)

Most enquiries are repeat questions: "what are your hours", "how much does it cost", "how do I place an order". An AI chatbot answers those automatically and hands the complex cases to a human.

## 2. Speech-to-text (STT)

For call centres, voice messages and speech-based products, accurate transcription matters. Many off-the-shelf solutions perform poorly in Uzbek — which is why a language-adapted model is needed. In the [Notiq AI project](/en/portfolio/notiq-ai/) we built an STT model adapted to Uzbek for exactly this task.

## 3. Content generation

When preparing product descriptions, social posts or email templates, AI speeds the work up — but the result always needs a human check.

## 4. Classifying and routing enquiries

Automatically sorting an incoming message into categories ("question", "complaint", "order") and routing it to the right team is another practical use.

## Where AI is not reliable yet

AI is not suited to important or one-off decisions (final contract terms, financial decisions) — those need human control. It performs best on repetitive, rule-based tasks.

## A practical approach

The most effective way to adopt AI is to start small: automate one specific process (for example, frequent questions in a Telegram bot), measure the result, then expand. The [AI solutions page](/en/xizmatlar/ai/) describes in detail which task is solved by which approach.

## Frequently asked questions

- **Can an AI chatbot be connected to Telegram or a website?** Yes — the chatbot integrates into any channel: site, Telegram, mobile app.
- **Is there a solution that works in Uzbek?** Yes — in the Notiq AI project we developed an STT model adapted to Uzbek.

To find out which of your processes is worth automating first, [get in touch](/en/aloqa/).""",
    ),
    dict(
        title="What does a Telegram bot give a business?",
        category="Telegram bot",
        tags="telegram-bot,orders,automation",
        excerpt="A Telegram bot is more than an auto-reply. Connected to a CRM, it automates order intake and client communication end to end.",
        seo_title="What does a Telegram bot give a business? | promtchi",
        seo_description="Taking orders through a Telegram bot, syncing with a CRM and automatic notifications — the real opportunities for business, with examples.",
        body="""In Uzbekistan, Telegram is not only a messenger but a sales and customer communication channel. Many businesses take orders directly in Telegram. The problem is that a basic bot only sends canned replies, and everything else is done by hand.

## The difference between a basic bot and one connected to a CRM

A basic bot answers commands but stores nothing. A manager has to read every message and copy it manually into another system (CRM, Excel).

A [bot connected to a CRM](/en/xizmatlar/telegram-bot/) creates a lead in the CRM automatically when a new order arrives, posts a message to the team group, and lets the manager change the stage with inline buttons ("New" → "In progress" → "Paid"). The change is instantly in sync with the site and the CRM.

## Practical scenarios

- **Order intake** — the client writes to the bot and the details land in the CRM automatically.
- **Group notifications** — a new lead posts a message into the sales team's Telegram group.
- **Stage management** — the manager changes the lead stage with inline buttons in the group, without opening the CRM.
- **Automatic reminders** — the bot reminds about an approaching payment or meeting.

## What it takes technically

Such a bot is usually built on aiogram (Python), stores data in PostgreSQL and works with a queue (Redis) that handles load — which keeps the bot responsive when many messages arrive at once.

## When a simple bot is enough and when you need CRM integration

If order volume is low and one manager can keep track of everything, a simple auto-reply bot is enough. As volume grows, a professional bot wired into a CRM saves noticeable time and reduces mistakes.

## Frequently asked questions

- **Can the bot be added to our existing group?** Yes — the bot is added to your existing Telegram group or channel.
- **How does the bot stay in sync with the CRM?** A new request triggers a message from the bot, and stages are changed with buttons — the sync works both ways.

If you want your Telegram orders connected to a system, [get in touch](/en/aloqa/).""",
    ),
    dict(
        title="When does a business need a mobile app?",
        category="Mobile app",
        tags="mobile,web,business",
        excerpt="Not every business needs an app. We use clear criteria to show when a website is enough and when an app adds real value.",
        seo_title="When does a business need a mobile app? | promtchi",
        seo_description="A mobile app is not always necessary. We compare the cases where a website is enough with the cases where an app adds real value.",
        body="""A mobile app looks impressive, but not every business needs one. Built at the wrong moment, it can become an expensive "digital display window" with no users.

## When a website is enough

If clients contact you rarely (say, once a month) or make a one-off purchase, a responsive website is enough. The user does not have to spend time installing anything, and the site opens instantly.

## When an app genuinely adds value

- **You have regular users** — for example, clients ordering several times a week (delivery, services).
- **Push notifications matter** — when a discount, order status or reminder has to reach the user immediately.
- **You need an offline mode** — when the work has to continue on an unstable connection.
- **You need device features** — camera, GPS and push are limited on the web.

## The middle option: a web app

Sometimes a full mobile app is not required — a [web app](/en/xizmatlar/web-development/) (a mobile-friendly client area) is enough in many cases: nothing to install, yet it behaves like an app.

## A practical example

The [Notiq AI project](/en/portfolio/notiq-ai/) was built as a mobile app precisely because users practise regularly and track their progress — a repeat-use scenario that a website cannot deliver.

## Conclusion: how to decide

Ask yourself: how often do clients come back? Do push notifications add real value? Do you need device features (camera, GPS)? If the answer is yes, a [mobile app](/en/xizmatlar/mobile-app-development/) is a sound investment. If not, starting with a website or web app is cheaper and faster.

## Frequently asked questions

- **Can you build for Android only, or iOS only?** Yes — a single platform is possible if you prefer, and it is usually cheaper and faster.
- **Can an existing website be turned into an app?** Yes — an app can be built on the existing backend API, so the site and the app work with the same data.

If you want to work out whether your project needs a website or an app, [get in touch](/en/aloqa/).""",
    ),
    dict(
        title="Where should you start with business automation?",
        category="Automation",
        tags="automation,business,reporting",
        excerpt="Automation is not about changing everything at once. We explain, step by step, which process to start with and in what order to move.",
        seo_title="Where should you start with business automation? | promtchi",
        seo_description="Where to begin with automation? Practical steps from mapping processes to launch, plus a real example from a project.",
        body=""""Automation" is often understood as "digitise everything at once" — which makes a project so complex that it stalls before it starts. In reality, effective automation always begins with one specific process.

## Step 1: write down what is done manually

For one week, watch which actions your team repeats by hand: moving a lead into another system, assembling a report manually, checking payment status manually. That list is the most accurate starting point.

## Step 2: pick the process that eats the most time

You do not need to automate everything at once. Take the single chain that costs the most time or causes the most mistakes — for example, "from incoming lead to confirmed payment".

## Step 3: find the gaps between systems

The problem is usually not the system itself but the gap between systems: the site captures a lead, but it does not reach the CRM automatically; a payment is taken, but stock is not updated. Those gaps are the automation points.

## Step 4: start small and measure

Do not connect the whole chain at once — wire up one link (for example, site → CRM), measure the result (time saved, fewer errors), then move to the next.

## A real example

The [Chindan Group project](/en/portfolio/chindan-group/) followed exactly this approach: first the lead flow was connected to the CRM, then payment and reporting stages were added. As a result the whole lead → payment chain is automated and manual work dropped by roughly 70%.

## The tools most often needed

- [CRM](/en/xizmatlar/crm/) — to centralise work with leads and clients
- [Telegram bot](/en/xizmatlar/telegram-bot/) — for order intake and notifications
- Payment system integration — to track payment status automatically
- Synchronisation with an external CRM (AmoCRM, Bitrix24) — to keep the system you already use

The approach is described in detail on the [automation service page](/en/xizmatlar/business-process-automation/).

## Frequently asked questions

- **Does automation deliver a real result?** Yes — in the Chindan Group project we automated the chain from lead to payment and cut manual work by roughly 70%.
- **Which systems can you connect?** Websites, Telegram bots, CRMs (including AmoCRM/Bitrix24), payment systems and warehouse software — into a single flow.

To work out which process to start with in your case, [get in touch](/en/aloqa/).""",
    ),
]
