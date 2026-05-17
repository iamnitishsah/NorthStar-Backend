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
- [User Role Quick Reference](#user-role-quick-reference)

---

## Overview

NorthStar replaces manual, siloed goal-tracking with a role-aware digital portal. Key capabilities include:

- **Goal creation** with thrust areas, UoM types, weightage, and targets
- **Manager approval workflow** with inline editing, approval, and return-for-rework
- **Quarterly check-ins** with structured achievement logging and system-computed progress scores
- **Shared Goals** — departmental KPIs pushed by Admin/Manager to multiple employees, with automatic achievement sync
- **Audit trail** for all significant actions and post-lock changes
- **Organization hierarchy** view built dynamically from `manager_id` relationships

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python) |
| **Database** | MongoDB (via Motor — async driver) |
| **Cache** | Redis (client initialized, ready for caching layer) |
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
│   └── security.py             # Password hashing & verification (SHA-256 + bcrypt)
├── db/
│   └── database.py             # MongoDB + Redis clients, index creation
├── audit/
│   └── logs.py                 # Centralized audit log writer
├── constants/
│   └── enums.py                # All enumerations (Role, GoalStatus, UOMType, etc.)
├── models/
│   ├── user_model.py           # User Pydantic model (stored shape)
│   └── goal_model.py           # Goal Pydantic model (stored shape)
├── schemas/
│   ├── auth_schema.py          # Register & Login request/response schemas
│   ├── goal_schema.py          # Goal create/update/view/check-in schemas
│   ├── shared_goal_schema.py   # Shared goal push/update/response schemas
│   └── organization_schema.py  # Org hierarchy recursive node schema
├── dependencies/
│   ├── auth_dependency.py      # get_current_user — JWT bearer extraction & DB lookup
│   └── role_dependency.py      # Role guards: require_employee / require_manager / require_admin
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
        ├── JWT Middleware (HTTPBearer — validates every protected request)
        ├── Role Guards   (require_employee / require_manager / require_admin)
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
                 ├── users      — user profiles, credentials, manager links
                 ├── goals      — all goal documents (personal + shared copies)
                 └── logs       — append-only audit log
                │
                ▼
         Redis (sync client, available for caching/rate-limiting)
```

### MongoDB Indexes

| Collection | Field | Unique |
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

Indexes are created automatically at application startup via the `startup` event handler in `main.py`.

---

## Data Models

### User

| Field | Type | Notes |
|---|---|---|
| `employee_id` | str | Unique employee identifier |
| `name` | str | Full name (2–100 chars) |
| `age` | int | 18–80 |
| `gender` | Gender | `MALE \| FEMALE \| OTHER` |
| `phone` | str | Contact number |
| `email` | EmailStr | Unique |
| `department` | str | Organizational department |
| `designation` | str | Job title |
| `role` | Role | `EMPLOYEE \| MANAGER \| ADMIN \| HR` |
| `manager_id` | str? | `employee_id` of the reporting manager |
| `hashed_password` | str | bcrypt hash of SHA-256(password) |
| `is_active` | bool | Default: `true` |
| `last_login` | datetime? | Updated on each successful login |

### Goal

| Field | Type | Notes |
|---|---|---|
| `employee_id` | str | Owner's employee ID |
| `employee_name` | str | Denormalized for display |
| `manager_id` | str | Manager who reviews this goal |
| `thrust_area` | str | Strategic area (3–100 chars) |
| `title` | str | Goal title (3–100 chars) |
| `description` | str? | Optional detail (max 500 chars) |
| `uom_type` | UOMType | `NUMERIC \| PERCENTAGE \| TIMELINE \| ZERO_BASED` |
| `measurement_type` | MeasurementType | `MIN \| MAX` |
| `target_value` | float | Must be > 0 |
| `weightage` | int | 10–100 |
| `target_date` | datetime? | Required for `TIMELINE` goals |
| `status` | GoalStatus | `DRAFT → SUBMITTED → LOCKED` (see lifecycle) |
| `manager_note` | str? | Note set on return or cleared on approval |
| `approver_id` | str? | Employee ID of approving manager |
| `approver_name` | str? | Denormalized approver name |
| `is_shared` | bool | `true` for shared goal copies |
| `source_goal_id` | ObjectId? | Links shared copies to their logical parent |
| `primary_owner_id` | str? | Employee ID of the shared goal pusher |
| `primary_owner_name` | str? | Denormalized name of pusher |
| `source_snapshot` | dict? | Immutable copy of original shared goal fields |
| `achievement_value` | float/str? | Latest logged achievement |
| `progress_percentage` | float? | Auto-computed from achievement |
| `progress_status` | ProgressStatus? | `NOT_STARTED \| ON_TRACK \| COMPLETED` |
| `quarter` | dict | `{ "1": CheckinParams, "2": ..., ... }` |
| `submitted_at` | datetime? | |
| `approved_at` | datetime? | |
| `returned_at` | datetime? | |
| `created_at` | datetime | Auto-set |
| `updated_at` | datetime | Auto-updated on every write |

### CheckinParams (nested in `Goal.quarter`)

| Field | Type | Notes |
|---|---|---|
| `achievement_value` | float \| str | Numeric or ISO date string for TIMELINE |
| `progress_status` | ProgressStatus | `NOT_STARTED \| ON_TRACK \| COMPLETED` |
| `progress_percentage` | float | Auto-computed |
| `manager_note` | str? | Added by manager via check-in comment |
| `updated_at` | datetime | Timestamp of this quarter's update |

### Log Entry

| Field | Type | Notes |
|---|---|---|
| `user_id` | str | employee_id of the actor |
| `action` | str | e.g. `CREATE_GOAL`, `APPROVE_GOAL` |
| `details` | dict | Context-specific payload |
| `timestamp` | datetime | UTC timestamp |

---

## Enums & Constants

```python
class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER  = "MANAGER"
    HR       = "HR"           # Registered but no dedicated routes currently
    ADMIN    = "ADMIN"

