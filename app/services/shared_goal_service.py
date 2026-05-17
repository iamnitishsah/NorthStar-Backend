from datetime import datetime, UTC
from typing import List
from bson import ObjectId
from fastapi import HTTPException

from app.constants.enums import GoalStatus, ProgressStatus
from app.db.database import db
from app.audit.logs import log_action
from app.schemas.shared_goal_schema import (
    PushSharedGoalRequest,
    UpdateSharedGoalWeightageRequest,
    SharedGoalResponse,
)

goals = db.goals
users = db.users



def _build_shared_response(data: dict) -> SharedGoalResponse:
    return SharedGoalResponse(
        goal_id=str(data["_id"]),
        source_goal_id=str(data["source_goal_id"]),
        thrust_area=data["thrust_area"],
        title=data["title"],
        description=data.get("description"),
        uom_type=data["uom_type"],
        measurement_type=data["measurement_type"],
        target_value=data["target_value"],
        weightage=data["weightage"],
        target_date=data.get("target_date"),
        employee_name=data["employee_name"],
        primary_owner_id=data["primary_owner_id"],
        is_shared=data["is_shared"],
        achievement_value=data.get("achievement_value"),
        progress_percentage=data.get("progress_percentage"),
        progress_status=data.get("progress_status"),
        status=data["status"],
        approver_name=data.get("approver_name"),
        submitted_at=data.get("submitted_at"),
        approved_at=data.get("approved_at"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )



async def push_shared_goal(payload: PushSharedGoalRequest, current_user: dict) -> tuple[bool, dict]:
    now = datetime.now(UTC)
    pusher_id = current_user["employee_id"]
    pusher_name = current_user["name"]

    recipient_ids = list(set(payload.recipient_employee_ids))

    recipient_docs = await users.find(
        {
            "employee_id": {"$in": recipient_ids},
            "is_active": True,
            "role": "EMPLOYEE",
        },
        {"employee_id": 1, "name": 1, "manager_id": 1},
    ).to_list(length=None)

    found_ids = {r["employee_id"] for r in recipient_docs}
    missing = set(recipient_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"These employee IDs were not found or are not active employees: {sorted(missing)}",
        )

    status_filter = {
        "$in": [
            GoalStatus.DRAFT,
            GoalStatus.RETURNED,
            GoalStatus.ADMIN_UNLOCKED,
            GoalStatus.SUBMITTED,
            GoalStatus.LOCKED,
        ]
    }
    existing_goals = await goals.find(
        {
            "employee_id": {"$in": recipient_ids},
            "status": status_filter,
        },
        {"employee_id": 1, "weightage": 1},
    ).to_list(length=None)

    weightage_by_employee: dict[str, int] = {}
    for goal in existing_goals:
        employee_id = goal["employee_id"]
        weightage_by_employee[employee_id] = (
            weightage_by_employee.get(employee_id, 0) + goal.get("weightage", 0)
        )

    count_by_employee: dict[str, int] = {}
    for goal in existing_goals:
        employee_id = goal["employee_id"]
        count_by_employee[employee_id] = count_by_employee.get(employee_id, 0) + 1

    over_limit = []
    for recipient in recipient_docs:
        employee_id = recipient["employee_id"]
        current_count = count_by_employee.get(employee_id, 0)
        if current_count >= 8:
            over_limit.append(
                {
                    "employee_id": employee_id,
                    "current_count": current_count,
                    "limit": 8,
                }
            )

    if over_limit:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Maximum 8 goals allowed per employee",
                "over_limit_recipients": over_limit,
            },
        )

    source_goal_id = ObjectId()
    docs_to_insert = []

    for recipient in recipient_docs:
        doc = {
            "_id": ObjectId(),
            "source_goal_id": source_goal_id,
            "employee_id": recipient["employee_id"],
            "employee_name": recipient["name"],
            "manager_id": recipient.get("manager_id"),
            "thrust_area": payload.thrust_area,
            "title": payload.title,
            "description": payload.description,
            "uom_type": payload.uom_type,
            "measurement_type": payload.measurement_type,
            "target_value": payload.target_value,
            "weightage": payload.default_weightage,
            "target_date": payload.target_date,
            "source_snapshot": {
                "thrust_area": payload.thrust_area,
                "title": payload.title,
                "description": payload.description,
                "uom_type": payload.uom_type,
                "measurement_type": payload.measurement_type,
                "target_value": payload.target_value,
                "target_date": payload.target_date,
            },
            "status": GoalStatus.DRAFT,
            "progress_status": ProgressStatus.NOT_STARTED,
            "is_shared": True,
            "primary_owner_id": pusher_id,
            "primary_owner_name": pusher_name,
            "manager_note": None,
            "approver_id": None,
            "approver_name": None,
            "achievement_value": None,
            "progress_percentage": None,
            "quarter": {},
            "submitted_at": None,
            "approved_at": None,
            "returned_at": None,
            "created_at": now,
            "updated_at": now,
        }
        docs_to_insert.append(doc)

    if not docs_to_insert:
        raise HTTPException(status_code=400, detail="No valid recipients found")

    await goals.insert_many(docs_to_insert)

    await log_action(
        user_id=pusher_id,
        action="PUSH_SHARED_GOAL",
        details={
            "source_goal_id": str(source_goal_id),
            "title": payload.title,
            "thrust_area": payload.thrust_area,
            "recipients": recipient_ids,
            "count": len(docs_to_insert),
        },
    )

    return True, {
        "message": f"Shared goal pushed to {len(docs_to_insert)} employee(s)",
        "source_goal_id": str(source_goal_id),
        "recipient_count": len(docs_to_insert),
        "recipients": [r["employee_id"] for r in recipient_docs],
    }



