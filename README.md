# 🌟 NorthStar — In-House Goal Setting & Tracking Portal
NorthStar is a structured, digital Goal Setting & Tracking Portal built to eliminate fragmented, spreadsheet-driven performance workflows. It supports the full lifecycle of employee goals — from creation and alignment, through quarterly check-ins, to final performance visibility — across three clearly differentiated user roles: **Employee**, **Manager**, and **Admin**.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Data Models](#data-models)
- [Enums & Constants](#enums--constants)
- [Authentication](#authentication)
- [API Reference](#api-reference)
  - [Auth APIs](#auth-apis)
  - [Employee APIs](#employee-apis)
  - [Manager APIs](#manager-apis)
  - [Admin APIs](#admin-apis)
  - [Shared Goal APIs](#shared-goal-apis)
  - [Organization APIs](#organization-apis)
- [Business Rules & Validations](#business-rules--validations)
- [Goal Lifecycle](#goal-lifecycle)
- [Progress Score Computation](#progress-score-computation)
- [Quarterly Check-in Schedule](#quarterly-check-in-schedule)
- [Audit Logging](#audit-logging)
- [Shared Goals](#shared-goals)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)

---

## Overview

NorthStar replaces manual, siloed goal-tracking with a role-aware digital portal. Key capabilities include:

- **Goal creation** with thrust areas, UoM types, weightage, and targets
- **Manager approval workflow** with inline editing, approval, and return-for-rework
- **Quarterly check-ins** with structured achievement logging and system-computed progress scores
- **Shared Goals** — departmental KPIs pushed by Admin/Manager to multiple employees, with achievement sync
- **Audit trail** for all post-lock changes
- **Organization hierarchy** view for structural clarity

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python) |
| **Database** | MongoDB (via Motor — async driver) |
| **Cache** | Redis |
| **Auth** | JWT (python-jose) · bcrypt (passlib) |
| **Data Validation** | Pydantic v2 |
| **Server** | Uvicorn (ASGI) |
| **Password Hashing** | SHA-256 pre-hash → bcrypt |

---

## Project Structure

```
app/
├── main.py                     # FastAPI app entrypoint, router registration, CORS
├── core/
│   ├── auth.py                 # JWT access & refresh token creation
│   ├── config.py               # Settings loaded from .env
│   └── security.py             # Password hashing & verification
├── db/
│   └── database.py             # MongoDB + Redis clients, index creation
├── audit/
│   └── logs.py                 # Centralized audit log writer
├── constants/
│   └── enums.py                # All enumerations (Role, GoalStatus, UOMType, etc.)
├── models/
│   ├── user_model.py           # User Pydantic model
│   └── goal_model.py           # Goal Pydantic model
├── schemas/
│   ├── auth_schema.py          # Register & Login request schemas
│   ├── goal_schema.py          # Goal request/response schemas
│   ├── shared_goal_schema.py   # Shared goal schemas
│   └── organization_schema.py  # Org hierarchy schema
├── dependencies/
│   ├── auth_dependency.py      # get_current_user — JWT bearer extraction
│   └── role_dependency.py      # Role guards: require_employee/manager/admin
├── routes/
│   ├── auth_routes.py
│   ├── employee_router.py
│   ├── manager_router.py
│   ├── admin_router.py
│   ├── shared_goal_router.py
│   └── organization_routes.py
└── services/
    ├── auth_service.py
    ├── employee_service.py
    ├── manager_service.py
    ├── admin_service.py
    ├── shared_goal_service.py
    └── organization_service.py
```

---

## Architecture

```
Client (Browser / API Consumer)
        │
        ▼
   FastAPI Gateway  (NorthStar API — port configurable via .env)
        │
        ├── JWT Middleware (HTTPBearer)
        ├── Role Guards (Employee / Manager / Admin)
        │
        ├── Auth Routes          /auth/*
        ├── Employee Routes      /employee/goals/*
        ├── Manager Routes       /manager/goals/*
        ├── Admin Routes         /admin/goals/*
        ├── Shared Goal Routes   /shared-goals/*
        └── Organization Routes  /organization/*
                │
                ▼
         MongoDB (Motor async)
           └── NorthStarDB
                 ├── users
                 ├── goals
                 └── logs
                │
                ▼
         Redis (sync client, ready for caching)
```

**MongoDB Indexes:**

| Collection | Index Field | Unique |
|---|---|---|
| users | email | ✅ |
| users | employee_id | ✅ |
| users | manager_id | — |
| goals | status | — |
| goals | employee_id | — |
| goals | manager_id | — |
| goals | source_goal_id | — |
| goals | is_shared | — |
| logs | timestamp | — |
| logs | user_id | — |

---

## Data Models

### User

```
employee_id    str            Unique employee identifier
name           str            Full name (2–100 chars)
age            int            18–80
gender         Gender         MALE | FEMALE | OTHER
phone          str
email          EmailStr       Unique
department     str
designation    str
role           Role           EMPLOYEE | MANAGER | ADMIN | HR
manager_id     str?           Employee ID of reporting manager
hashed_password str           bcrypt hash of SHA-256(password)
is_active      bool           Default: true
```

### Goal

```
employee_id        str
employee_name      str
manager_id         str
thrust_area        str
title              str
description        str?
uom_type           UOMType       NUMERIC | PERCENTAGE | TIMELINE | ZERO_BASED
measurement_type   MeasurementType  MIN | MAX
target_value       float
weightage          int           10–100
target_date        datetime?
status             GoalStatus    DRAFT | SUBMITTED | RETURNED | LOCKED
manager_note       str?
approver_id        str?
approver_name      str?
is_shared          bool          Default: false
primary_owner_id   str?          Employee ID of the shared goal creator
progress_percentage float?
quarter            dict          { "1": CheckinParams, "2": ..., ... }
submitted_at       datetime?
approved_at        datetime?
returned_at        datetime?
created_at         datetime
updated_at         datetime
```

### CheckinParams (nested in Goal.quarter)

```
achievement_value   float
progress_status     ProgressStatus   NOT_STARTED | ON_TRACK | COMPLETED
manager_note        str?
```

### Log Entry

```
user_id     str
action      str        e.g. CREATE_GOAL, APPROVE_GOAL, UNLOCK_GOAL
details     dict       Context-specific payload
timestamp   datetime
```

---

## Enums & Constants

```python
class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER  = "MANAGER"
    HR       = "HR"
    ADMIN    = "ADMIN"

class Gender(str, Enum):
    MALE   = "MALE"
    FEMALE = "FEMALE"
    OTHER  = "OTHER"

class GoalStatus(str, Enum):
    DRAFT     = "DRAFT"
    SUBMITTED = "SUBMITTED"
    RETURNED  = "RETURNED"
    LOCKED    = "LOCKED"

class ProgressStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    ON_TRACK    = "ON_TRACK"
    COMPLETED   = "COMPLETED"

class UOMType(str, Enum):
    NUMERIC    = "NUMERIC"
    PERCENTAGE = "PERCENTAGE"
    TIMELINE   = "TIMELINE"
    ZERO_BASED = "ZERO_BASED"

class MeasurementType(str, Enum):
    MIN = "MIN"   # Higher is better (e.g. Revenue)
    MAX = "MAX"   # Lower is better (e.g. TAT, Cost)
```

---

## Authentication

NorthStar uses **JWT Bearer tokens**. All protected routes require the header:

```
Authorization: Bearer <access_token>
```

### Token Details

| Token | Expiry | Secret |
|---|---|---|
| Access Token | 60 minutes | `JWT_SECRET` |
| Refresh Token | 7 days | `JWT_REFRESH_SECRET` |

**Access Token Payload:**
```json
{
  "sub": "employee_id",
  "role": "EMPLOYEE",
  "designation": "Software Engineer",
  "department": "Engineering",
  "iat": 1700000000,
  "exp": 1700003600
}
```

**Password hashing flow:**
```
plain_password  →  SHA-256(hex)  →  bcrypt hash  →  stored in DB
```
Verification reverses the same pre-hash before bcrypt comparison.

---

## API Reference

Base URL: `http://localhost:{GATEWAY_PORT}`

Interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

### Auth APIs

**Tag:** `Authentication APIs` · **Prefix:** `/auth`

---

#### `POST /auth/register`

Register a new user in the system.

**Request Body:**
```json
{
  "email": "alice@company.com",
  "employee_id": "EMP001",
  "name": "Alice Johnson",
  "age": 30,
  "gender": "FEMALE",
  "phone": "9876543210",
  "department": "Engineering",
  "designation": "Software Engineer",
  "role": "EMPLOYEE",
  "manager_id": "EMP010",
  "password": "SecurePass@123"
}
```

**Validations:**
- `name`: 2–100 characters
- `age`: 18–80
- `role`: must be one of `EMPLOYEE | MANAGER | ADMIN | HR`
- `email`: valid email format
- `employee_id` and `email` must be unique

**Response `200`:**
```json
{
  "message": "User Registered Successfully",
  "user_id": "<mongo_object_id>"
}
```

**Response `400`:**
```json
{ "detail": "<duplicate key or validation error>" }
```

---

#### `POST /auth/login`

Authenticate and receive tokens. Either `email` or `employee_id` is required.

**Request Body:**
```json
{
  "employee_id": "EMP001",
  "password": "SecurePass@123"
}
```

Or with email:
```json
{
  "email": "alice@company.com",
  "password": "SecurePass@123"
}
```

**Response `200`:**
```json
{
  "message": "Login Successfully",
  "response": {
    "user_id": "<mongo_object_id>",
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>",
    "user": {
      "employee_id": "EMP001",
      "name": "Alice Johnson",
      "role": "EMPLOYEE",
      "department": "Engineering",
      ...
    }
  }
}
```

**Response `400`:**
```json
{ "detail": "User does not exist" }
{ "detail": "Incorrect password" }
```

---

### Employee APIs

**Tag:** `Employee APIs` · **Prefix:** `/employee/goals`  
**Auth:** Bearer token required · **Role:** `EMPLOYEE` (enforced on write operations)

---

#### `GET /employee/goals/my`

Retrieve all goals belonging to the authenticated employee (all statuses).

**Response `200`:** Array of `ViewGoalResponse`
```json
[
  {
    "goal_id": "664abc123...",
    "employee_name": "Alice Johnson",
    "thrust_area": "Revenue Growth",
    "title": "Increase Q3 Sales",
    "description": "Achieve 15% growth in Q3",
    "uom_type": "NUMERIC",
    "measurement_type": "MIN",
    "target_value": 500000.0,
    "weightage": 30,
    "target_date": "2025-09-30T00:00:00Z",
    "achievement_value": null,
    "progress_percentage": null,
    "status": "DRAFT",
    "manager_note": null,
    "approver_name": null,
    "submitted_at": null,
    "approved_at": null,
    "returned_at": null,
    "created_at": "2025-05-01T10:00:00Z",
    "updated_at": "2025-05-01T10:00:00Z"
  }
]
```

---

#### `POST /employee/goals/`

Create a new goal in `DRAFT` status.

**Request Body:**
```json
{
  "thrust_area": "Revenue Growth",
  "title": "Increase Q3 Sales",
  "description": "Achieve 15% YoY growth",
  "uom_type": "NUMERIC",
  "measurement_type": "MIN",
  "target_value": 500000,
  "weightage": 30,
  "target_date": "2025-09-30T00:00:00Z",
  "progress_status": "NOT_STARTED"
}
```

**Field Rules:**
- `thrust_area`, `title`: 3–100 characters
- `description`: max 500 characters (optional)
- `target_value`: must be > 0
- `weightage`: 10–100
- `uom_type`: `NUMERIC | PERCENTAGE | TIMELINE | ZERO_BASED`
- `measurement_type`: `MIN | MAX`

**Response `200`:**
```json
{ "message": "Goal created successfully with ID: 664abc123..." }
```

**Response `400`:**
```json
{ "detail": "<validation error>" }
```

---

#### `PATCH /employee/goals/{goal_id}`

Update a goal. Only allowed when goal status is `DRAFT` or `RETURNED`.

For shared goals, fields `title`, `uom_type`, `measurement_type`, `target_value`, and `thrust_area` are **read-only** — use `PATCH /employee/goals/{goal_id}/weightage` for shared goal weightage.

**Path Param:** `goal_id` — MongoDB ObjectId

**Request Body (all fields optional):**
```json
{
  "thrust_area": "Cost Efficiency",
  "title": "Reduce Operational Cost",
  "description": "Cut costs by 10%",
  "uom_type": "PERCENTAGE",
  "measurement_type": "MAX",
  "target_value": 10.0,
  "weightage": 20,
  "target_date": "2025-12-31T00:00:00Z"
}
```

**Response `200`:**
```json
{ "message": "Goal updated successfully" }
```

**Response `400/403/404`:**
```json
{ "detail": "Only DRAFT or RETURNED goals can be updated" }
{ "detail": "Unauthorized to update this goal" }
{ "detail": "Goal not found" }
```

---

#### `DELETE /employee/goals/{goal_id}`

Delete a goal. Only allowed when status is `DRAFT`.

**Path Param:** `goal_id`

**Response `200`:**
```json
{ "message": "Goal deleted successfully" }
```

**Response `400/403/404`:**
```json
{ "detail": "Only DRAFT goals can be deleted" }
```

---

#### `POST /employee/goals/submit`

Submit a batch of goals for manager review. Triggers the 100% weightage validation.

**Request Body:**
```json
["664abc001", "664abc002", "664abc003"]
```

**Validation Logic:**
1. Retrieves all goals matching the provided IDs owned by the employee with status `DRAFT` or `RETURNED`
2. Fetches existing `LOCKED` and `SUBMITTED` goals for the employee
3. Total goal count (selected + locked + submitted) must not exceed **8**
4. Sum of weightages across all goals (selected + locked + submitted) must equal **100**

**Response `200`:**
```json
{ "message": "Goals submitted successfully" }
```

**Response `400`:**
```json
{ "detail": "Total goal weightage must equal 100" }
{ "detail": "Maximum 8 goals allowed including locked goals" }
{ "detail": "Select at least one goal" }
```

---

#### `PATCH /employee/goals/{goal_id}/quarterly-checkin`

Log quarterly achievement for a `LOCKED` goal. Progress percentage is auto-computed based on UoM and measurement type.

**Path Param:** `goal_id`

**Request Body:**
```json
{
  "quarter": {
    "1": {
      "achievement_value": 350000,
      "progress_status": "ON_TRACK"
    },
    "2": {
      "achievement_value": 420000,
      "progress_status": "ON_TRACK"
    }
  }
}
```

**Notes:**
- Multiple quarters can be updated in a single call
- `achievement_value` must be >= 0
- Progress is computed per UoM (see [Progress Score Computation](#progress-score-computation))
- If the goal is a shared goal and the updater is the `primary_owner`, achievement is **synced to all linked copies** automatically

**Response `200`:**
```json
{ "message": "Quarterly check-in updated successfully" }
```

---

#### `GET /employee/goals/my-shared-goals`

Retrieve all shared goal copies assigned to the authenticated employee.

**Response `200`:** Array of `SharedGoalResponse`
```json
[
  {
    "goal_id": "664abc999...",
    "source_goal_id": "664abc000...",
    "thrust_area": "Safety",
    "title": "Zero Incidents FY25",
    "uom_type": "ZERO_BASED",
    "measurement_type": "MIN",
    "target_value": 0.0,
    "weightage": 15,
    "is_shared": true,
    "primary_owner_id": "EMP010",
    "status": "DRAFT",
    ...
  }
]
```

---

#### `PATCH /employee/goals/{goal_id}/weightage`

Adjust the weightage of a shared goal copy. Only allowed when status is `DRAFT` or `RETURNED`. Title, target, and other fields remain read-only.

**Request Body:**
```json
{ "weightage": 20 }
```

**Validation:** `weightage` must be 10–100

**Response `200`:**
```json
{ "message": "Weightage updated successfully" }
```

---

### Manager APIs

**Tag:** `Manager APIs` · **Prefix:** `/manager/goals`  
**Auth:** Bearer token required · **Role:** `MANAGER`

---

#### `GET /manager/goals/review`

List all `SUBMITTED` goals awaiting review, grouped by employee name.

**Response `200`:**
```json
{
  "Alice Johnson": [
    {
      "goal_id": "664abc123...",
      "thrust_area": "Revenue Growth",
      "title": "Increase Q3 Sales",
      "weightage": 30,
      "status": "SUBMITTED",
      ...
    }
  ],
  "Bob Smith": [...]
}
```

**Response `404`:**
```json
{ "detail": "No goals found for review" }
```

---

#### `POST /manager/goals/{goal_id}/approve`

Approve a submitted goal, optionally tweaking `target_value` or `weightage` inline before locking.

**Path Param:** `goal_id`

**Request Body (optional):**
```json
{
  "target_value": 550000,
  "weightage": 35
}
```

If `tweaks` is not provided or a field is omitted, the original goal value is preserved.

**Effect:** Goal status transitions to `LOCKED`. `approver_id`, `approver_name`, and `approved_at` are set.

**Response `200`:**
```json
{ "message": "Goal approved successfully" }
```

**Response `400/403/404`:**
```json
{ "detail": "Only SUBMITTED goals can be approved" }
{ "detail": "Unauthorized to approve this goal" }
```

---

#### `POST /manager/goals/{goal_id}/return`

Return a submitted goal to the employee for rework, with an optional note.

**Path Param:** `goal_id`

**Request Body:**
```json
{ "manager_note": "Please revise the target value to be more realistic." }
```

**Effect:** Goal status transitions to `RETURNED`. `manager_note` and `returned_at` are set.

**Response `200`:**
```json
{ "message": "Goal returned successfully" }
```

---

#### `GET /manager/goals/`

List all `LOCKED` (approved) goals for the manager's team, grouped by employee name.

**Response `200`:** Same structure as `/review` but filtered to `LOCKED` status.

---

#### `POST /manager/goals/{goal_id}/comment`

Add a structured check-in comment to a specific quarter of an employee's goal.

**Path Param:** `goal_id`

**Query Params:**
- `quarter` (int, required): 1 | 2 | 3 | 4
- `comment` (str, required): The comment text

**Example:**
```
POST /manager/goals/664abc123.../comment?quarter=2&comment=Good+progress+so+far
```

**Validation:**
- Quarter must be one of 1, 2, 3, 4
- The specified quarter check-in must already exist (employee must have submitted a check-in for that quarter first)
- Manager must own the goal (matched via `manager_id`)

**Response `200`:**
```json
{ "message": "Comment added for Q2" }
```

**Response `400`:**
```json
{ "detail": "Q2 check-in not found" }
```

---

### Admin APIs

**Tag:** `Admin APIs` · **Prefix:** `/admin/goals`  
**Auth:** Bearer token required · **Role:** `ADMIN`

---

#### `PATCH /admin/goals/{goal_id}/unlock`

Unlock a `LOCKED` goal — transitions it back to `RETURNED` so the employee can edit and resubmit. All changes are audit-logged.

**Path Param:** `goal_id`

**Response `200`:**
```json
{ "message": "Goal unlocked successfully" }
```

**Response `400`:**
```json
{ "detail": "Only LOCKED goals can be unlocked" }
{ "detail": "Invalid goal ID" }
```

**Response `404`:**
```json
{ "detail": "Goal not found" }
```

---

#### `GET /admin/goals/logs`

Retrieve the audit log (most recent 100 entries). Supports optional filtering by action type or user.

**Query Params (all optional):**
- `action` (str): Filter by action type, e.g. `APPROVE_GOAL`, `UNLOCK_GOAL`
- `user_id` (str): Filter by the employee ID who performed the action

**Example:**
```
GET /admin/goals/logs?action=UNLOCK_GOAL&user_id=EMP001
```

**Response `200`:** Array of log entries
```json
[
  {
    "_id": "664log001...",
    "user_id": "EMP001",
    "action": "UNLOCK_GOAL",
    "details": {
      "goal_id": "664abc123...",
      "previous_status": "LOCKED",
      "new_status": "RETURNED"
    },
    "timestamp": "2025-06-01T12:34:56Z"
  }
]
```

---

### Shared Goal APIs

**Tag:** `Shared Goal APIs` · **Prefix:** `/shared-goals`  
**Auth:** Bearer token required · **Role:** `ADMIN` or `MANAGER`

---

#### `POST /shared-goals/push`

Push a departmental KPI to multiple employees at once. Each recipient gets their own copy of the goal in `DRAFT` status. Recipients can only adjust weightage — title, target, and UoM are read-only.

**Request Body:**
```json
{
  "recipient_employee_ids": ["EMP002", "EMP003", "EMP004"],
  "thrust_area": "Safety",
  "title": "Zero Incidents FY25",
  "description": "Maintain zero safety incidents throughout the financial year",
  "uom_type": "ZERO_BASED",
  "measurement_type": "MIN",
  "target_value": 0,
  "default_weightage": 15,
  "target_date": "2026-03-31T00:00:00Z"
}
```

**Validation:**
- All `recipient_employee_ids` must correspond to active `EMPLOYEE` role users
- `default_weightage`: 10–100
- `target_value`: > 0

**Response `200`:**
```json
{
  "message": "Shared goal pushed to 3 employee(s)",
  "source_goal_id": "664src001...",
  "recipient_count": 3,
  "recipients": ["EMP002", "EMP003", "EMP004"]
}
```

**Response `400`:**
```json
{ "detail": "These employee IDs were not found or are not active employees: ['EMP999']" }
```

---

#### `GET /shared-goals/pushed`

View all shared goals pushed by the authenticated manager/admin. Admins see all pushed shared goals; managers see only goals they pushed.

**Response `200`:** Array of `SharedGoalResponse`

---

### Organization APIs

**Tag:** `Organization APIs` · **Prefix:** `/organization`  
**Auth:** Bearer token required (any authenticated user)

---

#### `GET /organization/hierarchy`

Returns the full organization hierarchy as a tree structure based on `manager_id` relationships stored in the users collection.

**Algorithm:**
1. Fetches all active users
2. Builds a map of `employee_id → node`
3. Attaches each node as a child of its manager
4. Nodes with no manager (or self-referencing) become root nodes

**Response `200`:** Array of `HierarchyNode` (recursive tree)
```json
[
  {
    "employee_id": "EMP010",
    "name": "Carol Director",
    "designation": "Engineering Director",
    "department": "Engineering",
    "role": "MANAGER",
    "children": [
      {
        "employee_id": "EMP001",
        "name": "Alice Johnson",
        "designation": "Software Engineer",
        "department": "Engineering",
        "role": "EMPLOYEE",
        "children": []
      }
    ]
  }
]
```

---

## Business Rules & Validations

### Goal Creation
- Minimum weightage per goal: **10%**
- Maximum weightage per goal: **100%**
- Minimum thrust area / title length: **3 characters**

### Goal Submission
- Total weightage across all active goals (DRAFT + SUBMITTED + LOCKED) must equal **100%**
- Maximum **8 goals** per employee (combined DRAFT + SUBMITTED + LOCKED)
- At least **1 goal** must be selected for submission

### Goal Editing
- Only `DRAFT` or `RETURNED` goals can be edited or deleted
- Shared goal copies: only `weightage` can be changed; all other fields are locked

### Goal Approval (Manager)
- Only goals in `SUBMITTED` status can be approved or returned
- Manager can only act on goals where `manager_id` matches their own `employee_id`
- On approval, manager may optionally override `target_value` and/or `weightage`
- Approved goals transition to `LOCKED` — no further edits without Admin intervention

### Goal Unlock (Admin)
- Only `LOCKED` goals can be unlocked
- Unlock transitions status back to `RETURNED`
- All unlock events are audit-logged with before/after status

### Quarterly Check-in
- Only `LOCKED` goals can receive check-in updates
- Employee must own the goal
- Progress is auto-computed — see formula table below

---

## Goal Lifecycle

```
                       ┌─────────────────────────────────────┐
                       │              EMPLOYEE                │
                       └─────────────────────────────────────┘
                                        │
                              create_goal()
                                        │
                                        ▼
                                    [ DRAFT ] ◄──────────────────────────┐
                                        │                                 │
                              submit_goals()                              │
                                        │                                 │
                                        ▼                                 │
                                  [ SUBMITTED ]                           │
                                        │                                 │
                          ┌─────────────────────────┐                    │
                          │         MANAGER          │                    │
                          └─────────────────────────┘                    │
                                        │                                 │
                          approve_goal() │ return_goal()                  │
                                        │                                 │
                     ┌──────────────────┴─────────────────┐              │
                     ▼                                      ▼             │
                [ LOCKED ]                           [ RETURNED ]─────────┘
                     │
         quarterly_checkin() [Employee]
         comment_on_goal()   [Manager]
                     │
         unlock_goal()  [Admin only]
                     │
                     ▼
               [ RETURNED ] → Employee can re-edit & resubmit
```

---

## Progress Score Computation

Progress percentage is computed automatically during quarterly check-in based on the goal's `uom_type` and `measurement_type`:

| UoM Type | Measurement | Description | Formula |
|---|---|---|---|
| `NUMERIC` / `PERCENTAGE` | `MIN` | Higher is better (e.g. Sales Revenue) | `(achievement / target) × 100` |
| `NUMERIC` / `PERCENTAGE` | `MAX` | Lower is better (e.g. TAT, Cost) | `(target / achievement) × 100` |
| `NUMERIC` / `PERCENTAGE` | `MAX` | Achievement is zero (perfect) | `100%` |
| `ZERO_BASED` | — | Zero = Success (e.g. Safety incidents) | `achievement == 0 → 100%, else 0%` |
| `TIMELINE` | — | Date-based completion | `achievement_value` used directly as % |

> Note: Progress percentage is a **tracking metric only** — it is not used for formal ratings.

---

## Quarterly Check-in Schedule

| Period | Window Opens | Action |
|---|---|---|
| **Phase 1 — Goal Setting** | 1st May | Goal Creation, Submission & Approval |
| **Q1 Check-in** | July | Progress Update — Planned vs. Actual |
| **Q2 Check-in** | October | Progress Update — Planned vs. Actual |
| **Q3 Check-in** | January | Progress Update — Planned vs. Actual |
| **Q4 / Annual** | March / April | Final Achievement Capture |

---

## Audit Logging

Every significant action is recorded in the `logs` collection via `log_action()`:

| Action | Triggered By |
|---|---|
| `CREATE_GOAL` | Employee creates a goal |
| `UPDATE_GOAL` | Employee updates a goal |
| `DELETE_GOAL` | Employee deletes a draft goal |
| `SUBMIT_GOALS` | Employee submits goals for review |
| `APPROVE_GOAL` | Manager approves a goal |
| `RETURN_GOAL` | Manager returns a goal for rework |
| `COMMENT_ON_GOAL` | Manager adds a check-in comment |
| `UNLOCK_GOAL` | Admin unlocks a locked goal |
| `PUSH_SHARED_GOAL` | Admin/Manager pushes a shared goal |
| `UPDATE_SHARED_GOAL_WEIGHTAGE` | Employee adjusts shared goal weightage |
| `QUARTERLY_CHECKIN` | Employee logs quarterly achievement |
| `SYNC_SHARED_ACHIEVEMENT` | System syncs achievement to shared goal copies |

Each log entry stores: `user_id`, `action`, `details` (context-specific dict), and `timestamp`.

---

## Shared Goals

The Shared Goal feature allows an Admin or Manager to broadcast a departmental KPI to multiple employees simultaneously.

**How it works:**

1. Pusher calls `POST /shared-goals/push` with a list of `recipient_employee_ids`
2. A `source_goal_id` (ObjectId) is generated — this is the logical parent identifier shared across all copies
3. Each recipient gets their own goal document with `is_shared: true` and `source_goal_id` set
4. Recipients can only adjust `weightage` on their copy via `PATCH /employee/goals/{goal_id}/weightage`
5. All other fields (`title`, `target_value`, `uom_type`, `thrust_area`) are enforced read-only
6. When the **primary owner** logs a quarterly check-in, `sync_shared_achievement()` propagates `achievement_value`, `progress_percentage`, and `quarter` data to all other LOCKED copies of the same shared goal

---

## Environment Variables

Create a `.env` file in the project root:

```env
GATEWAY_PORT=8000
JWT_SECRET=NorthStarSecretKey
JWT_REFRESH_SECRET=NorthStarRefreshSecretKey
MONGO_URI=mongodb://localhost:27017/
REDIS_HOST=localhost
REDIS_PORT=6379
```

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_PORT` | `8000` | Port for the FastAPI server |
| `JWT_SECRET` | `NorthStarSecretKey` | Secret for signing access tokens |
| `JWT_REFRESH_SECRET` | `NorthStarRefreshSecretKey` | Secret for signing refresh tokens |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |

---

## Running the Project

### Prerequisites

- Python 3.10+
- MongoDB running locally or via Atlas
- Redis running locally

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start the server

```bash
python -m app.main
```

Or directly with uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Docs

Once running, open:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/`

---

## User Role Quick Reference

| Capability | Employee | Manager | Admin |
|---|---|---|---|
| Register / Login | ✅ | ✅ | ✅ |
| Create / Edit / Delete goals | ✅ | — | — |
| Submit goals for approval | ✅ | — | — |
| Log quarterly check-in | ✅ | — | — |
| View own shared goals | ✅ | — | — |
| Adjust shared goal weightage | ✅ | — | — |
| Review submitted goals | — | ✅ | — |
| Approve / Return goals | — | ✅ | — |
| Inline edit on approval | — | ✅ | — |
| Add check-in comments | — | ✅ | — |
| Push shared goals | — | ✅ | ✅ |
| View pushed shared goals | — | ✅ | ✅ |
| Unlock locked goals | — | — | ✅ |
| View audit logs | — | — | ✅ |
| View org hierarchy | ✅ | ✅ | ✅ |

---

*NorthStar — Built for AtomQuest Hackathon 1.0*
