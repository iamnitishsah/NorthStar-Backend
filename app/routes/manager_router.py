from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.role_dependency import require_manager
from app.schemas.goal_schema import (
    ReturnGoalRequest,
    ViewGoalResponse
)
from app.services.manager_service import (
    review_goals,
    approve_goal,
    return_goal,
    view_goals,
    comment_on_goal
)

router = APIRouter(prefix="/manager/goals", tags=["Manager APIs"])


@router.get("/review", response_model=dict[str, List[ViewGoalResponse]])
async def review_goals_router(current_user: dict = Depends(get_current_user), manager = Depends(require_manager)):
    goals = await review_goals(current_user)

    if not goals:
        raise HTTPException(
            status_code=404,
            detail="No goals found for review"
        )

    return goals


@router.post("/{goal_id}/approve", response_model=dict)
async def approve_goal_router(goal_id: str, current_user: dict = Depends(get_current_user), manager = Depends(require_manager)):
    success, message = await approve_goal(goal_id, current_user)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}


@router.post("/{goal_id}/return", response_model=dict)
async def return_goal_router(goal_id: str, payload: ReturnGoalRequest, current_user: dict = Depends(get_current_user), manager = Depends(require_manager)):

    success, message = await return_goal(goal_id, payload, current_user)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}


@router.get("/", response_model=dict[str, List[ViewGoalResponse]])
async def view_goals_router(current_user: dict = Depends(get_current_user), manager = Depends(require_manager)):
    goals = await view_goals(current_user)

    if not goals:
        raise HTTPException(
            status_code=404,
            detail="No goals found for this manager"
        )

    return goals


@router.post("/{goal_id}/comment", response_model=dict)
async def comment_on_goal_router(goal_id: str, comment: str, current_user: dict = Depends(get_current_user), manager = Depends(require_manager)):
    success, message = await comment_on_goal(goal_id, comment, current_user)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}