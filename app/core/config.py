import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()


class Settings:
    GATEWAY_PORT: int = int(os.getenv("GATEWAY_PORT", 8000))
    JWT_SECRET: str = "NorthStarSecretKey"
    JWT_REFRESH_SECRET: str = "NorthStarRefreshSecretKey"
    ACCESS_TOKEN_EXPIRE= timedelta(minutes=60)
    REFRESH_TOKEN_EXPIRE= timedelta(days=7)
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))


config = Settings()