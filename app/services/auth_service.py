from datetime import datetime
from app.db.database import db
from app.core.security import hash_password, verify_password
from app.models.user_model import User
from app.schemas.auth_schema import RegisterUserRequest, LoginUserRequest
from app.core.auth import create_access_token, create_refresh_token


users = db.users


async def register_user(payload: RegisterUserRequest):
    now = datetime.utcnow()
    email = payload.email.strip().lower()
    await users.create_index("email", unique=True)
    await users.create_index("employee_id", unique=True)

    encrypted = hash_password(payload.password)

    user = User(
    employee_id=payload.employee_id,
    name=payload.name,
    age=payload.age,
    gender=payload.gender,
    phone=payload.phone,
    email=email,
    department=payload.department,
    designation=payload.designation,
    role=payload.role,
    manager_id=payload.manager_id,
    hashed_password=encrypted,
    created_on=now,
)

    try:
        user = await users.insert_one(user.model_dump())
        return True, str(user.inserted_id)
    except Exception as e:
        return False, str(e)


async def login_user(payload: LoginUserRequest):
    now = datetime.utcnow()

    email = payload.email.strip().lower()
    employee_id = payload.employee_id.strip() if payload.employee_id else None
    password = payload.password

    if employee_id:
        user = await users.find_one({"employee_id": employee_id})
    else:
        user = await users.find_one({"email": email})

    if not user:
        return False, {"message": "User does not exist"}

    if not verify_password(password, user["hashed_password"]):
        return False, {"message": "Incorrect password"}

    user_id = user["_id"]

    access = create_access_token(
        employee_id=user["employee_id"],
        role=user["role"],
        designation=user["designation"],
        department=user["department"]
    )
    refresh = create_refresh_token(str(user["employee_id"]))

    await users.update_one(
        {"_id": user_id},
        {"$set": {
            "last_login": now,
        }}
    )

    user.pop("hashed_password", None)
    user["_id"] = str(user["_id"])

    response = {
        "user_id": user["_id"],
        "access": access,
        "refresh": refresh,
        "user": user
    }

    return True, response