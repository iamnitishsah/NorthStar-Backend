from datetime import datetime, UTC
from bson import ObjectId
from fastapi import HTTPException
from app.constants.enums import GoalStatus
from app.db.database import db
from app.audit.logs import log_action

goals = db.goals
logs = db.logs


async def unlock_goal(goal_id: str, current_user: dict) -> tuple[bool, str]:
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

    if goal_data["status"] != GoalStatus.LOCKED:
        raise HTTPException(
            status_code=400,
            detail="Only LOCKED goals can be unlocked"
        )

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "status": GoalStatus.RETURNED,
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(
        user_id=current_user["_id"],
        action="UNLOCK_GOAL",
        details={
            "goal_id": goal_id,
            "previous_status": GoalStatus.LOCKED,
            "new_status": GoalStatus.RETURNED
        }
    )

    return True, "Goal unlocked successfully"


async def view_logs(action_filter: str = None, user_id_filter: str = None) -> list[dict]:
    query = {}
    if action_filter:
        query["action"] = action_filter
    if user_id_filter:
        query["user_id"] = ObjectId(user_id_filter)

    logs_cursor = logs.find(query).sort("timestamp", -1).limit(100)
    logs_list = []
    async for log in logs_cursor:
        log["_id"] = str(log["_id"])
        log["user_id"] = str(log["user_id"])
        logs_list.append(log)
    return logs_list