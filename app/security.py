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
CSP = "; ".join([
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "img-src 'self' data: blob: https:",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' data: https://fonts.gstatic.com",
    "script-src 'self' 'unsafe-inline'",
    "connect-src 'self'",
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

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                h = MutableHeaders(raw=message["headers"])
                for k, v in self.headers:
                    h.setdefault(k, v)
                # admin/API javoblari keshlanmasin
                if path.startswith("/api/admin") or path == "/api/auth/login":
                    h["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodyLimitMiddleware:
    """Content-Length bo'yicha oldindan rad etish — katta body serverni bo'g'masin."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        cl = Headers(scope=scope).get("content-length")
        if cl:
            try:
                if int(cl) > settings.MAX_BODY_BYTES:
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
