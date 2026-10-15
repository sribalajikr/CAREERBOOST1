"""Email delivery for password-reset codes (free-tier friendly).

Works in two modes, chosen automatically by configuration — no code changes:

1. SMTP configured (`SMTP_HOST` + `SMTP_USER` + `SMTP_PASSWORD` in backend/.env)
   → sends a real email through any free provider (Gmail app password, Outlook,
   Brevo, Mailtrap free tier, ...).
2. Nothing configured (the default) → demo mode: no email is sent; the reset
   code is shown on screen so the flow stays usable offline.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("uvicorn.app")


def email_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_reset_code(to_email: str, code: str) -> bool:
    """Email the 6-digit reset code. Returns True when actually sent."""
    if not email_configured():
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your CareerBoost password reset code: {code}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email

    text = (
        "Hi there,\n\n"
        f"Your CareerBoost password reset code is: {code}\n\n"
        "It is valid for 15 minutes. If you didn't request this, "
        "you can safely ignore this email.\n\n"
        "— The CareerBoost Team"
    )
    html = f"""\
<html><body style="margin:0;padding:0;background:#f1f5f9;">
  <div style="max-width:520px;margin:32px auto;background:#ffffff;border-radius:16px;
              overflow:hidden;border:1px solid #e2e8f0;font-family:Segoe UI,Arial,sans-serif;">
    <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px;text-align:center;">
      <h1 style="color:#ffffff;margin:0;font-size:22px;">CareerBoost</h1>
      <p style="color:#e0e7ff;margin:6px 0 0;font-size:13px;">Password reset request</p>
    </div>
    <div style="padding:32px;text-align:center;">
      <p style="color:#334155;font-size:15px;margin:0 0 16px;">
        Use this code to reset your password:</p>
      <div style="font-size:34px;font-weight:800;letter-spacing:10px;color:#4f46e5;
                  background:#eef2ff;border-radius:12px;padding:16px 0;">{code}</div>
      <p style="color:#64748b;font-size:13px;margin:16px 0 0;">
        This code expires in 15 minutes. If you didn't request a reset,
        you can safely ignore this email.</p>
    </div>
  </div>
</body></html>"""
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
        logger.info("Password reset email sent to %s", to_email)
        return True
    except Exception as exc:  # noqa: BLE001 - never crash login flow on SMTP errors
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
        return False