class Gender(str, Enum):
    MALE   = "MALE"
    FEMALE = "FEMALE"
    OTHER  = "OTHER"

class GoalStatus(str, Enum):
    DRAFT          = "DRAFT"
    SUBMITTED      = "SUBMITTED"
    RETURNED       = "RETURNED"
    ADMIN_UNLOCKED = "ADMIN_UNLOCKED"   # Unlocked by admin; treated like RETURNED for edits
    LOCKED         = "LOCKED"           # Approved; requires admin to edit

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
    MIN = "MIN"   # Higher is better (e.g. Revenue, Units Sold)
    MAX = "MAX"   # Lower is better (e.g. TAT, Cost, Errors)
```

---

## Authentication

NorthStar uses **JWT Bearer tokens**. All protected routes require the header:

```
Authorization: Bearer <access_token>
```

### Token Details

| Token | Expiry | Secret Env Var |
|---|---|---|
| Access Token | 60 minutes | `JWT_SECRET` |
| Refresh Token | 7 days | `JWT_REFRESH_SECRET` |

**Access Token Payload:**
```json
{
  "sub": "EMP001",
  "role": "EMPLOYEE",
  "designation": "Software Engineer",
  "department": "Engineering",
  "iat": 1700000000,
  "exp": 1700003600
}
```

**Password hashing flow:**
```
plain_password → SHA-256(hex) → bcrypt hash → stored in DB
```
On login, the same SHA-256 pre-hash is applied before bcrypt comparison, preventing length extension attacks and ensuring consistent hashing.

**Token validation flow (`get_current_user`):**
1. Extract Bearer token from `Authorization` header
2. Decode and verify JWT signature using `JWT_SECRET`
3. Look up the user in MongoDB by `employee_id` from the `sub` claim
4. Return the full user document to downstream route handlers

---

## API Reference

**Base URL:** `http://localhost:{GATEWAY_PORT}`

Interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

### Auth APIs

**Tag:** `Authentication APIs` · **Prefix:** `/auth`

---

#### `POST /auth/register`

Register a new user. `employee_id` and `email` must both be unique across the system.

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

**Field Rules:**
- `name`: 2–100 characters
- `age`: 18–80
- `role`: one of `EMPLOYEE | MANAGER | ADMIN | HR`
- `email`: valid email format, unique
- `employee_id`: unique
- `manager_id`: optional; should be the `employee_id` of the reporting manager

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

Authenticate and receive tokens. Provide either `email` or `employee_id` — at least one is required (enforced by `model_validator`).

**Request Body (by employee ID):**
```json
{
  "employee_id": "EMP001",
  "password": "SecurePass@123"
}
```

**Request Body (by email):**
```json
{
  "email": "alice@company.com",
  "password": "SecurePass@123"
}
```