async def my_shared_goals(current_user: dict) -> List[SharedGoalResponse]:
    """Returns all shared goal copies assigned to the current employee."""
    employee_id = current_user["employee_id"]

    cursor = goals.find(
        {"employee_id": employee_id, "is_shared": True}
    ).sort("created_at", -1)

    result = []
    async for data in cursor:
        result.append(_build_shared_response(data))

    return result



async def update_shared_goal_weightage(goal_id: str, payload: UpdateSharedGoalWeightageRequest, current_user: dict) -> tuple[bool, str]:
    if not ObjectId.is_valid(goal_id):
        raise HTTPException(status_code=400, detail="Invalid goal ID")

    goal_data = await goals.find_one({"_id": ObjectId(goal_id)})

    if not goal_data:
        raise HTTPException(status_code=404, detail="Goal not found")

    if not goal_data.get("is_shared"):
        raise HTTPException(
            status_code=400, detail="This endpoint is only for shared goals"
        )

    if goal_data["employee_id"] != current_user["employee_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if goal_data["status"] not in [
        GoalStatus.DRAFT,
        GoalStatus.RETURNED,
        GoalStatus.ADMIN_UNLOCKED,
    ]:
        raise HTTPException(
            status_code=400,
            detail="Weightage can only be changed while the goal is DRAFT, RETURNED, or ADMIN_UNLOCKED",
        )

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "weightage": payload.weightage,
                "updated_at": datetime.now(UTC),
            }
        },
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="UPDATE_SHARED_GOAL_WEIGHTAGE",
        details={"goal_id": goal_id, "new_weightage": payload.weightage},
    )

    return True, "Weightage updated successfully"



async def sync_shared_achievement(source_goal_id: str, achievement_value: float, progress_percentage: float, quarterly_data: dict, exclude_employee_id: str,) -> int:
    now = datetime.now(UTC)
    set_fields = {
        "achievement_value": achievement_value,
        "progress_percentage": progress_percentage,
        "updated_at": now,
        **{f"quarter.{key}": value for key, value in quarterly_data.items()},
    }

    result = await goals.update_many(
        {
            "source_goal_id": ObjectId(source_goal_id),
            "employee_id": {"$ne": exclude_employee_id},
            "status": GoalStatus.LOCKED,
            "is_shared": True,
        },
        {
            "$set": set_fields
        },
    )
    return result.modified_count



async def view_pushed_shared_goals(current_user: dict) -> List[SharedGoalResponse]:
    role = current_user["role"]
    query: dict = {"is_shared": True}

    if role == "MANAGER":
        query["primary_owner_id"] = current_user["employee_id"]

    cursor = goals.find(query).sort("created_at", -1)
    result = []
    async for data in cursor:
        result.append(_build_shared_response(data))

    return result
