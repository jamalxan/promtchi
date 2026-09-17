"""Xavfsizlik middleware'lari: header'lar, body hajmi cheklovi, rate-limit.

Hammasi SOF ASGI middleware — BaseHTTPMiddleware emas. BaseHTTPMiddleware har
bir so'rov uchun alohida task group + memory stream ochadi; uchtasi ustma-ust
10k+ RPS'da sezilarli CPU va latency qo'shadi. Sof ASGI varianti esa oddiy
funksiya chaqiruvi narxida ishlaydi.
"""
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

from .config import settings
from .ratelimit import MinInterval, TokenBucket, client_ip

# Sayt bitta HTML fayl: inline <style>/<script> va onclick'lar ishlatiladi,
# shuning uchun 'unsafe-inline' shart. Tashqi skript yuklashni esa bloklaydi.
# upgrade-insecure-requests faqat production'da: HTTPS'siz (faqat HTTP) muhitda
# brauzer API so'rovlarini https'ga majburan o'tkazib, saytni ishlamay qo'yadi.
# GA4 faqat GA_MEASUREMENT_ID berilganda ulanadi — shuning uchun uning
# domenlari ham FAQAT o'shanda CSP'ga qo'shiladi (analitika yoqilmagan saytda
# ruxsat ochiq turmaydi). Busiz gtag.js "script-src 'self'"ga urilib bloklanar,
# hodisalar esa "connect-src 'self'" sababli hech qayerga yetib bormas edi.
_GA_SCRIPT = ["https://www.googletagmanager.com"]
_GA_CONNECT = [
    "https://www.google-analytics.com",
    "https://analytics.google.com",
    "https://*.analytics.google.com",
    "https://*.google-analytics.com",
    "https://www.googletagmanager.com",
]
_ga_on = bool(settings.GA_MEASUREMENT_ID)

CSP = "; ".join([
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "img-src 'self' data: blob: https:",
    "media-src 'self' data: blob: https:",  # yuklangan videolar
    "frame-src https://www.youtube.com https://www.youtube-nocookie.com https://player.vimeo.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com",
    " ".join(["script-src 'self' 'unsafe-inline'"] + (_GA_SCRIPT if _ga_on else [])),
    " ".join(["connect-src 'self'"] + (_GA_CONNECT if _ga_on else [])),
    "form-action 'self'",
] + (["upgrade-insecure-requests"] if settings.is_production else []))

# Har so'rovda qayta hisoblamaslik uchun bir marta tayyorlab qo'yamiz
_BASE_HEADERS: list[tuple[str, str]] = [
    ("Content-Security-Policy", CSP),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Permissions-Policy", "geolocation=(), microphone=(), camera=(), interest-cohort=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("X-XSS-Protection", "0"),  # zamonaviy brauzerlarda CSP ishlaydi
]