If both are provided, `employee_id` takes priority.

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
      "designation": "Software Engineer",
      "email": "alice@company.com"
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
**Auth:** Bearer token required. Write operations additionally enforce `role == EMPLOYEE`.

---

#### `GET /employee/goals/my`

Retrieve all **personal** goals for the authenticated employee (all statuses, excluding shared goal copies).

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
    "progress_status": null,
    "quarter": {},
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

Create a new goal in `DRAFT` status. The `manager_id` is automatically derived from the authenticated user's profile.

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
- `progress_status`: optional, defaults to `NOT_STARTED`

**Validation:**
- Employee must not already have 8 or more active goals (status in `DRAFT | RETURNED | ADMIN_UNLOCKED | SUBMITTED | LOCKED`)

**Response `200`:**
```json
{ "message": "Goal created successfully with ID: 664abc123..." }
```

**Response `400`:**
```json
{ "detail": "Maximum 8 goals allowed per employee" }
```

---

#### `PATCH /employee/goals/{goal_id}`

Update a goal. Allowed only when the goal status is `DRAFT`, `RETURNED`, or `ADMIN_UNLOCKED`.

For shared goal copies, the fields `title`, `uom_type`, `measurement_type`, `target_value`, `thrust_area`, and `weightage` are read-only. Attempting to update them returns a `403`. Use `PATCH /employee/goals/{goal_id}/weightage` for shared goal weightage.

**Path Param:** `goal_id` — MongoDB ObjectId string

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

Only provided (non-null) fields are applied.

**Response `200`:**
```json
{ "message": "Goal updated successfully" }
```

**Response `400` / `403` / `404`:**
```json
{ "detail": "Only DRAFT or RETURNED goals can be updated" }
{ "detail": "Unauthorized to update this goal" }
{ "detail": "Goal not found" }
{ "detail": "Shared goal fields are read-only: ['title']. Use PATCH /shared-goals/{goal_id}/weightage to adjust weightage." }
```

---

#### `DELETE /employee/goals/{goal_id}`

Permanently delete a goal. Only allowed when status is `DRAFT`. An audit log entry is written before deletion.

**Path Param:** `goal_id`

**Response `200`:**
```json
{ "message": "Goal deleted successfully" }
```

**Response `400`:**
```json
{ "detail": "Only DRAFT goals can be deleted" }
```

---

#### `POST /employee/goals/submit`

Submit a batch of goals for manager review. This triggers the 100% weightage validation across all active goals.

**Request Body:** JSON array of goal ID strings
```json
["664abc001", "664abc002", "664abc003"]
```

**Validation Logic (in order):**
1. Fetches all goals matching the provided IDs that belong to the employee with status `DRAFT`, `RETURNED`, or `ADMIN_UNLOCKED`
2. Fetches all existing `LOCKED` goals for the employee (already approved)
3. Validates that each selected goal has `weightage >= 10`
4. For shared goal copies, validates that mutable fields match the `source_snapshot` (title, thrust_area, uom_type, measurement_type, target_value, target_date must not have been altered)
5. Total goal count (selected + locked) must not exceed **8**
6. Sum of weightages across **all** goals (selected + locked) must equal exactly **100**

**Response `200`:**
```json
{ "message": "Goals submitted successfully" }
```

**Response `400`:**
```json
{ "detail": "Total goal weightage must equal 100" }
{ "detail": "Maximum 8 goals allowed including locked goals" }
{ "detail": "Select at least one goal" }
{ "detail": "Each submitted goal must have minimum weightage of 10" }
{ "detail": { "message": "Shared goal fields must match the original shared goal", "goal_ids": ["..."] } }
```

---

#### `PATCH /employee/goals/{goal_id}/quarterly-checkin`

Log quarterly achievement for a `LOCKED` goal. Progress percentage is auto-computed per the goal's UoM and measurement type. **Only one quarter can be updated per request**, and it must be the next sequential quarter.

Quarter updates are appended without overwriting existing quarters; previously submitted quarters remain intact.

If the goal is a shared goal and the authenticated user is the `primary_owner`, achievement data is automatically synced to all other locked copies of the same shared goal.

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

For `TIMELINE` goals, `achievement_value` must be an ISO date string (`"YYYY-MM-DD"` or `"YYYY-MM-DDTHH:MM:SS"`).

After the update, the goal-level `achievement_value` and `progress_percentage` are set to the values from the **latest** quarter submitted (highest quarter key).

