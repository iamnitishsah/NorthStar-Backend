from datetime import datetime
from jose import jwt
from app.core.config import config


def create_access_token(user_id: str):
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        # "role": role,
        "iat": now,
        "exp": now + config.ACCESS_TOKEN_EXPIRE,
    }

    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def create_refresh_token(user_id: str):
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + config.REFRESH_TOKEN_EXPIRE,
    }

    return jwt.encode(payload, config.JWT_REFRESH_SECRET, algorithm="HS256")