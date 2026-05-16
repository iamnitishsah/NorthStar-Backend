from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.constants.enums import Gender, Role


class User(BaseModel):
    employee_id: str
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=18, le=80)
    gender: Gender
    phone: str
    email: EmailStr
    department: str
    designation: str
    role: Role
    manager_id: Optional[str] = None
    hashed_password: str
    is_active: bool = True