**Response `200`:**
```json
{ "message": "Quarterly check-in updated successfully" }
```

**Response `400` / `403`:**
```json
{ "detail": "Only LOCKED goals can be updated in quarterly check-in" }
{ "detail": "Unauthorized to update this goal" }
{ "detail": "Achievement value must be positive" }
{ "detail": "Target date is required for TIMELINE goals" }
{ "detail": "Invalid completion date format; use ISO YYYY-MM-DD" }
```

---

#### `GET /employee/goals/my-shared-goals`

Retrieve all shared goal copies assigned to the authenticated employee (all statuses).

**Response `200`:** Array of `SharedGoalResponse`

```json
[
  {
    "goal_id": "664abc999...",
    "source_goal_id": "664abc000...",
    "thrust_area": "Safety",
    "title": "Zero Incidents FY25",
    "description": "Maintain zero safety incidents throughout FY",
    "uom_type": "ZERO_BASED",
    "measurement_type": "MIN",
    "target_value": 1.0,
    "weightage": 15,
    "target_date": "2026-03-31T00:00:00Z",
    "employee_name": "Alice Johnson",
    "primary_owner_id": "EMP010",
    "is_shared": true,
    "achievement_value": null,
    "progress_percentage": null,
    "progress_status": null,
    "status": "DRAFT",
    "approver_name": null,
    "submitted_at": null,
    "approved_at": null,
    "created_at": "2025-05-01T09:00:00Z",
    "updated_at": "2025-05-01T09:00:00Z"
  }
]
```

---

#### `PATCH /employee/goals/{goal_id}/weightage`

Adjust the weightage of a shared goal copy. Only allowed when status is `DRAFT` or `RETURNED`. Title, target, UoM, and all other fields remain read-only.

**Path Param:** `goal_id`

**Request Body:**
```json
{ "weightage": 20 }
```

**Validation:** `weightage` must be 10–100

**Response `200`:**
```json
{ "message": "Weightage updated successfully" }
```

**Response `400` / `403`:**
```json
{ "detail": "This endpoint is only for shared goals" }
{ "detail": "Weightage can only be changed while the goal is DRAFT or RETURNED" }
{ "detail": "Unauthorized" }
```

---

### Manager APIs

**Tag:** `Manager APIs` · **Prefix:** `/manager/goals`
**Auth:** Bearer token required · **Role:** `MANAGER` enforced on all routes.

---

#### `GET /manager/goals/review`

