from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.role_dependency import require_admin
from app.services.admin_service import (
    unlock_goal
)

router = APIRouter(
    prefix="/admin/goals",
    tags=["Admin Goals"]
)


@router.patch(
    "/{goal_id}/unlock",
    response_model=dict
)
async def unlock_goal_router(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    admin=Depends(require_admin)
):

    success, message = await unlock_goal(goal_id, current_user)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}