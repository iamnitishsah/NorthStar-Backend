from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from app.core.config import config
from app.db.database import create_indexes
from app.routes.auth_routes import router as auth_router

app = FastAPI(
    title="NorthStar API Gateway",
    version="1.0",
)

app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "NorthStar API Gateway is live"}


@app.on_event("startup")
async def startup():
    await create_indexes()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.GATEWAY_PORT, reload=True)