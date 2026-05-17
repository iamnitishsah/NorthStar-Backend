from fastapi import APIRouter, Depends
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.role_dependency import require_admin
from app.services.admin_analytics_service import (
    distribution_analytics,
    qoq_analytics,
)

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics APIs"])


@router.get("/qoq", response_model=dict)
async def qoq_analytics_router(
    current_user: dict = Depends(get_current_user),
    admin=Depends(require_admin),
):
    return await qoq_analytics()


@router.get("/distribution", response_model=dict)
async def distribution_analytics_router(
    current_user: dict = Depends(get_current_user),
    admin=Depends(require_admin),
):
    return await distribution_analytics()