List all `SUBMITTED` goals awaiting manager review, grouped by employee name. Only goals where `manager_id` matches the authenticated manager's `employee_id` are returned.

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
      "submitted_at": "2025-05-03T08:00:00Z",
      ...
    }
  ],
  "Bob Smith": [ ... ]
}
```

**Response `404`:**
```json
{ "detail": "No goals found for review" }
```

---

#### `POST /manager/goals/{goal_id}/approve`

Approve a submitted goal, optionally tweaking `target_value` or `weightage` inline before locking. The manager can only approve goals assigned to them.

**Path Param:** `goal_id`

**Request Body (optional — omit or pass `null` to keep original values):**
```json
{
  "target_value": 550000,
  "weightage": 35
}
```

**Effect on approval:**
- Goal status transitions to `LOCKED`
- `approver_id`, `approver_name`, and `approved_at` are set
- `manager_note` is cleared (set to `null`)
- Any tweaked `target_value` or `weightage` is persisted

**Validation:**
- Only `SUBMITTED` goals can be approved
- Manager must be the goal's assigned manager (`manager_id` match)
- Tweaked `weightage` must be 10–100

**Response `200`:**
```json
{ "message": "Goal approved successfully" }
```

**Response `400` / `403` / `404`:**
```json
{ "detail": "Only SUBMITTED goals can be approved" }
{ "detail": "Unauthorized to approve this goal" }
{ "detail": "Weightage must be between 10 and 100" }
```

---

#### `POST /manager/goals/{goal_id}/return`

Return a submitted goal to the employee for rework, with an optional explanatory note.

**Path Param:** `goal_id`

**Request Body:**
```json
{ "manager_note": "Please revise the target value to be more realistic." }
```

**Effect on return:**
- Goal status transitions to `RETURNED`
- `manager_note` and `returned_at` are set
- Employee can then edit and resubmit

**Response `200`:**
```json
{ "message": "Goal returned successfully" }
```

**Response `400` / `403` / `404`:**
```json
{ "detail": "Only SUBMITTED goals can be returned" }
{ "detail": "Unauthorized to return this goal" }
```

---

#### `GET /manager/goals/`

List all `LOCKED` (approved) goals for the manager's team, grouped by employee name.

**Response `200`:** Same structure as `/review` but filtered to `LOCKED` status.

**Response `404`:**
```json
{ "detail": "No goals found for this manager" }
```

---

#### `POST /manager/goals/{goal_id}/comment`

Add a structured check-in comment to a specific quarter of a `LOCKED` goal. The quarter check-in must already exist (the employee must have submitted a check-in for that quarter first).

**Path Param:** `goal_id`

**Request Body:**
```json
{
  "quarter": 2,
  "comment": "Good progress so far. Keep tracking daily numbers."
}
```

**Validation:**
- `quarter` must be `1 | 2 | 3 | 4`
- The specified quarter must already exist in `goal.quarter` (employee must have done the check-in first)
- Manager must be the goal's assigned manager

**Effect:** Sets `goal.quarter.<N>.manager_note` to the provided comment.

**Response `200`:**
```json
{ "message": "Comment added for Q2" }
```

**Response `400` / `403`:**
```json
{ "detail": "Q2 check-in not found" }
{ "detail": "Invalid quarter" }
{ "detail": "Unauthorized to comment on this goal" }
```

---

### Admin APIs

**Tag:** `Admin APIs` · **Prefix:** `/admin/goals`
**Auth:** Bearer token required · **Role:** `ADMIN` enforced on all routes.

---

#### `PATCH /admin/goals/{goal_id}/unlock`

Unlock a `LOCKED` goal, transitioning it to `ADMIN_UNLOCKED`. This allows the employee to edit and resubmit without a full manager re-approval cycle from scratch. All unlock events are audit-logged with before/after status.

**Path Param:** `goal_id`

**Response `200`:**
```json
{ "message": "Goal unlocked successfully" }
```

**Response `400` / `404`:**
```json
{ "detail": "Only LOCKED goals can be unlocked" }
{ "detail": "Invalid goal ID" }
{ "detail": "Goal not found" }
```

---

#### `GET /admin/goals/logs`

Retrieve the audit log (most recent 100 entries, sorted descending by timestamp). Supports optional filtering.

**Query Params (all optional):**

| Param | Type | Description |
|---|---|---|
| `action` | str | Filter by action type, e.g. `APPROVE_GOAL`, `UNLOCK_GOAL` |
| `user_id` | str | Filter by the `employee_id` who performed the action |

**Example:**
```
GET /admin/goals/logs?action=UNLOCK_GOAL&user_id=EMP001
```

**Response `200`:** Array of log entry objects
```json
[
  {
    "_id": "664log001...",
    "user_id": "EMP001",
    "action": "UNLOCK_GOAL",
    "details": {
      "goal_id": "664abc123...",
      "previous_status": "LOCKED",
      "new_status": "ADMIN_UNLOCKED"
    },
    "timestamp": "2025-06-01T12:34:56Z"
  }
]
```

---

#### `GET /admin/goals/unlock-requests`

List unlock requests submitted by employees.

**Query Params (optional):**
- `status`: `PENDING` | `APPROVED`

**Response `200`:** Array of unlock request objects

---

#### `PATCH /admin/goals/unlock-requests/{request_id}/approve`

Approve an unlock request and unlock the linked goal.

**Response `200`:**
```json
{ "message": "Unlock request approved and goal unlocked" }
```

---

#### `PATCH /admin/goals/unlock-requests/{request_id}/reject`

Reject an unlock request with an optional reason.

**Request Body:**
```json
{ "reason": "Insufficient justification" }
```

**Response `200`:**
```json
{ "message": "Unlock request rejected" }
```

---

## Business Rules & Validations

### Goal Creation
- Minimum weightage per goal: **10%**
- Maximum weightage per goal: **100%**
- `thrust_area` and `title`: minimum **3 characters**
- `target_value` must be **> 0**
- Employee must not already have **8 or more** active goals

### Goal Submission
- Total weightage across all active goals (`DRAFT` being submitted + `LOCKED`) must equal exactly **100%**
- Combined count of submitted + locked goals must not exceed **8**
- At least **1 goal** must be included in the submission payload
- Each submitted goal must have `weightage >= 10`
- For shared goals: all read-only fields must match the `source_snapshot`

### Goal Editing
- Only goals with status `DRAFT`, `RETURNED`, or `ADMIN_UNLOCKED` can be edited or deleted
- `SUBMITTED` and `LOCKED` goals cannot be edited by the employee
- Shared goal copies: only `weightage` can be changed; all other core fields enforce read-only via `source_snapshot`

### Goal Approval (Manager)
- Only `SUBMITTED` goals can be approved or returned
- Manager can only act on goals where `manager_id` matches their `employee_id`
- On approval, manager may optionally override `target_value` and/or `weightage` (weightage still must be 10–100)
- Approved goals transition to `LOCKED`

### Goal Unlock (Admin)
- Only `LOCKED` goals can be unlocked
- Unlock sets status to `ADMIN_UNLOCKED` (not `RETURNED`)
- Employee can then edit and resubmit as if the goal were `RETURNED`
- All unlock events are audit-logged
- Employees must request unlock via `/employee/goals/{goal_id}/unlock-request`

### Quarterly Check-in
- Only `LOCKED` goals can receive check-in updates
- Employee must be the owner of the goal
- Progress percentage is auto-computed — see formula table below
- For shared goals: only the `primary_owner` triggers achievement sync to linked copies
- One quarter per request, in strict order (Q1 → Q2 → Q3 → Q4); skipping ahead is not allowed
- Previously submitted quarters remain stored and are not overwritten

---

## Goal Lifecycle

```
                       ┌───────────────────────────────────────────┐
                       │                 EMPLOYEE                  │
                       └───────────────────────────────────────────┘
                                           │
                                 create_goal()
                                           │
                                           ▼
                                       [ DRAFT ] ◄──────────────────────────────┐
                                           │                                     │
                                 submit_goals()                                  │
                                           │                                     │
                                           ▼                                     │
                                     [ SUBMITTED ]                               │
                                           │                                     │
                           ┌──────────────┴───────────────┐                     │
                           │           MANAGER             │                     │
                           └──────────────────────────────┘                     │
                                           │                                     │
                           approve_goal()  │  return_goal()                      │
                                           │                                     │
                    ┌──────────────────────┴────────────────────┐               │
                    ▼                                            ▼               │
               [ LOCKED ]                               [ RETURNED ] ────────────┘
                    │                                         ▲
    quarterly_checkin()  [Employee]                          │
    comment_on_goal()    [Manager]                unlock_goal()  [Admin]
                    │                                         │
                    └─────────────────────────────────────────┘
                         (Admin unlocks → ADMIN_UNLOCKED status,
                          treated same as RETURNED for edit/submit)
