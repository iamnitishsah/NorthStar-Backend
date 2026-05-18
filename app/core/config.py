import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()


class Settings:
    GATEWAY_PORT: int = int(os.getenv("GATEWAY_PORT", 8000))
    JWT_SECRET: str = os.getenv("JWT_SECRET", "NorthStarSecretKey")
    JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "NorthStarRefreshSecretKey")
    ACCESS_TOKEN_EXPIRE= timedelta(minutes=60)
    REFRESH_TOKEN_EXPIRE= timedelta(days=7)
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://red-d859iv6k1jcs73ffqvgg:6379")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", f"redis://{REDIS_HOST}:{REDIS_PORT}/1")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "northstar@example.com")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "northstar@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "dummy-app-password")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


config = Settings()
