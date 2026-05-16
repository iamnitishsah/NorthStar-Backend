from datetime import datetime, UTC
from typing import Optional

from pydantic import BaseModel, Field

from app.constants.enums import GoalStatus


class Goal(BaseModel):
    employee_id: str
    employee_name: str
    manager_id: str

    title: str
    description: Optional[str] = None

    weightage: int

    target_date: Optional[datetime] = None

    status: GoalStatus

    manager_note: Optional[str] = None

    approver_id: Optional[str] = None
    approver_name: Optional[str] = None

    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )