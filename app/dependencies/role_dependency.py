from fastapi import Depends, HTTPException
from app.dependencies.auth_dependency import get_current_user
from app.constants.enums import Role


async def require_employee(
    current_user=Depends(get_current_user)
):

    if current_user["role"] != Role.EMPLOYEE:

        raise HTTPException(
            status_code=403,
            detail="Employee access required"
        )

    return current_user


async def require_manager(
    current_user=Depends(get_current_user)
):

    if current_user["role"] != Role.MANAGER:

        raise HTTPException(
            status_code=403,
            detail="Manager access required"
        )

    return current_user


async def require_admin(
    current_user=Depends(get_current_user)
):

    if current_user["role"] != Role.ADMIN:

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user