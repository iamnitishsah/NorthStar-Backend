from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field
from app.constants.enums import GoalStatus, MeasurementType, ProgressStatus, UOMType


class ViewGoalResponse(BaseModel):
    goal_id: str
    thrust_area: str
    uom_type: UOMType
    measurement_type: MeasurementType
    target_value: float
    achievement_value: Optional[float] = None
    progress_status: Optional[ProgressStatus] = None
    progress_percentage: Optional[float] = None
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


class CheckinParams(BaseModel):
    achievement_value: Optional[float] = Field(ge=0)
    progress_status: ProgressStatus 


class QuarterlyCheckinRequest(BaseModel):
    quarter: Dict[str, CheckinParams]