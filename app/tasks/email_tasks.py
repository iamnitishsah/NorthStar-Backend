import smtplib
from email.message import EmailMessage
from app.core.celery_app import celery_app
from app.core.config import config


@celery_app.task(name="email.send")
def send_email(to_email: str, subject: str, body: str) -> bool:
    if not to_email:
        return False

    message = EmailMessage()
    message["From"] = config.EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        if config.SMTP_USE_TLS:
            smtp.starttls()
        if config.SMTP_USERNAME and config.SMTP_PASSWORD:
            smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        smtp.send_message(message)

    return True
