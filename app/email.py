"""SMTP orqali email yuborish (parol tiklash / email tasdiqlash uchun).

smtplib bloklovchi (sync) kutubxona — shuning uchun asyncio.to_thread orqali
alohida oqimda ishga tushiriladi, event loop'ni to'xtatib qo'ymaydi.
"""
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from .config import settings

log = logging.getLogger("promtchi.email")

FROM_NAME = "promtchi"


def _send_sync(to: str, subject: str, html: str) -> None:
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr((FROM_NAME, settings.SMTP_FROM))
    msg["To"] = to
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, [to], msg.as_string())


async def send_email(to: str, subject: str, html: str) -> bool:
    """True — muvaffaqiyatli yuborildi. SMTP sozlanmagan bo'lsa jim False qaytaradi."""
    if not (settings.SMTP_USER and settings.SMTP_PASSWORD and to):
        log.warning("SMTP sozlanmagan yoki qabul qiluvchi yo'q — email yuborilmadi (to=%s)", to)
        return False
    try:
        await asyncio.to_thread(_send_sync, to, subject, html)
        return True
    except Exception:
        log.exception("Email yuborishda xato — to=%s", to)
        return False


# ══════════ HTML shablon (jadval asosida — email mijozlarida eng ishonchli) ══════════

def _template(title: str, body_html: str, button_url: str, button_text: str) -> str:
    logo = f"{settings.SITE_URL}/static/logo.png"
    return f"""\
<!DOCTYPE html>
<html lang="uz"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0B0B0E">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0B0B0E;padding:40px 16px">
<tr><td align="center">
<table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%">
  <tr><td align="center" style="padding-bottom:28px">
    <img src="{logo}" width="56" height="56" alt="promtchi" style="border-radius:14px;display:block">
  </td></tr>
  <tr><td style="background:#F3EFE6;border-radius:20px;padding:40px 32px;font-family:Arial,Helvetica,sans-serif">
    <div style="font-weight:900;font-size:12px;letter-spacing:.25em;text-transform:uppercase;color:#FF4B2E;margin-bottom:14px">
      promtchi&reg;
    </div>
    <h1 style="font-size:22px;line-height:1.35;margin:0 0 16px;color:#0B0B0E">{title}</h1>
    <div style="font-size:15px;line-height:1.65;color:#2b2b2e">{body_html}</div>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:30px auto 0">
      <tr><td align="center" style="border-radius:999px;background:#0B0B0E">
        <a href="{button_url}" style="display:inline-block;padding:16px 38px;font-family:Arial,Helvetica,sans-serif;
          font-weight:700;font-size:15px;color:#D9FF3F;text-decoration:none;border-radius:999px">{button_text}</a>
      </td></tr>
    </table>
    <p style="font-size:12px;line-height:1.6;color:rgba(11,11,14,.5);margin:30px 0 0;text-align:center">
      Havola 30 daqiqa amal qiladi.<br>Agar bu so'rovni siz yubormagan bo'lsangiz, shunchaki e'tiborsiz qoldiring.
    </p>
  </td></tr>
  <tr><td align="center" style="padding-top:24px;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:rgba(255,255,255,.35)">
    &copy; 2026 promtchi&reg; &middot; jamolxon.uz
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def reset_password_email(url: str) -> str:
    body = "Admin panel paroli tiklashni so'radingiz. Quyidagi tugma orqali yangi parol o'rnating."
    return _template("Parolni tiklash", body, url, "Yangi parol o'rnatish")


def confirm_email_email(url: str, target_email: str, action: str) -> str:
    """action — "qo'shish" | "o'chirish"."""
    verb = "qo'shishni" if action == "qo'shish" else "o'chirishni"
    body = (
        f"Admin panel uchun <b>{target_email}</b> emailini {verb} so'ralmoqda. Bu — faqat "
        "ASOSIY admin sifatida sizga yuborilgan so'rov. Tasdiqlash uchun quyidagi tugmani bosing."
    )
    title = "Email qo'shishni tasdiqlash" if action == "qo'shish" else "Email o'chirishni tasdiqlash"
    return _template(title, body, url, "Tasdiqlash")


def set_primary_email(url: str, new_primary_email: str) -> str:
    body = (
        f"<b>{new_primary_email}</b>ni yangi ASOSIY admin qilib tayinlash so'ralmoqda. "
        "Bu — asosiy admin huquqini (email qo'shish/o'chirishni tasdiqlash) shu hisobga "
        "o'tkazadi. Tasdiqlash uchun quyidagi tugmani bosing."
    )
    return _template("Asosiy adminni almashtirish", body, url, "Tasdiqlash")


def new_account_email(url: str) -> str:
    body = (
        "Sizga promtchi admin panelida hisob ochildi. Ishni boshlash uchun quyidagi tugma orqali "
        "o'z parolingizni o'rnating."
    )
    return _template("Hisobingiz yaratildi", body, url, "Parol o'rnatish")
