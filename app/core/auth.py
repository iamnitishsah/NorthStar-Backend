from datetime import datetime, UTC
from jose import jwt
from app.core.config import config


def create_access_token(employee_id: str, role: str, designation: str, department: str):
    now = datetime.now(UTC)
    payload = {
        "sub": str(employee_id),
        "role": role,
        "designation": designation,
        "department": department,
        "iat": now,
        "exp": now + config.ACCESS_TOKEN_EXPIRE,
    }

    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def create_refresh_token(employee_id: str):
    now = datetime.now(UTC)
    payload = {
        "sub": str(employee_id),
        "iat": now,
        "exp": now + config.REFRESH_TOKEN_EXPIRE,
    }

    return jwt.encode(payload, config.JWT_REFRESH_SECRET, algorithm="HS256")