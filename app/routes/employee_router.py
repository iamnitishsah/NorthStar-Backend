from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.role_dependency import require_employee
from app.schemas.goal_schema import (
    CreateGoalRequest,
    UpdateGoalRequest,
    ViewGoalResponse,
    QuarterlyCheckinRequest
)
from app.services.employee_service import (
    my_goals,
    create_goal,
    update_goal,
    delete_goal,
    submit_goals,
    quarterly_checkin
)

router = APIRouter(prefix="/employee/goals", tags=["Employee APIs"])


@router.get("/my", response_model=List[ViewGoalResponse])
async def my_goals_router(
    current_user: dict = Depends(get_current_user)
):

    goal = await my_goals(current_user)

    return goal


@router.post("/", response_model=dict)
async def create_goal_router(
    payload: CreateGoalRequest,
    current_user: dict = Depends(get_current_user),
    employee=Depends(require_employee)
):

    success, message = await create_goal(
        payload,
        current_user,
        employee
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}


@router.patch("/{goal_id}", response_model=dict)
async def update_goal_router(
    goal_id: str,
    payload: UpdateGoalRequest,
    current_user: dict = Depends(get_current_user)
):

    success, message = await update_goal(
        goal_id,
        payload,
        current_user
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}


@router.delete("/{goal_id}", response_model=dict)
async def delete_goal_router(
    goal_id: str,
    current_user: dict = Depends(get_current_user)
):

    success, message = await delete_goal(
        goal_id,
        current_user
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}


@router.post("/submit", response_model=dict)
async def submit_goal_router(
    goal_ids: list[str],
    current_user: dict = Depends(get_current_user),
    employee=Depends(require_employee)
):

    success, message = await submit_goals(
        goal_ids,
        current_user
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}



@router.patch("/{goal_id}/quarterly-checkin", response_model=dict)
async def quarterly_checkin_router(goal_id: str, payload: QuarterlyCheckinRequest, current_user: dict = Depends(get_current_user)):
    success, message = await quarterly_checkin(goal_id, payload, current_user)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}