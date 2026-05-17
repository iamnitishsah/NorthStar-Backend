from datetime import datetime, UTC
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
        {"employee_id": employee_id}
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
        progress_status=ProgressStatus.NOT_STARTED
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

    if goal_data["status"] not in [GoalStatus.DRAFT, GoalStatus.RETURNED]:
        raise HTTPException(
            status_code=400,
            detail="Only DRAFT or RETURNED goals can be updated"
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
                    GoalStatus.RETURNED
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

    submitted_goals = await goals.find(
        {
            "employee_id": employee_id,
            "status": {
                "$in": [GoalStatus.SUBMITTED]
            }
        }
    ).to_list(length=None)

    if len(selected_goals) < 1:
        raise HTTPException(
            status_code=400,
            detail="Select at least one goal"
        )

    if len(selected_goals) + len(locked_goals) + len(submitted_goals) > 8:
        raise HTTPException(
            status_code=400,
            detail="Maximum 8 goals allowed including locked goals"
        )

    total_weightage = sum(
        goal["weightage"]
        for goal in selected_goals + locked_goals + submitted_goals
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

            if achievement_value < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Achievement value must be positive"
                )

            progress_percentage = achievement_value

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

    await goals.update_one(
        {"_id": ObjectId(goal_id)},
        {
            "$set": {
                "progress_percentage": progress_percentage,
                "quarter": quarterly_data,
                "updated_at": datetime.now(UTC)
            }
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