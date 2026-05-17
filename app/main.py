from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from app.core.config import config
from app.db.database import create_indexes
from app.routes.auth_routes import router as auth_router
from app.routes.employee_router import router as employee_goal_router
from app.routes.manager_router import router as manager_goal_router
from app.routes.admin_router import router as admin_goal_router
from app.routes.admin_analytics_router import router as admin_analytics_router
from app.routes.organization_routes import router as organization_router
from app.routes.shared_goal_router import router as shared_goal_router

app = FastAPI(
    title="NorthStar API Gateway",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await create_indexes()

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "NorthStar API Gateway is live"}


app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(employee_goal_router)
app.include_router(manager_goal_router)
app.include_router(admin_goal_router)
app.include_router(admin_analytics_router)
app.include_router(shared_goal_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.GATEWAY_PORT, reload=True)
