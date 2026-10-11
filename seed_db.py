import asyncio
from datetime import datetime, UTC
from app.db.database import db
from app.core.security import hash_password
from app.constants.enums import Role, Gender
from app.models.user_model import User


async def seed_users():
    users_collection = db.users

    # Common password for everyone
    hashed_pass = hash_password("Nitish@2027")
    now = datetime.now(UTC)

    # 1. ADMINS & HR (Top Level)
    # 2. MANAGERS (Report to Admin)
    # 3. EMPLOYEES (Report to Managers)

    marvel_characters = [
        # --- ADMIN ---
        {
            "employee_id": "SHIELD001", "name": "Nick Fury", "age": 65, "gender": Gender.MALE,
            "phone": "9876543210", "email": "nfury@shield.com", "department": "Executive",
            "designation": "Director", "role": Role.ADMIN, "manager_id": None
        },

        # --- HR ---
        {
            "employee_id": "SHIELD002", "name": "Phil Coulson", "age": 52, "gender": Gender.MALE,
            "phone": "9876543211", "email": "pcoulson@shield.com", "department": "Human Resources",
            "designation": "HR Head", "role": Role.HR, "manager_id": "SHIELD001"
        },
        {
            "employee_id": "SHIELD003", "name": "Maria Hill", "age": 38, "gender": Gender.FEMALE,
            "phone": "9876543212", "email": "mhill@shield.com", "department": "Human Resources",
            "designation": "HR Manager", "role": Role.HR, "manager_id": "SHIELD001"
        },

        # --- MANAGERS ---
        {
            "employee_id": "STARK001", "name": "Tony Stark", "age": 48, "gender": Gender.MALE,
            "phone": "9876543213", "email": "tstark@stark.com", "department": "R&D",
            "designation": "Head of R&D", "role": Role.MANAGER, "manager_id": "SHIELD001"
        },
        {
            "employee_id": "AVENG001", "name": "Steve Rogers", "age": 80, "gender": Gender.MALE,
            "phone": "9876543214", "email": "srogers@shield.com", "department": "Operations",
            "designation": "Operations Director", "role": Role.MANAGER, "manager_id": "SHIELD001"
        },
        {
            "employee_id": "LAW001", "name": "Matt Murdock", "age": 35, "gender": Gender.MALE,
            "phone": "9876543215", "email": "mmurdock@nelsonmurdock.com", "department": "Legal",
            "designation": "Managing Partner", "role": Role.MANAGER, "manager_id": "SHIELD001"
        },
        {
            "employee_id": "MED001", "name": "Stephen Strange", "age": 45, "gender": Gender.MALE,
            "phone": "9876543216", "email": "sstrange@sanctum.com", "department": "Medical",
            "designation": "Chief Surgeon", "role": Role.MANAGER, "manager_id": "SHIELD001"
        },

        # --- EMPLOYEES: R&D (Reporting to Tony Stark) ---
        {
            "employee_id": "STARK002", "name": "Peter Parker", "age": 18, "gender": Gender.MALE,
            "phone": "9876543217", "email": "pparker@stark.com", "department": "R&D",
            "designation": "Intern", "role": Role.EMPLOYEE, "manager_id": "STARK001"
        },
        {
            "employee_id": "STARK003", "name": "Bruce Banner", "age": 49, "gender": Gender.MALE,
            "phone": "9876543218", "email": "bbanner@stark.com", "department": "R&D",
            "designation": "Lead Scientist", "role": Role.EMPLOYEE, "manager_id": "STARK001"
        },
        {
            "employee_id": "STARK004", "name": "Shuri", "age": 22, "gender": Gender.FEMALE,
            "phone": "9876543219", "email": "shuri@wakanda.com", "department": "R&D",
            "designation": "Chief Engineer", "role": Role.EMPLOYEE, "manager_id": "STARK001"
        },
        {
            "employee_id": "STARK005", "name": "Hope van Dyne", "age": 38, "gender": Gender.FEMALE,
            "phone": "9876543220", "email": "hope@pym.com", "department": "R&D",
            "designation": "Quantum Researcher", "role": Role.EMPLOYEE, "manager_id": "STARK001"
        },

        # --- EMPLOYEES: Operations (Reporting to Steve Rogers) ---
        {
            "employee_id": "AVENG002", "name": "Natasha Romanoff", "age": 35, "gender": Gender.FEMALE,
            "phone": "9876543221", "email": "nromanoff@shield.com", "department": "Operations",
            "designation": "Senior Operative", "role": Role.EMPLOYEE, "manager_id": "AVENG001"
        },
        {
            "employee_id": "AVENG003", "name": "Sam Wilson", "age": 39, "gender": Gender.MALE,
            "phone": "9876543222", "email": "swilson@shield.com", "department": "Operations",
            "designation": "Tactical Lead", "role": Role.EMPLOYEE, "manager_id": "AVENG001"
        },
        {
            "employee_id": "AVENG004", "name": "Bucky Barnes", "age": 80, "gender": Gender.MALE,
            "phone": "9876543223", "email": "bbarnes@shield.com", "department": "Operations",
            "designation": "Field Agent", "role": Role.EMPLOYEE, "manager_id": "AVENG001"
        },
        {
            "employee_id": "AVENG005", "name": "Clint Barton", "age": 40, "gender": Gender.MALE,
            "phone": "9876543224", "email": "cbarton@shield.com", "department": "Operations",
            "designation": "Recon Specialist", "role": Role.EMPLOYEE, "manager_id": "AVENG001"
        },
        {
            "employee_id": "AVENG006", "name": "Frank Castle", "age": 42, "gender": Gender.MALE,
            "phone": "9876543225", "email": "fcastle@shield.com", "department": "Operations",
            "designation": "Security Specialist", "role": Role.EMPLOYEE, "manager_id": "AVENG001"
        },

        # --- EMPLOYEES: Legal (Reporting to Matt Murdock) ---
        {
            "employee_id": "LAW002", "name": "Foggy Nelson", "age": 35, "gender": Gender.MALE,
            "phone": "9876543226", "email": "fnelson@nelsonmurdock.com", "department": "Legal",
            "designation": "Senior Partner", "role": Role.EMPLOYEE, "manager_id": "LAW001"
        },
        {
            "employee_id": "LAW003", "name": "Karen Page", "age": 32, "gender": Gender.FEMALE,
            "phone": "9876543227", "email": "kpage@nelsonmurdock.com", "department": "Legal",
            "designation": "Lead Investigator", "role": Role.EMPLOYEE, "manager_id": "LAW001"
        },
        {
            "employee_id": "LAW004", "name": "Jennifer Walters", "age": 33, "gender": Gender.FEMALE,
            "phone": "9876543228", "email": "jwalters@glk-h.com", "department": "Legal",
            "designation": "Superhuman Law Expert", "role": Role.EMPLOYEE, "manager_id": "LAW001"
        },
        {
            "employee_id": "LAW005", "name": "Jessica Jones", "age": 34, "gender": Gender.FEMALE,
            "phone": "9876543229", "email": "jjones@alias.com", "department": "Legal",
            "designation": "Private Investigator", "role": Role.EMPLOYEE, "manager_id": "LAW001"
        },
        {
            "employee_id": "LAW006", "name": "Luke Cage", "age": 36, "gender": Gender.MALE,
            "phone": "9876543230", "email": "lcage@harlem.com", "department": "Legal",
            "designation": "Contract Security", "role": Role.EMPLOYEE, "manager_id": "LAW001"
        },

        # --- EMPLOYEES: Medical (Reporting to Stephen Strange) ---
        {
            "employee_id": "MED002", "name": "Christine Palmer", "age": 42, "gender": Gender.FEMALE,
            "phone": "9876543231", "email": "cpalmer@metrogeneral.com", "department": "Medical",
            "designation": "Trauma Surgeon", "role": Role.EMPLOYEE, "manager_id": "MED001"
        },
        {
            "employee_id": "MED003", "name": "Wong", "age": 48, "gender": Gender.MALE,
            "phone": "9876543232", "email": "wong@sanctum.com", "department": "Medical",
            "designation": "Head Librarian", "role": Role.EMPLOYEE, "manager_id": "MED001"
        },
        {
            "employee_id": "MED004", "name": "Claire Temple", "age": 35, "gender": Gender.FEMALE,
            "phone": "9876543233", "email": "ctemple@metrogeneral.com", "department": "Medical",
            "designation": "Night Nurse", "role": Role.EMPLOYEE, "manager_id": "MED001"
        }
    ]

    print("Checking for existing users...")
    count = await users_collection.count_documents({})
    if count > 0:
        print(f"Found {count} existing users. Clearing database for fresh seed...")
        await users_collection.delete_many({})

    print("Seeding Marvel / Daredevil Universe Characters...")

    users_to_insert = []
    for char in marvel_characters:
        user_model = User(
            **char,
            hashed_password=hashed_pass,
            is_active=True,
            created_at=now
        )
        users_to_insert.append(user_model.model_dump())

    # Insert many at once for efficiency
    await users_collection.insert_many(users_to_insert)

    print(f"Successfully inserted {len(users_to_insert)} characters into the database!")
    print("All characters share the password: Nitish@2027")


if __name__ == "__main__":
    asyncio.run(seed_users())