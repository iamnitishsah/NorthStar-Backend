from fastapi import APIRouter, HTTPException
from app.schemas.auth_schema import RegisterUserRequest, LoginUserRequest
from app.services.auth_service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["Authentication APIs"])


@router.post("/register")
async def registration(payload: RegisterUserRequest):
    status, response = await register_user(payload)
    if not status:
        raise HTTPException(status_code=400, detail=response)
    return {"message": "User Registered Successfully", "user_id": response}


@router.post("/login")
async def login(payload: LoginUserRequest):
    status, response = await login_user(payload)
    if not status:
        raise HTTPException(status_code=400, detail=response)
    return {"message": "Login Successfully", "response": response}