"""Free email alerts using any SMTP account (for example Gmail with an app password).
If SMTP_USER is not set, alerts are skipped, so the app works without email."""
import smtplib
from email.message import EmailMessage

from ..config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_user or not to:
        return False
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError):
        return False  # never block escalation because email failed
