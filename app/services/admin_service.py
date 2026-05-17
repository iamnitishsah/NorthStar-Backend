from datetime import datetime, UTC
from bson import ObjectId
from fastapi import HTTPException
from app.constants.enums import GoalStatus
from app.db.database import db
from app.audit.logs import log_action

goals = db.goals
logs = db.logs
unlock_requests = db.unlock_requests
users = db.users


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
                "status": GoalStatus.ADMIN_UNLOCKED,
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="UNLOCK_GOAL",
        details={
            "goal_id": goal_id,
            "previous_status": GoalStatus.LOCKED,
            "new_status": GoalStatus.ADMIN_UNLOCKED
        }
    )

    return True, "Goal unlocked successfully"


async def view_logs(action_filter: str = None, user_id_filter: str = None) -> list[dict]:
    query = {}
    if action_filter:
        query["action"] = action_filter
    if user_id_filter:
        query["user_id"] = user_id_filter

    logs_cursor = logs.find(query).sort("timestamp", -1).limit(100)
    logs_list = []
    async for log in logs_cursor:
        log["_id"] = str(log["_id"])
        log["user_id"] = str(log["user_id"])
        logs_list.append(log)
    return logs_list


async def view_unlock_requests(status_filter: str = None) -> list[dict]:
    query: dict = {}
    if status_filter:
        query["status"] = status_filter

    requests_cursor = unlock_requests.find(query).sort("created_at", -1).limit(200)
    results = []

    async for request in requests_cursor:
        manager_name = None
        manager_id = request.get("manager_id")
        if manager_id:
            manager = await users.find_one({"employee_id": manager_id}, {"name": 1})
            manager_name = manager.get("name") if manager else None

        results.append(
            {
                "request_id": str(request["_id"]),
                "goal_id": str(request["goal_id"]),
                "goal_title": request.get("goal_title"),
                "requester_id": request.get("requester_id"),
                "requester_name": request.get("requester_name"),
                "manager_id": manager_id,
                "manager_name": manager_name,
                "reason": request.get("reason"),
                "status": request.get("status"),
                "resolved_by": request.get("resolved_by"),
                "resolved_at": request.get("resolved_at"),
                "rejection_reason": request.get("rejection_reason"),
                "created_at": request.get("created_at"),
                "updated_at": request.get("updated_at"),
            }
        )

    return results


async def approve_unlock_request(request_id: str, current_user: dict) -> tuple[bool, str]:
    if not ObjectId.is_valid(request_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid request ID"
        )

    request_data = await unlock_requests.find_one({"_id": ObjectId(request_id)})
    if not request_data:
        raise HTTPException(
            status_code=404,
            detail="Unlock request not found"
        )

    if request_data.get("status") != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Unlock request is not pending"
        )

    goal_id = request_data.get("goal_id")
    goal_data = await goals.find_one({"_id": goal_id})
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

    now = datetime.now(UTC)

    await goals.update_one(
        {"_id": goal_id},
        {
            "$set": {
                "status": GoalStatus.ADMIN_UNLOCKED,
                "updated_at": now
            }
        }
    )

    await unlock_requests.update_one(
        {"_id": ObjectId(request_id)},
        {
            "$set": {
                "status": "APPROVED",
                "resolved_by": current_user["employee_id"],
                "resolved_at": now,
                "updated_at": now,
            }
        }
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="APPROVE_UNLOCK_REQUEST",
        details={
            "request_id": request_id,
            "goal_id": str(goal_id),
            "requester_id": request_data.get("requester_id"),
        }
    )

    return True, "Unlock request approved and goal unlocked"


async def reject_unlock_request(request_id: str, reason: str | None, current_user: dict) -> tuple[bool, str]:
    if not ObjectId.is_valid(request_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid request ID"
        )

    request_data = await unlock_requests.find_one({"_id": ObjectId(request_id)})
    if not request_data:
        raise HTTPException(
            status_code=404,
            detail="Unlock request not found"
        )

    if request_data.get("status") != "PENDING":
        raise HTTPException(
            status_code=400,
            detail="Unlock request is not pending"
        )

    now = datetime.now(UTC)

    await unlock_requests.update_one(
        {"_id": ObjectId(request_id)},
        {
            "$set": {
                "status": "REJECTED",
                "resolved_by": current_user["employee_id"],
                "resolved_at": now,
                "rejection_reason": reason,
                "updated_at": now,
            }
        }
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="REJECT_UNLOCK_REQUEST",
        details={
            "request_id": request_id,
            "goal_id": str(request_data.get("goal_id")),
            "requester_id": request_data.get("requester_id"),
            "reason": reason,
        }
    )

    return True, "Unlock request rejected"
