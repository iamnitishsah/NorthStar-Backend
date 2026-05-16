from datetime import datetime, UTC
from typing import Optional

from pydantic import BaseModel, Field

from app.constants.enums import (
    GoalStatus,
    UOMType,
    MeasurementType
)


class Goal(BaseModel):
    employee_id: str
    employee_name: str
    manager_id: str
    thrust_area: str
    title: str
    description: Optional[str] = None
    uom_type: UOMType
    measurement_type: MeasurementType
    target_value: float
    weightage: int
    target_date: Optional[datetime] = None
    status: GoalStatus
    manager_note: Optional[str] = None
    approver_id: Optional[str] = None
    approver_name: Optional[str] = None
    is_shared: bool = False
    primary_owner_id: Optional[str] = None
    achievement_value: Optional[float] = None
    progress_percentage: Optional[float] = None

    # timestamps
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )