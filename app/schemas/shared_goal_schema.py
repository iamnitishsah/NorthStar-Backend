from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.constants.enums import GoalStatus, MeasurementType, ProgressStatus, UOMType



class PushSharedGoalRequest(BaseModel):
    recipient_employee_ids: List[str] = Field(
        min_length=1,
        description="List of employee_ids who will receive this shared goal"
    )
    thrust_area: str = Field(min_length=3, max_length=100)
    title: str = Field(min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    uom_type: UOMType
    measurement_type: MeasurementType
    target_value: float = Field(gt=0)
    default_weightage: int = Field(ge=10, le=100, description="Starting weightage for all recipients")
    target_date: Optional[datetime] = None


class UpdateSharedGoalWeightageRequest(BaseModel):
    weightage: int = Field(ge=10, le=100)



class SharedGoalResponse(BaseModel):
    goal_id: str
    source_goal_id: str
    thrust_area: str
    title: str
    description: Optional[str]
    uom_type: UOMType
    measurement_type: MeasurementType
    target_value: float
    weightage: int
    target_date: Optional[datetime]
    employee_name: str
    primary_owner_id: str
    is_shared: bool
    achievement_value: Optional[float] = None
    progress_percentage: Optional[float] = None
    progress_status: Optional[ProgressStatus] = None
    status: GoalStatus
    approver_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime