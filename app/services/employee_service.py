from datetime import datetime, UTC, date
from typing import List
from bson import ObjectId
from fastapi import HTTPException
from app.constants.enums import GoalStatus, ProgressStatus, UOMType, MeasurementType
from app.db.database import db
from app.models.goal_model import Goal
from app.schemas.goal_schema import (
    CreateGoalRequest,
    UpdateGoalRequest,
    ViewGoalResponse,
    QuarterlyCheckinRequest
)
from app.audit.logs import log_action

goals = db.goals


async def my_goals(current_user: dict) -> List[ViewGoalResponse]:
    employee_id = current_user["employee_id"]
    goal_data = goals.find(
        {"employee_id": employee_id, "is_shared": {"$ne": True}}
    ).sort("created_at", -1)

    goals_list = []

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

        goals_list.append(goal)

    return goals_list


async def create_goal(payload: CreateGoalRequest, current_user: dict, employee: dict) -> tuple[bool, str]:
    employee_id = current_user["employee_id"]
    employee_name = current_user["name"]
    manager_id = employee["manager_id"]

    existing_count = await goals.count_documents(
        {
            "employee_id": employee_id,
            "status": {
                "$in": [
                    GoalStatus.DRAFT,
                    GoalStatus.RETURNED,
                    GoalStatus.ADMIN_UNLOCKED,
                    GoalStatus.SUBMITTED,
                    GoalStatus.LOCKED,
                ]
            },
        }
    )
    if existing_count >= 8:
        raise HTTPException(
            status_code=400,
            detail="Maximum 8 goals allowed per employee"
        )

    goal = Goal(
        employee_id=employee_id,
        employee_name=employee_name,
        manager_id=manager_id,
        thrust_area=payload.thrust_area,
        title=payload.title,
        description=payload.description,
        uom_type=payload.uom_type,
        measurement_type=payload.measurement_type,
        target_value=payload.target_value,
        weightage=payload.weightage,
        target_date=payload.target_date,
        status=GoalStatus.DRAFT,
    )

    result = await goals.insert_one(goal.model_dump())


    await log_action(
        user_id=current_user["employee_id"],
        action="CREATE_GOAL",
        details={
            "goal_id": str(result.inserted_id),
            "title": payload.title,
            "thrust_area": payload.thrust_area,
            "weightage": payload.weightage
            }
    )

    return True, f"Goal created successfully with ID: {result.inserted_id}"


async def update_goal(goal_id: str, payload: UpdateGoalRequest, current_user: dict) -> tuple[bool, str]:
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
            detail="Unauthorized to update this goal"
        )

    if goal_data["status"] not in [GoalStatus.DRAFT, GoalStatus.RETURNED, GoalStatus.ADMIN_UNLOCKED]:
        raise HTTPException(
            status_code=400,
            detail="Only DRAFT or RETURNED goals can be updated"
        )
    
    if goal_data.get("is_shared"):
        restricted = {k: v for k, v in payload.model_dump().items() if v is not None and k in ["title", "uom_type", "measurement_type", "target_value", "thrust_area", "weightage"]}
        if restricted:
            raise HTTPException(
                status_code=403,
                detail=f"Shared goal fields are read-only: {list(restricted.keys())}. Use PATCH /shared-goals/{{goal_id}}/weightage to adjust weightage."
            )

    update_data = {
        k: v
        for k, v in payload.model_dump().items()
        if v is not None
    }

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    update_data["updated_at"] = datetime.now(UTC)

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {"$set": update_data}
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="UPDATE_GOAL",
        details={
            "goal_id": goal_id,
            "updated_fields": list(update_data.keys())
        }
    )

    return True, "Goal updated successfully"


async def delete_goal(goal_id: str, current_user: dict) -> tuple[bool, str]:
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
            detail="Unauthorized to delete this goal"
        )

    if goal_data["status"] != GoalStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Only DRAFT goals can be deleted"
        )
    
    await log_action(
        user_id=current_user["employee_id"],
        action="DELETE_GOAL",
        details={
            "goal_id": goal_id
        }
    )

    await goals.delete_one({"_id": ObjectId(goal_id)})

    return True, "Goal deleted successfully"


