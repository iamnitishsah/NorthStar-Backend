from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth_dependency import get_current_user

from app.services.achievement_service import (
    update_achievement
)

router = APIRouter(
    prefix="/achievement",
    tags=["Achievement Tracking"]
)


@router.patch(
    "/{goal_id}",
    response_model=dict
)
async def update_achievement_router(
    goal_id: str,
    achievement_value: float,
    current_user: dict = Depends(get_current_user)
):

    success, message = await update_achievement(
        goal_id,
        achievement_value,
        current_user
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {"message": message}