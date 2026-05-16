from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.constants.enums import GoalStatus


class ViewGoalResponse(BaseModel):
    goal_id: str
    employee_name: str
    title: str
    description: Optional[str]
    weightage: int
    target_date: Optional[datetime]
    status: GoalStatus
    manager_note: Optional[str]
    approver_name: Optional[str]
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    returned_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CreateGoalRequest(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    weightage: int = Field(ge=10, le=100)
    target_date: Optional[datetime]


class UpdateGoalRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    weightage: Optional[int] = None
    target_date: Optional[datetime] = None


class ReturnGoalRequest(BaseModel):
    manager_note: Optional[str] = None