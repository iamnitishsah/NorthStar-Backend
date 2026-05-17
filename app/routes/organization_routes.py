from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.organization_schema import HierarchyNode
from app.services.organization_service import get_organization_hierarchy

router = APIRouter(prefix="/organization", tags=["Organization APIs"])

@router.get("/hierarchy", response_model=List[HierarchyNode])
async def get_organization_hierarchy_router():
    status, response = await get_organization_hierarchy()
    if not status:
        raise HTTPException(status_code=400, detail=response)
    return response