from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth_dependency import get_current_user
from app.schemas.shared_goal_schema import (
    PushSharedGoalRequest,
    SharedGoalResponse,
)
from app.services.shared_goal_service import (
    push_shared_goal,
    view_pushed_shared_goals,
)

router = APIRouter(prefix="/shared-goals", tags=["Shared Goal APIs"])




@router.post("/push", response_model=dict)
async def push_shared_goal_router(payload: PushSharedGoalRequest, current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Manager can push shared goals",
        )

    success, result = await push_shared_goal(payload, current_user)

    if not success:
        raise HTTPException(status_code=400, detail=result)

    return result




@router.get("/pushed", response_model=List[SharedGoalResponse])
async def view_pushed_router(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in ("ADMIN", "MANAGER"):
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Manager can view pushed shared goals",
        )

    return await view_pushed_shared_goals(current_user)