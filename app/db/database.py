from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis
from app.core.config import config

mongo_client = AsyncIOMotorClient(config.MONGO_URI)
db = mongo_client["NorthStarDB"]

redis_client = Redis.from_url(
    config.REDIS_URL,
    decode_responses=True,
)


async def create_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("employee_id", unique=True)
    await db.users.create_index("manager_id")
    await db.goals.create_index("status")
    await db.goals.create_index("employee_id")
    await db.goals.create_index("manager_id")
    await db.goals.create_index("source_goal_id")
    await db.goals.create_index("is_shared")
    await db.logs.create_index("timestamp")
    await db.logs.create_index("user_id")
    await db.unlock_requests.create_index("status")
    await db.unlock_requests.create_index("goal_id")
    await db.unlock_requests.create_index("requester_id")
    await db.unlock_requests.create_index("created_at")
