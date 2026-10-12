import smtplib
from email.message import EmailMessage

from app.config import settings


def send_otp_email(recipient: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Your email verification code"
    message["From"] = settings.email_from
    message["To"] = recipient
    message.set_content(
        f"Your verification code is {otp}.\n\n"
        f"It expires in {settings.otp_expire_seconds // 60} minutes. "
        "If you did not request this code, you can ignore this email."
    )

    if settings.smtp_use_tls:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
