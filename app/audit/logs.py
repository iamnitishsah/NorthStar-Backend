from datetime import UTC, datetime
from app.db.database import db

logs = db.logs

async def log_action(user_id: str, action: str, details: dict):
    log_entry = {
        "user_id": user_id,
        "action": action,
        "details": details,
        "timestamp": datetime.now(UTC)
    }
    await logs.insert_one(log_entry)