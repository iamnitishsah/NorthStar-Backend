from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import config
from app.db.database import db

users = db.users

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            config.JWT_SECRET,
            algorithms=["HS256"]
        )

        employee_id = payload.get("sub")

        if employee_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = await users.find_one({
        "employee_id": employee_id
    })

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    user.pop("hashed_password", None)

    return user
