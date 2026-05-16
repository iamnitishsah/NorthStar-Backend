from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from typing import List
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.role_dependency import require_employee
from app.schemas.goal_schema import CreateGoalRequest, UpdateGoalRequest, ReturnGoalRequest, ViewGoalResponse
from app.services.goal_service import view_goals, create_goal, update_goal, delete_goal, submit_goal

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("/my", response_model=List[ViewGoalResponse])
async def view_goals_router(current_user: dict = Depends(get_current_user)):
    goal = await view_goals(current_user)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.post("/", response_model=dict)
async def create_goal_router(
    payload: CreateGoalRequest,
    current_user: dict = Depends(get_current_user),
    employee=Depends(require_employee)
):
    success, message = await create_goal(payload, current_user, employee)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.patch("/{goal_id}", response_model=dict)
async def update_goal_router(
    goal_id: str,
    payload: UpdateGoalRequest,
    current_user: dict = Depends(get_current_user)
):
    success, message = await update_goal(goal_id, payload, current_user)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": "Goal updated successfully"}


@router.delete("/{goal_id}", response_model=dict)
async def delete_goal_router(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    employee=Depends(require_employee)
):
    success, message = await delete_goal(goal_id, current_user, employee)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": "Goal deleted successfully"}


@router.post("/submit", response_model=dict)
async def submit_goal_router(
    current_user: dict = Depends(get_current_user),
    employee=Depends(require_employee)
):
    success, message = await submit_goal(current_user, employee)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": "Goal submitted for approval successfully"}