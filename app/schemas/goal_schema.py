from datetime import datetime
from typing import Any, Optional, Dict, Union
from pydantic import BaseModel, Field, validator
from app.constants.enums import GoalStatus, MeasurementType, ProgressStatus, UOMType


class ViewGoalResponse(BaseModel):
    goal_id: str
    thrust_area: str
    uom_type: UOMType
    measurement_type: MeasurementType
    target_value: float
    achievement_value: Optional[Union[float, str]] = None
    progress_status: Optional[ProgressStatus] = None
    progress_percentage: Optional[float] = None
    quarter: Dict[str, Any] = {}
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
    thrust_area: str = Field(min_length=3, max_length=100)
    title: str = Field(min_length=3, max_length=100)
    description: Optional[str] = Field(
        default=None,
        max_length=500
    )
    progress_status: Optional[ProgressStatus] = ProgressStatus.NOT_STARTED
    uom_type: UOMType
    measurement_type: MeasurementType
    target_value: float = Field(gt=0)
    weightage: int = Field(ge=10, le=100)
    target_date: Optional[datetime]


class UpdateGoalRequest(BaseModel):
    thrust_area: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    uom_type: Optional[UOMType] = None
    measurement_type: Optional[MeasurementType] = None
    target_value: Optional[float] = None
    weightage: Optional[int] = None
    target_date: Optional[datetime] = None


class ReturnGoalRequest(BaseModel):
    manager_note: Optional[str] = None


class ApproveGoalRequest(BaseModel):
    target_value: Optional[float] = Field(default=None, gt=0)
    weightage: Optional[int] = Field(default=None, ge=10, le=100)


class CommentGoalRequest(BaseModel):
    quarter: int
    comment: str


class CheckinParams(BaseModel):
    achievement_value: Optional[Union[float, str]] = None
    progress_status: ProgressStatus

    @validator("achievement_value")
    def validate_achievement_value(cls, value):
        if value is None:
            return value
        if isinstance(value, (int, float)) and value < 0:
            raise ValueError("achievement_value must be >= 0")
        return value


class QuarterlyCheckinRequest(BaseModel):
    quarter: Dict[str, CheckinParams]


class UnlockGoalRequestCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class UnlockGoalRequestDecision(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class UnlockGoalRequestResponse(BaseModel):
    request_id: str
    goal_id: str
    goal_title: str
    requester_id: str
    requester_name: str
    manager_id: Optional[str]
    manager_name: Optional[str]
    reason: str
    status: str
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
