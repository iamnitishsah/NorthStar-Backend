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
from app.services.notification_service import (
    notify_goal_approved,
    notify_goal_returned,
)

goals = db.goals
users = db.users


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
            progress_status=data.get("progress_status"),
            quarter=data.get("quarter", {}),

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


async def approve_goal(goal_id: str, tweaks: dict | None, current_user: dict) -> tuple[bool, str]:

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
    
    target_value = goal_data["target_value"]
    weightage = goal_data["weightage"]
    if tweaks is not None:
        if "target_value" in tweaks and tweaks["target_value"] is not None:
            target_value = tweaks["target_value"]
        if "weightage" in tweaks and tweaks["weightage"] is not None:
            weightage = tweaks["weightage"]

    if weightage < 10 or weightage > 100:
        raise HTTPException(
            status_code=400,
            detail="Weightage must be between 10 and 100"
        )

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "status": GoalStatus.LOCKED,
                "target_value": target_value,
                "weightage": weightage,

                "manager_note": None,

                "approver_id": current_user["employee_id"],
                "approver_name": current_user["name"],

                "approved_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="APPROVE_GOAL",
        details={
            "goal_id": goal_id,
            "employee_id": goal_data["employee_id"],
            "employee_name": goal_data["employee_name"]
        }
    )

    employee = await users.find_one(
        {"employee_id": goal_data["employee_id"]},
        {"email": 1}
    )
    notify_goal_approved(
        employee_email=employee.get("email") if employee else None,
        goal_title=goal_data.get("title"),
        manager_name=current_user.get("name"),
    )

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

    await log_action(
        user_id=current_user["employee_id"],
        action="RETURN_GOAL",
        details={
            "goal_id": goal_id,
            "employee_id": goal_data["employee_id"],
            "employee_name": goal_data["employee_name"],
            "manager_note": payload.manager_note
        }
    )

    employee = await users.find_one(
        {"employee_id": goal_data["employee_id"]},
        {"email": 1}
    )
    notify_goal_returned(
        employee_email=employee.get("email") if employee else None,
        goal_title=goal_data.get("title"),
        manager_name=current_user.get("name"),
        manager_note=payload.manager_note,
    )

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
            progress_status=data.get("progress_status"),
            quarter=data.get("quarter", {}),

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


async def checkin_review(current_user: dict) -> dict[str, list[dict]]:
    manager_id = current_user["employee_id"]

    goal_data = goals.find(
        {"manager_id": manager_id, "status": GoalStatus.LOCKED}
    ).sort([("employee_name", 1), ("created_at", -1)])

    grouped_review = defaultdict(list)

    async for data in goal_data:
        quarter = data.get("quarter") or {}
        quarters = {}

        for quarter_number in range(1, 5):
            quarter_data = quarter.get(str(quarter_number)) or {}
            quarters[f"q{quarter_number}"] = {
                "achievement_value": quarter_data.get("achievement_value"),
                "progress_percentage": quarter_data.get("progress_percentage"),
                "progress_status": quarter_data.get("progress_status"),
                "manager_note": quarter_data.get("manager_note"),
                "updated_at": quarter_data.get("updated_at"),
                "completed": bool(quarter_data),
            }

        grouped_review[data["employee_name"]].append(
            {
                "goal_id": str(data["_id"]),
                "employee_id": data.get("employee_id"),
                "employee_name": data.get("employee_name"),
                "title": data.get("title"),
                "thrust_area": data.get("thrust_area"),
                "uom_type": data.get("uom_type"),
                "measurement_type": data.get("measurement_type"),
                "planned_target_value": data.get("target_value"),
                "latest_achievement_value": data.get("achievement_value"),
                "latest_progress_percentage": data.get("progress_percentage"),
                "latest_progress_status": data.get("progress_status"),
                "weightage": data.get("weightage"),
                "target_date": data.get("target_date"),
                "quarters": quarters,
            }
        )

    return dict(grouped_review)


async def comment_on_goal(goal_id: str, quarter: int, comment: str, current_user: dict) -> tuple[bool, str]:
    if not ObjectId.is_valid(goal_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid goal ID"
        )


    if quarter not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=400,
            detail="Invalid quarter"
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
            detail="Unauthorized to comment on this goal"
        )

    quarter_data = goal_data.get("quarter", {})

    if str(quarter) not in quarter_data:
        raise HTTPException(
            status_code=400,
            detail=f"Q{quarter} check-in not found"
        )


    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                f"quarter.{quarter}.manager_note": comment,
                "updated_at": datetime.now(UTC)
            }
        }
    )


    await log_action(
        user_id=current_user["employee_id"],
        action="COMMENT_ON_GOAL",
        details={
            "goal_id": goal_id,
            "quarter": quarter,
            "employee_id": goal_data["employee_id"],
            "employee_name": goal_data["employee_name"],
            "comment": comment
        }
    )

    return True, f"Comment added for Q{quarter}"
