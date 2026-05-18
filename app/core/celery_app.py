from celery import Celery
from app.core.config import config

celery_app = Celery(
    "NorthStar",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
    include=["app.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
