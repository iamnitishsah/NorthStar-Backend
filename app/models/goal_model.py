from datetime import datetime, UTC
from typing import Any, Optional, Dict, Union
from pydantic import BaseModel, Field, validator
from app.constants.enums import (
    GoalStatus,
    UOMType,
    MeasurementType,
    ProgressStatus
)


class CheckinParams(BaseModel):
    achievement_value: Union[float, str]
    progress_status: ProgressStatus
    manager_note: Optional[str] = None

    @validator("achievement_value")
    def validate_achievement_value(cls, value):
        if isinstance(value, (int, float)) and value < 0:
            raise ValueError("achievement_value must be >= 0")
        return value

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
    source_goal_id: Optional[Any] = None
    source_snapshot: Optional[Dict[str, Any]] = None
    primary_owner_id: Optional[str] = None
    primary_owner_name: Optional[str] = None
    achievement_value: Optional[Union[float, str]] = None
    progress_percentage: Optional[float] = None
    progress_status: Optional[ProgressStatus] = None
    quarter: Dict[str, CheckinParams] = Field(default_factory=dict)
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
