from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.role_dependency import require_admin
from app.services.admin_service import (
    unlock_goal,
    view_logs
)

router = APIRouter(prefix="/admin/goals", tags=["Admin APIs"])


@router.patch("/{goal_id}/unlock", response_model=dict)
async def unlock_goal_router(goal_id: str, current_user: dict = Depends(get_current_user), admin=Depends(require_admin)):

    success, message = await unlock_goal(goal_id, current_user)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}


@router.get("/logs", response_model=list[dict])
async def view_logs_router(action: str = None, user_id: str = None, current_user: dict = Depends(get_current_user), admin=Depends(require_admin)):
    logs = await view_logs(action_filter=action, user_id_filter=user_id)
    return logs