```

**Status Summary:**

| Status | Who Sets It | What Can Happen Next |
|---|---|---|
| `DRAFT` | Employee (on create) | Edit, Delete, Submit |
| `SUBMITTED` | Employee (on submit) | Manager Approve or Return |
| `RETURNED` | Manager (on return) | Employee can Edit and Resubmit |
| `ADMIN_UNLOCKED` | Admin (on unlock) | Employee can Edit and Resubmit |
| `LOCKED` | Manager (on approval) | Employee Check-in, Manager Comment, Admin Unlock |

---

## Progress Score Computation

Progress percentage is computed automatically during quarterly check-in based on the goal's `uom_type` and `measurement_type`. It is a **tracking metric only** — not used for formal ratings.

| UoM Type | Measurement | Description | Formula |
|---|---|---|---|
| `NUMERIC` / `PERCENTAGE` | `MIN` | Higher is better (e.g. Sales Revenue) | `(achievement / target) × 100` |
| `NUMERIC` / `PERCENTAGE` | `MAX` | Lower is better (e.g. TAT, Cost) | `(target / achievement) × 100` |
| `NUMERIC` / `PERCENTAGE` | `MAX` | Achievement is zero (perfect outcome) | `100%` |
| `ZERO_BASED` | — | Zero = Success (e.g. Safety incidents) | `achievement == 0 → 100%, else 0%` |
| `TIMELINE` | — | Date-based completion | On/before deadline → `100%`; late → `max(0, 100 - (days_late / total_days) × 100)` |

**TIMELINE detail:** `total_days` is computed as `(deadline_date - goal.created_at.date())`. If `total_days <= 0`, it defaults to 1. Completion before or on the deadline always yields 100%. Late completion degrades proportionally.

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

Every significant action is recorded in the `logs` collection via the centralized `log_action()` function in `app/audit/logs.py`. Logs are append-only and visible to Admins via `GET /admin/goals/logs`.

| Action | Triggered By | Key Details Logged |
|---|---|---|
| `CREATE_GOAL` | Employee creates a goal | `goal_id`, `title`, `thrust_area`, `weightage` |
| `UPDATE_GOAL` | Employee updates a goal | `goal_id`, `updated_fields` |
| `DELETE_GOAL` | Employee deletes a draft | `goal_id` |
| `SUBMIT_GOALS` | Employee submits goals | `goal_ids`, `number_of_goals_submitted` |
| `APPROVE_GOAL` | Manager approves | `goal_id`, `employee_id`, `employee_name` |
| `RETURN_GOAL` | Manager returns | `goal_id`, `employee_id`, `manager_note` |
| `COMMENT_ON_GOAL` | Manager comments | `goal_id`, `quarter`, `comment` |
| `UNLOCK_GOAL` | Admin unlocks | `goal_id`, `previous_status`, `new_status` |
| `PUSH_SHARED_GOAL` | Admin/Manager pushes | `source_goal_id`, `title`, `recipients`, `count` |
| `UPDATE_SHARED_GOAL_WEIGHTAGE` | Employee adjusts | `goal_id`, `new_weightage` |
| `QUARTERLY_CHECKIN` | Employee logs achievement | `goal_id`, `quarters_updated` |
| `SYNC_SHARED_ACHIEVEMENT` | System (after primary owner check-in) | `source_goal_id`, `synced_copies`, `quarters_updated` |
| `REQUEST_UNLOCK_GOAL` | Employee requests unlock | `request_id`, `goal_id`, `reason` |
| `APPROVE_UNLOCK_REQUEST` | Admin approves unlock request | `request_id`, `goal_id`, `requester_id` |
| `REJECT_UNLOCK_REQUEST` | Admin rejects unlock request | `request_id`, `goal_id`, `requester_id`, `reason` |

---

## Shared Goals

The Shared Goal feature allows an Admin or Manager to broadcast a departmental KPI to multiple employees simultaneously.

**How it works:**

1. Pusher calls `POST /shared-goals/push` with a list of `recipient_employee_ids`
2. A single `source_goal_id` (ObjectId) is generated — this is the logical parent shared across all copies
3. Each recipient gets their own independent goal document with `is_shared: true`, `source_goal_id` set, and a `source_snapshot` capturing the immutable fields at creation time
4. Recipients can only adjust `weightage` via `PATCH /employee/goals/{goal_id}/weightage`; all other fields (`title`, `target_value`, `uom_type`, `thrust_area`, `description`, `measurement_type`, `target_date`) are enforced read-only — both at update time and at submission time via snapshot comparison
5. When the **primary owner** (the pusher) logs a quarterly check-in, `sync_shared_achievement()` propagates `achievement_value`, `progress_percentage`, and the full `quarter` dict to all other `LOCKED` copies sharing the same `source_goal_id`
6. Non-primary-owner recipients see the synced achievement data but cannot log their own check-ins (they can only submit and have their goals approved)

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
- Redis running locally or via a managed service

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

The health check endpoint returns:
```json
{ "message": "NorthStar API Gateway is live" }
```

---

## User Role Quick Reference

| Capability | Employee | Manager | Admin |
|---|---|---|---|
| Register / Login | ✅ | ✅ | ✅ |
| Create / Edit / Delete goals | ✅ | — | — |
| Submit goals for approval | ✅ | — | — |
| Log quarterly check-in | ✅ | — | — |
| View own personal goals | ✅ | — | — |
| View own shared goal copies | ✅ | — | — |
| Adjust shared goal weightage | ✅ | — | — |
| Review submitted goals | — | ✅ | — |
| Approve / Return goals | — | ✅ | — |
| Inline edit on approval | — | ✅ | — |
| Add check-in comments | — | ✅ | — |
| View team's locked goals | — | ✅ | — |
| Push shared goals | — | ✅ | ✅ |
| View pushed shared goals | — | ✅ (own) | ✅ (all) |
| Unlock locked goals | — | — | ✅ |
| View audit logs | — | — | ✅ |
| View org hierarchy | ✅ | ✅ | ✅ |

---

*NorthStar — Built for AtomQuest Hackathon 1.0*