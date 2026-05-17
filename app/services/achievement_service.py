from datetime import datetime, UTC
from bson import ObjectId
from fastapi import HTTPException
from app.constants.enums import GoalStatus
from app.db.database import db
from app.constants.enums import (UOMType, MeasurementType)
from app.audit.logs import log_action

goals = db.goals


async def update_achievement(goal_id: str, achievement_value: float, current_user: dict) -> tuple[bool, str]:
    if not ObjectId.is_valid(goal_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid goal ID"
        )

    goal_data = await goals.find_one({"_id": ObjectId(goal_id)})

    if not goal_data:
        raise HTTPException(
            status_code=404,
            detail="Goal not found"
        )

    if goal_data["employee_id"] != current_user["employee_id"]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update achievement for this goal"
        )

    if goal_data["status"] != GoalStatus.LOCKED:
        raise HTTPException(
            status_code=400,
            detail="Only LOCKED goals can update achievement"
        )

    target_value = goal_data["target_value"]

    measurement_type = goal_data["measurement_type"]

    UoM_type = goal_data["uom_type"]


    if UoM_type in [UOMType.PERCENTAGE, UOMType.NUMERIC]:
        if achievement_value < 0:
            raise HTTPException(
                status_code=400,
                detail="Achievement value must be a positive number for percentage measurement type"
            )
        if measurement_type == MeasurementType.MIN:
            progress_percentage = (achievement_value / target_value) * 100
        elif measurement_type == MeasurementType.MAX:
            if achievement_value==0:
                progress_percentage = 100
            else:
                progress_percentage = (target_value / achievement_value) * 100
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid measurement type for percentage UoM"
            )
    elif UoM_type == UOMType.ZERO_BASED:
        if achievement_value < 0:
            raise HTTPException(
                status_code=400,
                detail="Achievement value must be a positive number for numeric measurement type"
            )
        elif achievement_value == 0:
            progress_percentage = 100
        else:
            progress_percentage = 0
    elif UoM_type == UOMType.TIMELINE:
        # I am assuming that employee will submit the percentage of work completed for timeline goals, so the target value will be 100 and achievement value will be percentage of work completed
        if achievement_value<0:
            raise HTTPException(
                status_code=400,
                detail="Achievement value must be a positive number for timeline measurement type"
            )
        progress_percentage = achievement_value
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid UoM type"
        )
        

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "achievement_value": achievement_value,
                "progress_percentage": progress_percentage,
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="UPDATE_ACHIEVEMENT",
        details={
            "goal_id": goal_id,
            "achievement_value": achievement_value,
            "progress_percentage": progress_percentage
        }
    )

    return True, "Achievement updated successfully"