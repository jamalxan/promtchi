"""IP aniqlash va rate-limit (token bucket).

Nega token bucket va nima uchun "har 30 soniyada 1 ta" emas:
  Eski mantiq bitta IP dan 30 soniyada 1 ta arizaga ruxsat berardi. Reverse-proxy
  ortida BARCHA foydalanuvchilar bitta IP (proxy) sifatida ko'rinadi, ya'ni butun
  sayt daqiqasiga 2 ta ariza qabul qilardi. Bundan tashqari bitta ofis yoki uyali
  operator NAT'i ortidagi odamlar ham bir-birini bloklardi.

  Token bucket burst'ga ruxsat beradi (masalan 10 daqiqada 5 ta), shuning uchun
  real odamlar bloklanmaydi, spam esa baribir to'xtatiladi.
"""
import time


def client_ip(headers, peer_host: str, trust_proxy: bool, hops: int = 1) -> str:
    """Haqiqiy mijoz IP'si. `headers` — .get() ga ega mapping (starlette Headers).

    trust_proxy=False bo'lsa faqat TCP peer IP ishlatiladi (header'lar
    soxtalashtirilishi mumkin, shuning uchun ishonchsiz proxy'da o'qilmaydi).
    """
    if trust_proxy:
        cf = headers.get("cf-connecting-ip")
        if cf:
            return cf.strip()
        xff = headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                # o'ngdan `hops`-inchi element — bizga eng yaqin ishonchli proxy'dan keyingisi
                idx = max(0, len(parts) - hops)
                return parts[idx] if idx < len(parts) else parts[0]
        xr = headers.get("x-real-ip")
        if xr:
            return xr.strip()
    return peer_host or "unknown"


class TokenBucket:
    """Xotiradagi token bucket. Kalit boshiga ikkita float — juda ixcham.

    Eslatma: bir nechta uvicorn worker ishlatilsa har bir worker o'z hisobini
    yuritadi (limit worker soniga ko'payadi). Qat'iy global limit kerak bo'lsa
    Redis backend qo'shish kerak.
    """

    __slots__ = ("capacity", "rate", "max_keys", "_b")

    def __init__(self, capacity: int, window_seconds: int, max_keys: int = 50_000):
        self.capacity = float(max(1, capacity))
        self.rate = self.capacity / max(1, window_seconds)  # token/sekund
        self.max_keys = max_keys
        self._b: dict[str, list[float]] = {}  # key -> [tokens, last_seen]

    def hit(self, key: str, cost: float = 1.0) -> tuple[bool, int]:
        """(ruxsat, retry_after_seconds) qaytaradi."""
        now = time.monotonic()
        slot = self._b.get(key)
        if slot is None:
            if len(self._b) >= self.max_keys:
                self._prune(now)
            slot = [self.capacity, now]
            self._b[key] = slot

        tokens = min(self.capacity, slot[0] + (now - slot[1]) * self.rate)
        slot[1] = now
        if tokens >= cost:
            slot[0] = tokens - cost
            return True, 0
        slot[0] = tokens
        return False, max(1, int((cost - tokens) / self.rate) + 1)

    def peek(self, key: str, cost: float = 1.0) -> tuple[bool, int]:
        """Token yemasdan tekshirish (login uchun: faqat xato urinish jazolanadi)."""
        slot = self._b.get(key)
        if slot is None:
            return True, 0
        tokens = min(self.capacity, slot[0] + (time.monotonic() - slot[1]) * self.rate)
        if tokens >= cost:
            return True, 0
        return False, max(1, int((cost - tokens) / self.rate) + 1)

    def _prune(self, now: float) -> None:
        """To'lgan (ya'ni faol bo'lmagan) kalitlarni tashlaymiz."""
        full = self.capacity - 1e-9
        drop = [
            k for k, s in self._b.items()
            if min(self.capacity, s[0] + (now - s[1]) * self.rate) >= full
        ]
        for k in drop:
            self._b.pop(k, None)
        if len(self._b) >= self.max_keys:  # hali ham to'la — eng eskilarini tashlaymiz
            for k, _ in sorted(self._b.items(), key=lambda kv: kv[1][1])[: self.max_keys // 4]:
                self._b.pop(k, None)

    def __len__(self) -> int:
        return len(self._b)


class MinInterval:
    """Bitta kalit uchun minimal interval (ikki marta bosishdan himoya)."""

    __slots__ = ("seconds", "max_keys", "_t")

    def __init__(self, seconds: int, max_keys: int = 50_000):
        self.seconds = seconds
        self.max_keys = max_keys
        self._t: dict[str, float] = {}

    def hit(self, key: str) -> tuple[bool, int]:
        if self.seconds <= 0:
            return True, 0
        now = time.monotonic()
        last = self._t.get(key)
        if last is not None and now - last < self.seconds:
            return False, max(1, int(self.seconds - (now - last)) + 1)
        if len(self._t) >= self.max_keys:
            cutoff = now - self.seconds
            for k in [k for k, v in self._t.items() if v < cutoff]:
                self._t.pop(k, None)
        self._t[key] = now
        return True, 0