# Ichki SSR sahifalar — QISQA kesh (60s), ilgari 3600s (1 soat) edi.
# Sabab: deploy'dan keyin brauzer 1 soatgacha ESKI HTML'ni ko'rsatardi va
# foydalanuvchi yangilanishlarni umuman ko'rmasdi (bu muammo bir necha bor
# kuzatildi — hard reload qilinmaguncha eski dizayn turardi).
# Nega 0 emas, 60: bu sahifalarda ETag yo'q, ya'ni max-age=0 bo'lsa har bir
# havolani bosganda HTML to'liq qaytadan yuklanadi. 60s — muvozanat: deploy
# bir daqiqada yetib boradi, navigatsiya esa keshdan tez ishlaydi.
# Eski HTML + yangi CSS nomuvofiqligi endi BO'LMAYDI, chunki site.css/js
# ?v=<mtime> bilan versiyalangan — eski HTML eski CSS'ni, yangisi yangisini
# chaqiradi, ikkalasi ham o'zaro mos.
_PUBLIC_PAGE_CACHE = "public, max-age=60, must-revalidate"
# `/static/uploads/*` fayl nomlari secrets.token_hex(8) bilan yaratiladi
# (main.py::upload_file) — bir URL HECH QACHON boshqa kontentga almashmaydi
# (qayta yuklash yangi nom oladi), shuning uchun immutable xavfsiz.
_UPLOADS_CACHE = "public, max-age=31536000, immutable"
# Qolgan /static/* (logo.png, site.css, admin.html, ...) — repo bilan birga
# deploy qilinadi, fayl nomi versiyalanmagan (hash yo'q), shu sabab
# immutable EMAS — o'rtacha TTL bilan muddat tugagach qayta tekshiriladi.
_STATIC_ASSET_CACHE = "public, max-age=86400, must-revalidate"
# `site.css?v=<hash>` / `site.js?v=<hash>` — URL fayl mazmuniga bog'langan
# (hash o'zgarsa URL ham o'zgaradi), shuning uchun bunday so'rovlar uchun
# uzoq muddatli immutable kesh xavfsiz: qayta tekshirish so'rovi ham ketmaydi.
# Versiyasiz (`/static/site.css`) so'rov esa eski qoida bilan qoladi.
_STATIC_VERSIONED_CACHE = "public, max-age=31536000, immutable"


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app
        self.headers = list(_BASE_HEADERS)
        if settings.is_production and settings.HSTS_SECONDS > 0:
            self.headers.append((
                "Strict-Transport-Security",
                f"max-age={settings.HSTS_SECONDS}; includeSubDomains",
            ))

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        versioned = b"v=" in scope.get("query_string", b"")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                h = MutableHeaders(raw=message["headers"])
                for k, v in self.headers:
                    h.setdefault(k, v)
                # admin/API javoblari keshlanmasin (parol so'raladigan yoki
                # sessiyaga bog'liq har qanday sahifa/API — brauzer/oraliq
                # keshlar hech qachon eski holatni ko'rsatmasin)
                # Qidiruv tizimlari indekslamasligi kerak bo'lgan yo'llar —
                # robots.txt "so'ramaslikni" aytadi, X-Robots-Tag esa tashqi
                # havola orqali kelib qolgan holatda ham indeksdan chetda
                # qoldiradi (robots.txt bloklagan sahifa baribir indeksga
                # tushishi mumkin — Google buni alohida ogohlantiradi).
                if (
                    path.startswith("/api/")
                    or path.startswith("/admin")
                    or path in ("/docs", "/redoc", "/openapi.json")
                ):
                    h.setdefault("X-Robots-Tag", "noindex, nofollow")
                if (
                    path.startswith("/api/admin")
                    or path.startswith("/api/auth/")
                    or path == "/admin"
                ):
                    h["Cache-Control"] = "no-store"
                elif (
                    200 <= message["status"] < 300
                    and path.startswith("/static/uploads/")
                    and "cache-control" not in h
                ):
                    h["Cache-Control"] = _UPLOADS_CACHE
                elif (
                    200 <= message["status"] < 300
                    and path.startswith("/static/")
                    and "cache-control" not in h
                ):
                    h["Cache-Control"] = (
                        _STATIC_VERSIONED_CACHE if versioned else _STATIC_ASSET_CACHE
                    )
                elif (
                    200 <= message["status"] < 300
                    and not path.startswith("/api/")
                    and not path.startswith("/static/")
                    and "cache-control" not in h
                ):
                    # Ichki SEO sahifalar (xizmatlar/portfolio/faq/blog/...,
                    # app/pages.py) — bosh sahifada (main.py::_PAGE_CACHE)
                    # allaqachon qo'llanilgan naqshni takrorlaymiz (production
                    # audit: 81/84 sahifada Cache-Control umuman yo'q edi).
                    # Sahifalar admin panel orqali kamdan-kam yangilanadi;
                    # `must-revalidate` ETag/Last-Modified bo'lmasa ham muddat
                    # tugagach har doim originaldan qayta tekshirtiradi.
                    h["Cache-Control"] = _PUBLIC_PAGE_CACHE
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodyLimitMiddleware:
    """Content-Length bo'yicha oldindan rad etish — katta body serverni bo'g'masin."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Fayl yuklash yo'li uchun kattaroq limit (rasm/video)
        limit = (settings.MAX_UPLOAD_BYTES
                 if scope["path"] == "/api/admin/upload" else settings.MAX_BODY_BYTES)
        cl = Headers(scope=scope).get("content-length")
        if cl:
            try:
                if int(cl) > limit:
                    resp = JSONResponse({"detail": "So'rov hajmi juda katta"}, status_code=413)
                    return await resp(scope, receive, send)
            except ValueError:
                resp = JSONResponse({"detail": "Noto'g'ri Content-Length"}, status_code=400)
                return await resp(scope, receive, send)
        await self.app(scope, receive, send)


# Limiterlar modul darajasida — login endpoint'i ham ularga murojaat qiladi
api_limiter = TokenBucket(
    settings.API_RATE_LIMIT, settings.API_RATE_WINDOW_SECONDS, settings.RATE_LIMIT_MAX_KEYS
)
lead_limiter = TokenBucket(
    settings.LEAD_RATE_LIMIT, settings.LEAD_RATE_WINDOW_SECONDS, settings.RATE_LIMIT_MAX_KEYS
)
lead_gap = MinInterval(settings.LEAD_MIN_INTERVAL_SECONDS, settings.RATE_LIMIT_MAX_KEYS)


review_limiter = TokenBucket(5, 3600, settings.RATE_LIMIT_MAX_KEYS)


def check_review_limits(ip: str) -> tuple[bool, int, str]:
    """Fikr yozish limiti — soatiga 5 ta urinish (kod brute-force'iga qarshi)."""
    ok, retry = review_limiter.hit(ip)
    if not ok:
        return False, retry, "Juda ko'p urinish — birozdan so'ng qayta urining"
    return True, 0, ""


def check_lead_limits(ip: str) -> tuple[bool, int, str]:
    """Ariza limitlari: (ruxsat, retry_after, xabar).

    Endpoint ichida, Pydantic validatsiyasi MUVAFFAQIYATLI o'tgandan keyin
    chaqiriladi — noto'g'ri to'ldirilgan forma limit yemaydi.
    """
    ok, retry = lead_gap.hit(ip)
    if not ok:
        return False, retry, "Juda tez — bir necha soniyadan so'ng urining"
    ok, retry = lead_limiter.hit(ip)
    if not ok:
        return False, retry, "Ariza chegarasiga yetdingiz — birozdan so'ng qayta urining"
    return True, 0, ""
# Login: token faqat NOTO'G'RI parolda yeyiladi (main.py), middleware faqat tekshiradi
login_limiter = TokenBucket(
    settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCKOUT_SECONDS, settings.RATE_LIMIT_MAX_KEYS
)

# Parol tiklash / email tasdiqlash — haqiqiy email yuborishni ishga tushiradi,
# shuning uchun qattiqroq: soatiga 3 ta urinish (IP bo'yicha).
pwreset_limiter = TokenBucket(3, 3600, settings.RATE_LIMIT_MAX_KEYS)


def check_pwreset_limit(ip: str) -> tuple[bool, int]:
    return pwreset_limiter.hit(ip)


class RateLimitMiddleware:
    """Rate-limit — DB sessiyasi olinishidan OLDIN ishlaydi.

    Bu muhim: endpoint ichida tekshirilsa, bloklanishi kerak bo'lgan so'rov ham
    ulanishlar pulidan joy band qilib, pul tugashiga sabab bo'ladi.
    """

    def __init__(self, app):
        self.app = app

    @staticmethod
    async def _429(msg: str, retry: int, scope, receive, send):
        resp = JSONResponse(
            {"detail": msg}, status_code=429, headers={"Retry-After": str(retry)}
        )
        await resp(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)

        path = scope["path"]
        client = scope.get("client")
        ip = client_ip(
            Headers(scope=scope),
            client[0] if client else "unknown",
            settings.TRUST_PROXY,
            settings.PROXY_HOPS,
        )
        # request.state.client_ip endpoint'larda o'qiladi
        scope.setdefault("state", {})["client_ip"] = ip

        if path == "/api/health":
            return await self.app(scope, receive, send)

        ok, retry = api_limiter.hit(ip)
        if not ok:
            return await self._429("Juda ko'p so'rov — birozdan so'ng urining", retry, scope, receive, send)

        # Eslatma: lead gap/limit endpoint ichida (validatsiyadan KEYIN) tekshiriladi —
        # xato to'ldirilgan forma (422) foydalanuvchi limitini yemasligi kerak.
        # Flood'dan yuqoridagi api_limiter himoya qiladi.

        if path == "/api/auth/login" and scope["method"] == "POST":
            # Faqat tekshiramiz — token noto'g'ri parolda main.py'da yeyiladi,
            # shuning uchun to'g'ri parol bilan qayta-qayta kirish bloklanmaydi.
            ok, retry = login_limiter.peek(ip)
            if not ok:
                return await self._429(
                    "Juda ko'p noto'g'ri urinish — vaqtincha bloklandi", retry, scope, receive, send
                )

        await self.app(scope, receive, send)
