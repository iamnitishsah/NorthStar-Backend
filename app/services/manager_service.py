from collections import defaultdict
from datetime import datetime, UTC
from typing import List
from bson import ObjectId
from fastapi import HTTPException
from app.constants.enums import GoalStatus
from app.db.database import db
from app.schemas.goal_schema import (
    ReturnGoalRequest,
    ViewGoalResponse
)
from app.audit.logs import log_action

goals = db.goals


async def review_goals(current_user: dict) -> dict[str, List[ViewGoalResponse]]:
    manager_id = current_user["employee_id"]

    goal_data = goals.find({"manager_id": manager_id, "status": GoalStatus.SUBMITTED}).sort("created_at", -1)

    grouped_goals = defaultdict(list)

    async for data in goal_data:

        goal = ViewGoalResponse(
            goal_id=str(data["_id"]),

            employee_name=data["employee_name"],

            thrust_area=data["thrust_area"],

            title=data["title"],
            description=data.get("description"),

            uom_type=data["uom_type"],
            measurement_type=data["measurement_type"],

            target_value=data["target_value"],

            weightage=data["weightage"],

            target_date=data.get("target_date"),

            achievement_value=data.get("achievement_value"),
            progress_percentage=data.get("progress_percentage"),

            status=data["status"],

            manager_note=data.get("manager_note"),

            approver_name=data.get("approver_name"),

            submitted_at=data.get("submitted_at"),
            approved_at=data.get("approved_at"),
            returned_at=data.get("returned_at"),

            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )

        grouped_goals[data["employee_name"]].append(goal)

    return dict(grouped_goals)


async def approve_goal(goal_id: str, current_user: dict) -> tuple[bool, str]:

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

    if goal_data["manager_id"] != current_user["employee_id"]:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to approve this goal"
        )

    if goal_data["status"] != GoalStatus.SUBMITTED:
        raise HTTPException(
            status_code=400,
            detail="Only SUBMITTED goals can be approved"
        )

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "status": GoalStatus.LOCKED,

                "manager_note": None,

                "approver_id": current_user["employee_id"],
                "approver_name": current_user["name"],

                "approved_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(current_user["employee_id"], "APPROVE_GOAL", f"Goal approved with ID: {goal_id}")

    return True, "Goal approved successfully"


async def return_goal(goal_id: str, payload: ReturnGoalRequest, current_user: dict) -> tuple[bool, str]:
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

    if goal_data["manager_id"] != current_user["employee_id"]:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to return this goal"
        )

    if goal_data["status"] != GoalStatus.SUBMITTED:
        raise HTTPException(
            status_code=400,
            detail="Only SUBMITTED goals can be returned"
        )

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "status": GoalStatus.RETURNED,

                "manager_note": payload.manager_note,

                "returned_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(current_user["employee_id"], "RETURN_GOAL", f"Goal returned with ID: {goal_id}")

    return True, "Goal returned successfully"



async def view_goals(current_user: dict) -> dict[str, List[ViewGoalResponse]]:
    manager_id = current_user["employee_id"]

    goal_data = goals.find(
        {"manager_id": manager_id, "status": GoalStatus.LOCKED}
    ).sort("created_at", -1)

    grouped_goals = defaultdict(list)

    async for data in goal_data:

        goal = ViewGoalResponse(
            goal_id=str(data["_id"]),

            employee_name=data["employee_name"],

            thrust_area=data["thrust_area"],

            title=data["title"],
            description=data.get("description"),

            uom_type=data["uom_type"],
            measurement_type=data["measurement_type"],

            target_value=data["target_value"],

            weightage=data["weightage"],

            target_date=data.get("target_date"),

            achievement_value=data.get("achievement_value"),
            progress_percentage=data.get("progress_percentage"),

            status=data["status"],

            manager_note=data.get("manager_note"),

            approver_name=data.get("approver_name"),

            submitted_at=data.get("submitted_at"),
            approved_at=data.get("approved_at"),
            returned_at=data.get("returned_at"),

            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )

        grouped_goals[data["employee_name"]].append(goal)

    return dict(grouped_goals)



async def comment_on_goal(goal_id: str, comment: str, current_user: dict) -> tuple[bool, str]:
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

    if goal_data["manager_id"] != current_user["employee_id"]:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to comment on this goal"
        )

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "manager_note": comment,
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(current_user["employee_id"], "COMMENT_ON_GOAL", f"Comment added to goal with ID: {goal_id}")

    return True, "Comment added successfully"