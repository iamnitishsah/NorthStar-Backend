from app.models.goal_model import Goal
from collections import defaultdict
from app.schemas.goal_schema import CreateGoalRequest, UpdateGoalRequest, ReturnGoalRequest, ViewGoalResponse
from app.db.database import db
from bson import ObjectId
from datetime import datetime, UTC
from app.constants.enums import GoalStatus
from fastapi import HTTPException
from typing import List

goals=db.goals


'''Service functions for Employee Goal Management'''
async def my_goals(current_user: dict) -> List[ViewGoalResponse]:
    employee_id = current_user["employee_id"]
    manager_id = current_user["manager_id"]

    goal_data = goals.find({"employee_id": employee_id}).sort("created_at", -1)

    goals_list = []

    async for data in goal_data:
        goal = ViewGoalResponse(
            goal_id=str(data["_id"]),
            employee_name=data["employee_name"],
            title=data["title"],
            description=data.get("description"),
            weightage=data["weightage"],
            target_date=data.get("target_date"),
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
    goal_status = GoalStatus.DRAFT
    goal = Goal(
        employee_id=employee_id,
        employee_name=employee_name,
        manager_id=manager_id,
        title=payload.title,
        description=payload.description,
        weightage=payload.weightage,
        target_date=payload.target_date,
        status=goal_status
    )
    result = await goals.insert_one(goal.model_dump())
    return True, f"Goal created successfully with ID: {result.inserted_id}"


async def update_goal(goal_id: str, payload: UpdateGoalRequest, current_user: dict) -> tuple[bool, str]:
    if not ObjectId.is_valid(goal_id):
        raise HTTPException(status_code=400, detail="Invalid goal ID")
    
    goal_data = await goals.find_one({"_id": ObjectId(goal_id)})

    if not goal_data:
        raise HTTPException(status_code=404, detail="Goal not found")

    if goal_data["employee_id"] != current_user["employee_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized to update this goal")
    
    if goal_data["status"] != GoalStatus.DRAFT and goal_data["status"] != GoalStatus.RETURNED:
        raise HTTPException(status_code=400, detail="Only DRAFT or RETURNED goals can be updated")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.now(UTC)

    await goals.update_one({"_id": ObjectId(goal_id)}, {"$set": update_data})
    return True, "Goal updated successfully"


async def delete_goal(goal_id: str, current_user: dict, employee: dict) -> tuple[bool, str]:
    if not ObjectId.is_valid(goal_id):
        raise HTTPException(status_code=400, detail="Invalid goal ID")
    
    goal_data = await goals.find_one({"_id": ObjectId(goal_id)})

    if not goal_data:
        raise HTTPException(status_code=404, detail="Goal not found")

    if goal_data["employee_id"] != current_user["employee_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized to delete this goal")
    
    if goal_data["status"] != GoalStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT goals can be deleted")

    await goals.delete_one({"_id": ObjectId(goal_id)})
    return True, "Goal deleted successfully"


async def submit_goal(current_user: dict, employee: dict) -> tuple[bool, str]:
    employee_goals = await goals.find({"employee_id": current_user["employee_id"]}).to_list(length=None)

    if len(employee_goals) < 1 or len(employee_goals) > 8:
        raise HTTPException(
            status_code=400,
            detail="You must have between 1 and 8 goals to submit for approval"
        )

    total_weightage = sum(g["weightage"] for g in employee_goals)

    if total_weightage != 100:
        raise HTTPException(
            status_code=400,
            detail="Total goal weightage must equal 100"
        )
    
    await goals.update_many(
        {
            "employee_id": current_user["employee_id"],
            "status": GoalStatus.DRAFT
        },
        {
            "$set": {
                "status": GoalStatus.SUBMITTED,
                "submitted_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
        }
    )

    return True, "Goal submitted successfully"



'''Service function for Manager to view, approve, or return employee goals'''
async def view_goals(current_user: dict) -> dict[str, List[ViewGoalResponse]]:
    employee_id = current_user["employee_id"]
    manager_id = current_user["manager_id"]

    goal_data = goals.find({"manager_id": manager_id}).sort("created_at", -1)

    grouped_goals = defaultdict(list)

    async for data in goal_data:
        goal = ViewGoalResponse(
            goal_id=str(data["_id"]),
            employee_name=data["employee_name"],
            title=data["title"],
            description=data.get("description"),
            weightage=data["weightage"],
            target_date=data.get("target_date"),
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
    return grouped_goals