async def submit_goals(goal_ids: list[str], current_user: dict) -> tuple[bool, str]:
    employee_id = current_user["employee_id"]

    selected_goals = await goals.find(
        {
            "_id": {
                "$in": [ObjectId(goal_id) for goal_id in goal_ids]
            },

            "employee_id": employee_id,

            "status": {
                "$in": [
                    GoalStatus.DRAFT,
                    GoalStatus.RETURNED,
                    GoalStatus.ADMIN_UNLOCKED,
                ]
            }
        }
    ).to_list(length=None)

    locked_goals = await goals.find(
        {
            "employee_id": employee_id,

            "status": {
                "$in": [GoalStatus.LOCKED]
            }
        }
    ).to_list(length=None)

    if len(selected_goals) < 1:
        raise HTTPException(
            status_code=400,
            detail="Select at least one goal"
        )

    invalid_weightage = [goal for goal in selected_goals if goal.get("weightage", 0) < 10]
    if invalid_weightage:
        raise HTTPException(
            status_code=400,
            detail="Each submitted goal must have minimum weightage of 10"
        )

    invalid_shared = []
    shared_fields = [
        "thrust_area",
        "title",
        "description",
        "uom_type",
        "measurement_type",
        "target_value",
        "target_date",
    ]
    for goal in selected_goals:
        if not goal.get("is_shared"):
            continue
        snapshot = goal.get("source_snapshot")
        if not snapshot:
            continue
        if any(goal.get(field) != snapshot.get(field) for field in shared_fields):
            invalid_shared.append(str(goal["_id"]))

    if invalid_shared:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Shared goal fields must match the original shared goal",
                "goal_ids": invalid_shared,
            }
        )

    if len(selected_goals) + len(locked_goals) > 8:
        raise HTTPException(
            status_code=400,
            detail="Maximum 8 goals allowed including locked goals"
        )

    total_weightage = sum(
        goal["weightage"]
        for goal in selected_goals + locked_goals
    )

    if total_weightage != 100:
        raise HTTPException(
            status_code=400,
            detail="Total goal weightage must equal 100"
        )

    await goals.update_many(
        {
            "_id": {
                "$in": [goal["_id"] for goal in selected_goals]
            }
        },
        {
            "$set": {
                "status": GoalStatus.SUBMITTED,
                "submitted_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
        }
    )

    await log_action(
        user_id=current_user["employee_id"],
        action="SUBMIT_GOALS",
        details={
            "goal_ids": goal_ids,
            "number_of_goals_submitted": len(selected_goals)
        }
    )

    return True, "Goals submitted successfully"



async def quarterly_checkin(goal_id: str, payload: QuarterlyCheckinRequest, current_user: dict) -> tuple[bool, str]:
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
            detail="Unauthorized to update this goal"
        )

    if goal_data["status"] != GoalStatus.LOCKED:
        raise HTTPException(
            status_code=400,
            detail="Only LOCKED goals can be updated in quarterly check-in"
        )

    target_value = goal_data["target_value"]
    measurement_type = goal_data["measurement_type"]
    uom_type = goal_data["uom_type"]

    quarterly_data = {}
    progress_by_quarter = {}

    existing_quarters = goal_data.get("quarter", {}) or {}
    existing_quarter_keys = []
    for key in existing_quarters.keys():
        try:
            existing_quarter_keys.append(int(key))
        except (TypeError, ValueError):
            continue
    max_existing_quarter = max(existing_quarter_keys) if existing_quarter_keys else 0

    incoming_quarters = []
    for key in payload.quarter.keys():
        try:
            incoming_quarters.append(int(key))
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Quarter keys must be numeric between 1 and 4"
            )

    if not incoming_quarters:
        raise HTTPException(
            status_code=400,
            detail="At least one quarter update is required"
        )

    if any(q not in [1, 2, 3, 4] for q in incoming_quarters):
        raise HTTPException(
            status_code=400,
            detail="Quarter must be between 1 and 4"
        )

    if len(set(incoming_quarters)) != len(incoming_quarters):
        raise HTTPException(
            status_code=400,
            detail="Duplicate quarter updates are not allowed"
        )

    min_incoming = min(incoming_quarters)
    if min_incoming != max_existing_quarter + 1:
        raise HTTPException(
            status_code=400,
            detail=f"Next update must be Q{max_existing_quarter + 1}"
        )

    sorted_incoming = sorted(incoming_quarters)
    if sorted_incoming != list(range(min_incoming, min_incoming + len(sorted_incoming))):
        raise HTTPException(
            status_code=400,
            detail="Quarter updates must be sequential without gaps"
        )

    for quarter, checkin in payload.quarter.items():

        achievement_value = checkin.achievement_value

        if uom_type in [UOMType.PERCENTAGE, UOMType.NUMERIC]:

            if achievement_value < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Achievement value must be positive"
                )

            if measurement_type == MeasurementType.MIN:
                progress_percentage = (
                    achievement_value / target_value
                ) * 100

            elif measurement_type == MeasurementType.MAX:

                if achievement_value == 0:
                    progress_percentage = 100
                else:
                    progress_percentage = (
                        target_value / achievement_value
                    ) * 100

            else:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid measurement type"
                )

        elif uom_type == UOMType.ZERO_BASED:

            if achievement_value < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Achievement value must be positive"
                )

            progress_percentage = (
                100 if achievement_value == 0 else 0
            )

        elif uom_type == UOMType.TIMELINE:
            target_date = goal_data.get("target_date")
            if not target_date:
                raise HTTPException(
                    status_code=400,
                    detail="Target date is required for TIMELINE goals"
                )

            if isinstance(achievement_value, datetime):
                completion_date = achievement_value.date()
            elif isinstance(achievement_value, date):
                completion_date = achievement_value
            elif isinstance(achievement_value, str):
                try:
                    completion_date = (
                        datetime.fromisoformat(achievement_value).date()
                        if "T" in achievement_value
                        else date.fromisoformat(achievement_value)
                    )
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid completion date format; use ISO YYYY-MM-DD"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Completion date must be an ISO date string"
                )

            deadline_date = (
                target_date.date() if isinstance(target_date, datetime) else target_date
            )
            start_date = goal_data.get("created_at")
            start_date = start_date.date() if isinstance(start_date, datetime) else start_date
            if not start_date:
                start_date = deadline_date

            if completion_date <= deadline_date:
                progress_percentage = 100
            else:
                total_days = (deadline_date - start_date).days
                if total_days <= 0:
                    total_days = 1
                days_late = (completion_date - deadline_date).days
                progress_percentage = max(0, 100 - (days_late / total_days) * 100)

            achievement_value = completion_date.isoformat()

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid UoM type"
            )

        quarterly_data[str(quarter)] = {
            "achievement_value": achievement_value,
            "progress_status": checkin.progress_status,
            "progress_percentage": progress_percentage,
            "updated_at": datetime.now(UTC)
        }

        progress_by_quarter[str(quarter)] = progress_percentage

    combined_quarters = {**existing_quarters, **quarterly_data}
    combined_progress = {
        **{k: v.get("progress_percentage") for k, v in existing_quarters.items()},
        **progress_by_quarter,
    }

    try:
        latest_quarter_key = max(
            combined_progress.keys(),
            key=lambda key: int(key)
        )
    except ValueError:
        latest_quarter_key = list(combined_progress.keys())[-1]

    latest_progress_percentage = combined_progress[latest_quarter_key]
    latest_achievement_value = combined_quarters[latest_quarter_key]["achievement_value"]

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "achievement_value": latest_achievement_value,
                "progress_percentage": latest_progress_percentage,
                "updated_at": datetime.now(UTC),
                **{f"quarter.{key}": value for key, value in quarterly_data.items()}
            }
        }
    )

    # ── Shared goal sync ──────────────────────────────────────────────────────
    # If this is a shared goal and the updater is the primary owner,
    # propagate achievement to all linked copies.
    is_shared = goal_data.get("is_shared", False)
    is_primary_owner = goal_data.get("primary_owner_id") == current_user["employee_id"]
 
    if is_shared and is_primary_owner:
        source_goal_id = goal_data.get("source_goal_id")
        if source_goal_id:
            from app.services.shared_goal_service import sync_shared_achievement
            synced = await sync_shared_achievement(
                source_goal_id=str(source_goal_id),
                achievement_value=latest_achievement_value,
                progress_percentage=latest_progress_percentage,
                quarterly_data=quarterly_data,
                exclude_employee_id=current_user["employee_id"],
            )
            await log_action(
                user_id=current_user["employee_id"],
                action="SYNC_SHARED_ACHIEVEMENT",
                details={
                    "source_goal_id": str(source_goal_id),
                    "synced_copies": synced,
                    "quarters_updated": list(payload.quarter.keys())
                }
            )
 
    await log_action(
        user_id=current_user["employee_id"],
        action="QUARTERLY_CHECKIN",
        details={
            "goal_id": goal_id,
            "quarters_updated": list(payload.quarter.keys())
        }
    )

    return True, "Quarterly check-in updated successfully"
