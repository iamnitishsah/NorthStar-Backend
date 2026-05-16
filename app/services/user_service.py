from app.db.database import db

users = db.users

async def get_team_members(employee_id: str):

    team = await users.find({"manager_id": employee_id}).to_list(length=None)