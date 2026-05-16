from datetime import datetime, UTC

from bson import ObjectId
from fastapi import HTTPException

from app.constants.enums import GoalStatus
from app.db.database import db

goals = db.goals


async def update_achievement(goal_id: str, achievement_value: float, current_user: dict) -> tuple[bool, str]:

    if not ObjectId.is_valid(goal_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid goal ID"
        )

    goal_data = await goals.find_one(
        {"_id": ObjectId(goal_id)}
    )

    if not goal_data:
        raise HTTPException(
            status_code=404,
            detail="Goal not found"
        )

    if goal_data["employee_id"] != current_user["employee_id"]:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized"
        )

    if goal_data["status"] != GoalStatus.LOCKED:
        raise HTTPException(
            status_code=400,
            detail="Only LOCKED goals can update achievement"
        )

    target_value = goal_data["target_value"]

    progress_percentage = round(
        (achievement_value / target_value) * 100,
        2
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

    return True, "Achievement updated successfully"