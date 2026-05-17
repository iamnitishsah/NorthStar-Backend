from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from app.constants.enums import Gender, Role



class RegisterUserRequest(BaseModel):
    email: EmailStr
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
    password: str

class LoginUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    employee_id: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def validate_login_identifier(self):

        if not self.email and not self.employee_id:
            raise ValueError(
                "Either email or employee_id is required"
            )

        return self