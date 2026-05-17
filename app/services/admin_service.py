import csv
from collections import defaultdict
from io import StringIO
from datetime import datetime, UTC
from bson import ObjectId
from fastapi import HTTPException
from app.constants.enums import GoalStatus, Role
from app.db.database import db
from app.audit.logs import log_action

goals = db.goals
logs = db.logs
unlock_requests = db.unlock_requests
users = db.users


def _csv_value(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


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


async def view_logs(
    action_filter: str = None,
    user_id_filter: str = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    query = {}
    if action_filter:
        query["action"] = action_filter
    if user_id_filter:
        query["user_id"] = user_id_filter

    logs_cursor = logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    logs_list = []
    async for log in logs_cursor:
        log["_id"] = str(log["_id"])
        log["user_id"] = str(log["user_id"])
        logs_list.append(log)
    return logs_list


async def export_goals_report() -> str:
    output = StringIO()
    fieldnames = [
        "goal_id",
        "employee_id",
        "employee_name",
        "manager_id",
        "title",
        "thrust_area",
        "uom_type",
        "measurement_type",
        "planned_target_value",
        "actual_achievement_value",
        "progress_percentage",
        "progress_status",
        "weightage",
        "target_date",
        "status",
        "q1_actual",
        "q1_progress_percentage",
        "q1_progress_status",
        "q2_actual",
        "q2_progress_percentage",
        "q2_progress_status",
        "q3_actual",
        "q3_progress_percentage",
        "q3_progress_status",
        "q4_actual",
        "q4_progress_percentage",
        "q4_progress_status",
        "created_at",
        "updated_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    goals_cursor = goals.find({}).sort([("employee_name", 1), ("created_at", -1)])
    async for goal in goals_cursor:
        quarter = goal.get("quarter") or {}
        row = {
            "goal_id": str(goal["_id"]),
            "employee_id": goal.get("employee_id"),
            "employee_name": goal.get("employee_name"),
            "manager_id": goal.get("manager_id"),
            "title": goal.get("title"),
            "thrust_area": goal.get("thrust_area"),
            "uom_type": goal.get("uom_type"),
            "measurement_type": goal.get("measurement_type"),
            "planned_target_value": goal.get("target_value"),
            "actual_achievement_value": goal.get("achievement_value"),
            "progress_percentage": goal.get("progress_percentage"),
            "progress_status": goal.get("progress_status"),
            "weightage": goal.get("weightage"),
            "target_date": goal.get("target_date"),
            "status": goal.get("status"),
            "created_at": goal.get("created_at"),
            "updated_at": goal.get("updated_at"),
        }

        for quarter_number in range(1, 5):
            quarter_data = quarter.get(str(quarter_number)) or {}
            row[f"q{quarter_number}_actual"] = quarter_data.get("achievement_value")
            row[f"q{quarter_number}_progress_percentage"] = quarter_data.get("progress_percentage")
            row[f"q{quarter_number}_progress_status"] = quarter_data.get("progress_status")

        writer.writerow({key: _csv_value(value) for key, value in row.items()})

    return output.getvalue()


async def completion_dashboard() -> list[dict]:
    employee_goals = defaultdict(list)
    goals_cursor = goals.find({}).sort([("employee_name", 1), ("created_at", -1)])

    async for goal in goals_cursor:
        employee_goals[goal.get("employee_id")].append(goal)

    employees = {}
    users_cursor = users.find({"role": Role.EMPLOYEE, "is_active": True}).sort("name", 1)
    async for user in users_cursor:
        employees[user["employee_id"]] = user

    for employee_id, grouped_goals in employee_goals.items():
        if employee_id not in employees:
            first_goal = grouped_goals[0]
            employees[employee_id] = {
                "employee_id": employee_id,
                "name": first_goal.get("employee_name"),
                "manager_id": first_goal.get("manager_id"),
            }

    dashboard = []
    for employee_id, employee in employees.items():
        grouped_goals = employee_goals.get(employee_id, [])
        checkin_goals = [
            goal for goal in grouped_goals
            if goal.get("status") == GoalStatus.LOCKED
        ]
        manager_id = employee.get("manager_id") or (
            grouped_goals[0].get("manager_id") if grouped_goals else None
        )
        manager = await users.find_one({"employee_id": manager_id}, {"name": 1}) if manager_id else None

        quarters = {}
        latest_completed_quarter = None
        for quarter_number in range(1, 5):
            quarter_key = str(quarter_number)
            employee_completed_goals = 0
            manager_completed_goals = 0

            for goal in checkin_goals:
                quarter_data = (goal.get("quarter") or {}).get(quarter_key)
                if not quarter_data:
                    continue

                employee_completed_goals += 1
                if quarter_data.get("manager_note"):
                    manager_completed_goals += 1

            employee_complete = (
                len(checkin_goals) > 0
                and employee_completed_goals == len(checkin_goals)
            )
            manager_complete = (
                employee_completed_goals > 0
                and manager_completed_goals == employee_completed_goals
            )

            if employee_complete:
                latest_completed_quarter = quarter_number

            quarters[f"q{quarter_number}"] = {
                "employee_completed": employee_complete,
                "employee_completed_goals": employee_completed_goals,
                "manager_completed": manager_complete,
                "manager_completed_goals": manager_completed_goals,
                "required_goals": len(checkin_goals),
            }

        dashboard.append(
            {
                "employee_id": employee_id,
                "employee_name": employee.get("name"),
                "manager_id": manager_id,
                "manager_name": manager.get("name") if manager else None,
                "total_goals": len(grouped_goals),
                "checkin_required_goals": len(checkin_goals),
                "latest_completed_quarter": latest_completed_quarter,
                "quarters": quarters,
            }
        )

    return dashboard


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
