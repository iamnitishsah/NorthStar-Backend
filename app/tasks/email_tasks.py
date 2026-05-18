import smtplib
from email.message import EmailMessage
from loguru import logger
from app.core.celery_app import celery_app
from app.core.config import config


@celery_app.task(name="email.send", bind=True, autoretry_for=(smtplib.SMTPException, OSError), retry_kwargs={"max_retries": 3, "countdown": 60})
def send_email(self, to_email: str, subject: str, body: str, event_type: str, metadata: dict | None = None) -> bool:
    task_id = self.request.id

    log_context = {
        "task_id": task_id,
        "event_type": event_type,
        "to_email": to_email,
        "subject": subject,
        **(metadata or {}),
    }

    if not to_email:
        logger.warning(
            "Email skipped: missing recipient email | {}",
            log_context,
        )
        return False

    message = EmailMessage()
    message["From"] = config.EMAIL_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    logger.info(
        "Email sending started | {}",
        log_context,
    )

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:

            if config.SMTP_USE_TLS:
                smtp.starttls()

            if config.SMTP_USERNAME and config.SMTP_PASSWORD:
                smtp.login(
                    config.SMTP_USERNAME,
                    config.SMTP_PASSWORD,
                )

            smtp.send_message(message)

    except Exception as exc:
        logger.exception(
            "Email sending failed | error={} | context={}",
            str(exc),
            log_context,
        )
        raise

    logger.success(
        "Email sent successfully | {}",
        log_context,
    )

    return True