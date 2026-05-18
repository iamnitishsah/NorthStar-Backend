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

<p align="center">
  <img src="./Architecture%20Diagram.png" alt="NorthStar Architecture Diagram" width="100%">
</p>

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
- `manager_id`: optional; when provided, must match an existing user whose role is `MANAGER`

**Response `200`:**
```json
{
  "message": "User Registered Successfully",
  "user_id": "<mongo_object_id>"
}
```

**Response `400`:**
```json
{ "detail": "manager_id does not match an existing employee" }
{ "detail": "manager_id must belong to a MANAGER user" }
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

**Query Params (optional):**

| Param | Type | Description |
|---|---|---|
| `status` | GoalStatus | Filter by `DRAFT`, `SUBMITTED`, `RETURNED`, `ADMIN_UNLOCKED`, or `LOCKED` |

**Example:**
```
GET /employee/goals/my?status=DRAFT
```

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

Adjust the weightage of a shared goal copy. Only allowed when status is `DRAFT`, `RETURNED`, or `ADMIN_UNLOCKED`. Title, target, UoM, and all other fields remain read-only.

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
{ "detail": "Weightage can only be changed while the goal is DRAFT, RETURNED, or ADMIN_UNLOCKED" }
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

#### `GET /manager/goals/checkin-review`

View Planned vs Achievement check-in progress for each team member. Returns all `LOCKED` goals assigned to the authenticated manager, grouped by employee name, with latest achievement and Q1-Q4 check-in status.

**Response `200`:**
```json
{
  "Alice Johnson": [
    {
      "goal_id": "664abc123...",
      "employee_id": "EMP001",
      "employee_name": "Alice Johnson",
      "title": "Increase Q3 Sales",
      "thrust_area": "Revenue Growth",
      "planned_target_value": 550000,
      "latest_achievement_value": 420000,
      "latest_progress_percentage": 76.36,
      "latest_progress_status": "ON_TRACK",
      "weightage": 35,
      "target_date": "2025-12-31T00:00:00Z",
      "quarters": {
        "q1": {
          "achievement_value": 350000,
          "progress_percentage": 63.64,
          "progress_status": "ON_TRACK",
          "manager_note": "Good progress so far.",
          "completed": true
        },
        "q2": {
          "achievement_value": 420000,
          "progress_percentage": 76.36,
          "progress_status": "ON_TRACK",
          "manager_note": null,
          "completed": true
        }
      }
    }
  ]
}
```

**Response `404`:**
```json
{ "detail": "No check-in data found for this manager" }
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

#### `GET /admin/goals/export`

Export the Achievement Report as CSV for all employee goals. The report includes planned target values, actual achievement values, current progress, and Q1-Q4 check-in actuals.

**Response `200`:** `text/csv`

**Download filename:** `achievement_report.csv`

**CSV columns include:**
`employee_id`, `employee_name`, `title`, `planned_target_value`, `actual_achievement_value`, `progress_percentage`, `progress_status`, `q1_actual`, `q2_actual`, `q3_actual`, `q4_actual`

---

#### `GET /admin/goals/completion-dashboard`

Show quarterly check-in completion status per employee. The dashboard includes all active employees and computes completion against each employee's `LOCKED` goals, since only locked goals are eligible for quarterly check-ins.

**Response `200`:**
```json
[
  {
    "employee_id": "EMP001",
    "employee_name": "Alice Johnson",
    "manager_id": "MGR001",
    "manager_name": "Priya Sharma",
    "total_goals": 5,
    "checkin_required_goals": 5,
    "latest_completed_quarter": 2,
    "quarters": {
      "q1": {
        "employee_completed": true,
        "employee_completed_goals": 5,
        "manager_completed": true,
        "manager_completed_goals": 5,
        "required_goals": 5
      },
      "q2": {
        "employee_completed": true,
        "employee_completed_goals": 5,
        "manager_completed": false,
        "manager_completed_goals": 3,
        "required_goals": 5
      }
    }
  }
]
```

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

Retrieve the audit log, sorted descending by timestamp. Supports optional filtering and pagination.

**Query Params (all optional):**

| Param | Type | Description |
|---|---|---|
| `action` | str | Filter by action type, e.g. `APPROVE_GOAL`, `UNLOCK_GOAL` |
| `user_id` | str | Filter by the `employee_id` who performed the action |
| `skip` | int | Number of matching logs to skip; defaults to `0` |
| `limit` | int | Number of logs to return; defaults to `100`, max `500` |

**Example:**
```
GET /admin/goals/logs?action=UNLOCK_GOAL&user_id=EMP001&skip=0&limit=100
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

List all unlock requests submitted by employees, with optional status filtering.

**Query Params (optional):**
- `status`: `PENDING` | `APPROVED` | `REJECTED`

**Response `200`:** Array of unlock request objects
```json
[
  {
    "request_id": "664req001...",
    "goal_id": "664abc123...",
    "goal_title": "Increase Q3 Sales",
    "requester_id": "EMP001",
    "requester_name": "Alice Johnson",
    "manager_id": "EMP010",
    "manager_name": "Priya Sharma",
    "reason": "Target market conditions have changed; need to adjust target value",
    "status": "PENDING",
    "resolved_by": null,
    "resolved_at": null,
    "rejection_reason": null,
    "created_at": "2025-06-10T14:30:00Z",
    "updated_at": "2025-06-10T14:30:00Z"
  }
]
```

---

#### `POST /employee/goals/{goal_id}/unlock-request`

Employee endpoint to request unlock of a `LOCKED` goal. Requires a reason (5–500 characters).

**Auth:** Bearer token + Employee role

**Path Param:** `goal_id`

**Request Body:**
```json
{
  "reason": "Target market conditions have changed; need to adjust target value and weightage"
}
```

**Validation:**
- Goal must exist and belong to the authenticated employee
- Goal status must be `LOCKED`
- No pending unlock request for this goal can already exist

**Response `200`:**
```json
{ "message": "Unlock request submitted with ID: 664req001..." }
```

**Response `400` / `403` / `404`:**
```json
{ "detail": "Only LOCKED goals can be requested for unlock" }
{ "detail": "An unlock request for this goal is already pending" }
{ "detail": "Unauthorized to request unlock for this goal" }
{ "detail": "Goal not found" }
```

**Audit Trail:** `REQUEST_UNLOCK_GOAL` log entry created with request_id, goal_id, and reason.

---

#### `PATCH /admin/goals/unlock-requests/{request_id}/approve`

Admin endpoint to approve an unlock request. This unlocks the linked goal (sets status to `ADMIN_UNLOCKED`), allowing the employee to edit and resubmit.

**Auth:** Bearer token + Admin role

**Path Param:** `request_id`

**Response `200`:**
```json
{ "message": "Unlock request approved and goal unlocked" }
```

**Response `400` / `404`:**
```json
{ "detail": "Unlock request is not pending" }
{ "detail": "Only LOCKED goals can be unlocked" }
{ "detail": "Unlock request not found" }
{ "detail": "Goal not found" }
```

**Audit Trail:** 
- `APPROVE_UNLOCK_REQUEST` — admin approval action
- Goal status changed from `LOCKED` to `ADMIN_UNLOCKED`

---

#### `PATCH /admin/goals/unlock-requests/{request_id}/reject`

Admin endpoint to reject an unlock request with an optional reason.

**Auth:** Bearer token + Admin role

**Path Param:** `request_id`

**Request Body:**
```json
{
  "reason": "Current target is achievable; insufficient justification for unlock"
}
```

**Validation:**
- Request must have status `PENDING`

**Response `200`:**
```json
{ "message": "Unlock request rejected" }
```

**Response `400` / `404`:**
```json
{ "detail": "Unlock request is not pending" }
{ "detail": "Unlock request not found" }
```

**Audit Trail:** `REJECT_UNLOCK_REQUEST` log entry created with request_id, goal_id, requester_id, and rejection reason.

---

### Admin Analytics APIs

**Tag:** `Admin Analytics APIs` · **Prefix:** `/admin/analytics`
**Auth:** Bearer token required · **Role:** `ADMIN` enforced on all routes.

---

#### `GET /admin/analytics/qoq`

Quarter-on-quarter progress analytics for employees and manager teams. Uses `LOCKED` goals and averages submitted quarterly `progress_percentage` values.

**Response `200`:**
```json
{
  "employees": [
    {
      "employee_id": "EMP001",
      "employee_name": "Alice Johnson",
      "manager_id": "MGR001",
      "manager_name": "Priya Sharma",
      "goal_count": 5,
      "quarters": {
        "q1": {
          "average_progress_percentage": 63.64,
          "completed_goals": 5,
          "qoq_delta": null
        },
        "q2": {
          "average_progress_percentage": 76.36,
          "completed_goals": 5,
          "qoq_delta": 12.72
        }
      }
    }
  ],
  "teams": [
    {
      "manager_id": "MGR001",
      "manager_name": "Priya Sharma",
      "employee_count": 8,
      "goal_count": 35,
      "quarters": {
        "q1": {
          "average_progress_percentage": 61.4,
          "completed_goals": 32,
          "qoq_delta": null
        }
      }
    }
  ]
}
```

---

#### `GET /admin/analytics/distribution`

Goal distribution analytics by thrust area, UoM type, and thrust-area/UoM combination. Includes goal counts, total weightage, average latest progress, and status breakdown.

**Response `200`:**
```json
{
  "total_goals": 120,
  "by_thrust_area": [
    {
      "label": "Revenue Growth",
      "goal_count": 40,
      "total_weightage": 1200,
      "average_progress_percentage": 72.5,
      "status_breakdown": {
        "LOCKED": 35,
        "DRAFT": 5
      }
    }
  ],
  "by_uom_type": [
    {
      "label": "NUMERIC",
      "goal_count": 75,
      "total_weightage": 2200,
      "average_progress_percentage": 68.1,
      "status_breakdown": {
        "LOCKED": 60,
        "SUBMITTED": 15
      }
    }
  ],
  "by_thrust_area_and_uom_type": [
    {
      "thrust_area": "Revenue Growth",
      "uom_type": "NUMERIC",
      "goal_count": 28,
      "total_weightage": 840,
      "average_progress_percentage": 74.2,
      "status_breakdown": {
        "LOCKED": 25,
        "DRAFT": 3
      }
    }
  ]
}
```

---

### Shared Goal APIs

**Tag:** `Shared Goal APIs` · **Prefix:** `/shared-goals`
**Auth:** Bearer token required

The Shared Goal APIs allow Managers and Admins to broadcast departmental KPIs to multiple employees. Recipients can adjust weightage but core goal fields are immutable. Primary owner achievement updates sync automatically across all linked copies.

---

#### `POST /shared-goals/push`

Push a shared goal (KPI) to multiple employees. Only Managers and Admins can push shared goals.

**Auth:** Bearer token + (Manager or Admin role)

**Request Body:**
```json
{
  "recipient_employee_ids": ["EMP001", "EMP002", "EMP003"],
  "thrust_area": "Safety",
  "title": "Zero Incidents FY25",
  "description": "Maintain zero safety incidents throughout the fiscal year",
  "uom_type": "ZERO_BASED",
  "measurement_type": "MIN",
  "target_value": 1.0,
  "default_weightage": 15,
  "target_date": "2026-03-31T00:00:00Z"
}
```

**Field Rules:**
- `recipient_employee_ids`: non-empty array of valid active employee IDs
- `thrust_area`, `title`: 3–100 characters
- `description`: optional, max 500 characters
- `uom_type`: `NUMERIC | PERCENTAGE | TIMELINE | ZERO_BASED`
- `measurement_type`: `MIN | MAX`
- `target_value`: must be > 0
- `default_weightage`: 10–100 (assigned to all recipients initially)

**Validation:**
- All recipient IDs must exist and be active EMPLOYEE role users
- Each recipient must have < 8 active goals (after insertion would not exceed 8)

**Response `200`:**
```json
{
  "message": "Shared goal pushed to 3 employee(s)",
  "source_goal_id": "664abc000...",
  "recipient_count": 3,
  "recipients": ["EMP001", "EMP002", "EMP003"]
}
```

**Response `400`:**
```json
{ "detail": "These employee IDs were not found or are not active employees: [\"EMP999\"]" }
{ "detail": { "message": "Maximum 8 goals allowed per employee", "over_limit_recipients": [...] } }
```

**Effect:**
- Single `source_goal_id` (ObjectId) created as logical parent
- Each recipient gets independent goal document with:
  - `is_shared: true`
  - `source_goal_id` referencing the parent
  - `source_snapshot` capturing immutable fields (title, uom_type, measurement_type, target_value, thrust_area, description, target_date, target_date)
  - `primary_owner_id` set to the pusher's employee_id
  - Initial status: `DRAFT`
- All goals start with the same `default_weightage`

**Audit Trail:** `PUSH_SHARED_GOAL` log entry with source_goal_id, title, recipients list, and count.

---

#### `GET /shared-goals/pushed`

View all shared goals that the current user has pushed. Only Managers (for goals they pushed) and Admins (for all pushed goals) can access this.

**Auth:** Bearer token + (Manager or Admin role)

**Response `200`:** Array of `SharedGoalResponse` objects (see `GET /employee/goals/my-shared-goals` for response structure)

**Role Rules:**
- **Manager**: Returns only shared goals where `primary_owner_id == current_user.employee_id`
- **Admin**: Returns all shared goals in the system

---

#### `PATCH /employee/goals/{goal_id}/weightage`

Employee endpoint to adjust weightage of a shared goal copy only. All other fields are read-only for shared goals.

**Auth:** Bearer token + Employee role

**Path Param:** `goal_id` (must be a shared goal copy)

**Request Body:**
```json
{ "weightage": 20 }
```

**Field Rules:**
- `weightage`: 10–100

**Validation:**
- Goal must exist and belong to the authenticated employee
- Goal must be a shared goal (`is_shared: true`)
- Goal status must be `DRAFT`, `RETURNED`, or `ADMIN_UNLOCKED`

**Response `200`:**
```json
{ "message": "Weightage updated successfully" }
```

**Response `400` / `403`:**
```json
{ "detail": "This endpoint is only for shared goals" }
{ "detail": "Weightage can only be changed while the goal is DRAFT, RETURNED, or ADMIN_UNLOCKED" }
{ "detail": "Unauthorized" }
```

**Audit Trail:** `UPDATE_SHARED_GOAL_WEIGHTAGE` log entry with goal_id and new_weightage.

---

#### `GET /employee/goals/my-shared-goals`

Employee endpoint to view all shared goal copies assigned to them (all statuses).

**Auth:** Bearer token + Employee role

**Response `200`:** Array of `SharedGoalResponse` objects
```json
[
  {
    "goal_id": "664abc999...",
    "source_goal_id": "664abc000...",
    "thrust_area": "Safety",
    "title": "Zero Incidents FY25",
    "description": "Maintain zero safety incidents...",
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

### Shared Goal Mechanics

**Immutable Fields (read-only for recipients):**
- `title`
- `thrust_area`
- `uom_type`
- `measurement_type`
- `target_value`
- `description`
- `target_date`

**Mutable Fields (only on shared goal copies):**
- `weightage` (via dedicated `/weightage` endpoint)

**Read-only Enforcement:**
1. **At Update Time**: `PATCH /employee/goals/{goal_id}` rejects any update to immutable fields with a 403 error
2. **At Submission**: `POST /employee/goals/submit` validates that shared goal mutable fields match `source_snapshot`; if not, returns 400 with list of invalid goal_ids

**Achievement Sync (Primary Owner Only):**
When the primary owner (pusher) logs a quarterly check-in for a shared goal:
1. System calls `sync_shared_achievement()` internally
2. Latest `achievement_value` and `progress_percentage` propagate to all other `LOCKED` copies of the same source goal
3. Only newly submitted quarter data is synced; previous quarters remain unchanged
4. Non-primary-owner recipients cannot log their own check-ins—they only see synced data

**Status Flow for Shared Goals:**
- Created in `DRAFT` by pusher
- Recipients can edit (adjust weightage) and submit
- Manager approves → `LOCKED`
- Only primary owner can log check-in and trigger sync
- Recipients can request unlock if needed

---

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
<p align="center">
  <img src="./Goal%20Life%20Cycle.png" alt="NorthStar Architecture Diagram" width="100%">
</p>

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
| `EMAIL_NOTIFICATION_QUEUED` | API process queues email | `event_type`, `to_email`, `subject`, `task_id`, event metadata |
| `EMAIL_NOTIFICATION_SKIPPED` | API process skips email enqueue | `event_type`, `reason`, event metadata |
| `EMAIL_NOTIFICATION_QUEUE_FAILED` | API process fails to enqueue email | `event_type`, `error`, event metadata |
| `EMAIL_SEND_STARTED` | Celery worker starts SMTP send | `task_id`, `event_type`, `to_email`, `subject`, SMTP host/port |
| `EMAIL_SEND_SUCCEEDED` | Celery worker sends email | `task_id`, `event_type`, `to_email`, `subject`, SMTP host/port |
| `EMAIL_SEND_FAILED` | Celery worker fails SMTP send | `task_id`, `event_type`, `to_email`, `subject`, `error` |
| `EMAIL_SEND_SKIPPED` | Celery worker skips send | `task_id`, `event_type`, `reason` |

---

## Email Notifications

NorthStar sends background email notifications for the goal review workflow using Redis, Celery, and SMTP. The notification system is non-blocking — if email enqueue fails, the main business logic continues.

### Events & Recipients

| Event | Trigger | Recipient | Notification Type |
|---|---|---|---|
| Goal submission | Employee submits goals for review | Assigned manager | `GOALS_SUBMITTED` |
| Goal approval | Manager approves a submitted goal | Employee goal owner | `GOAL_APPROVED` |
| Goal return | Manager returns a submitted goal | Employee goal owner | `GOAL_RETURNED` |

### Implementation Flow

1. **Business Action**: API updates MongoDB and writes the primary audit log (`SUBMIT_GOALS`, `APPROVE_GOAL`, or `RETURN_GOAL`)
2. **Notification Enqueue**: API calls `notification_service._enqueue_email()` with recipient email, subject, and body
3. **Email Dispatch**: Service queues Celery task `send_email.delay()` via Redis broker
4. **Audit Logging**: API writes enqueue result audit logs:
   - `EMAIL_NOTIFICATION_QUEUED` — task successfully queued with task ID
   - `EMAIL_NOTIFICATION_SKIPPED` — recipient email missing
   - `EMAIL_NOTIFICATION_QUEUE_FAILED` — exception during enqueue (non-blocking)
5. **Worker Processing**: Celery worker picks up task and attempts SMTP send
6. **Send Logging**: Worker writes execution audit logs:
   - `EMAIL_SEND_STARTED` — connection and auth initiated
   - `EMAIL_SEND_SUCCEEDED` — SMTP send complete
   - `EMAIL_SEND_FAILED` — SMTP error (with retry policy: 3 retries at 60s intervals)
   - `EMAIL_SEND_SKIPPED` — recipient validation failed

### Celery Configuration

- **Task Definition**: `send_email` in `app/tasks/email_tasks.py`
- **Broker**: Redis (configurable via `REDIS_URL`)
- **Result Backend**: Redis (configurable via `REDIS_URL`)
- **Retry Policy**: `autoretry_for=(smtplib.SMTPException, OSError)` with `max_retries=3` and `countdown=60s`
- **Serialization**: JSON (configured in `celery_app.py`)

### Notification Service (app/services/notification_service.py)

Three async functions handle notifications:
- `notify_goals_submitted()` — sends to manager when employee submits goals
- `notify_goal_approved()` — sends to employee when manager approves
- `notify_goal_returned()` — sends to employee when manager returns (includes manager note)

All functions are non-blocking; enqueue exceptions are caught and logged without disrupting the business transaction.

### SMTP Configuration & Providers

The system uses configurable SMTP settings via environment variables. Default configuration uses Gmail-style app password.

**Default (Gmail with app password):**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=northstar@example.com
SMTP_PASSWORD=<gmail-app-password>
SMTP_USE_TLS=true
EMAIL_FROM=northstar@example.com
```

**SendGrid SMTP:**
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_USE_TLS=true
EMAIL_FROM=northstar@example.com
```

**Development (without auth):**
```env
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=false
EMAIL_FROM=northstar@localhost
```

The email worker respects all SMTP settings and logs connection details in audit logs. Connection failures automatically trigger retry logic (up to 3 retries with 60-second intervals).

---

## Shared Goals

The Shared Goal feature allows an Admin or Manager to broadcast a departmental KPI to multiple employees simultaneously.

**How it works:**

1. Pusher calls `POST /shared-goals/push` with a list of `recipient_employee_ids`
2. A single `source_goal_id` (ObjectId) is generated — this is the logical parent shared across all copies
3. Each recipient gets their own independent goal document with `is_shared: true`, `source_goal_id` set, and a `source_snapshot` capturing the immutable fields at creation time
4. Recipients can only adjust `weightage` via `PATCH /employee/goals/{goal_id}/weightage`; all other fields (`title`, `target_value`, `uom_type`, `thrust_area`, `description`, `measurement_type`, `target_date`) are enforced read-only — both at update time and at submission time via snapshot comparison
5. When the **primary owner** (the pusher) logs a quarterly check-in, `sync_shared_achievement()` propagates `achievement_value`, `progress_percentage`, and only the newly submitted quarter entries to all other `LOCKED` copies sharing the same `source_goal_id`
6. Non-primary-owner recipients see the synced achievement data but cannot log their own check-ins (they can only submit and have their goals approved)

---

## Organization Hierarchy & Structure

### GET /organization/hierarchy

Retrieve the complete organizational hierarchy as a recursive tree structure. This endpoint is accessible to all authenticated users (Employee, Manager, Admin, HR) and displays the org structure built from `manager_id` relationships.

**Auth:** Bearer token required (any authenticated user)

**Response `200`:** Recursive array of `HierarchyNode` objects

```json
[
  {
    "employee_id": "EMP010",
    "name": "Priya Sharma",
    "designation": "VP Engineering",
    "department": "Engineering",
    "role": "MANAGER",
    "manager_id": null,
    "children": [
      {
        "employee_id": "EMP001",
        "name": "Alice Johnson",
        "designation": "Software Engineer",
        "department": "Engineering",
        "role": "EMPLOYEE",
        "manager_id": "EMP010",
        "children": []
      },
      {
        "employee_id": "EMP002",
        "name": "Bob Smith",
        "designation": "Senior Engineer",
        "department": "Engineering",
        "role": "EMPLOYEE",
        "manager_id": "EMP010",
        "children": []
      }
    ]
  },
  {
    "employee_id": "EMP020",
    "name": "Rajesh Kumar",
    "designation": "VP Sales",
    "department": "Sales",
    "role": "MANAGER",
    "manager_id": null,
    "children": [ ... ]
  }
]
```

**How it works:**
1. Queries all active users from MongoDB
2. Builds a node map for all employees
3. Identifies root users (those with `manager_id == null` or self-referencing)
4. Recursively constructs children arrays by matching `manager_id` relationships
5. Returns clean hierarchy without passwords or internal fields

**Use Cases:**
- Managers view their team structure
- Employees view reporting lines
- Admins audit org hierarchy
- Frontend org chart rendering

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
REDIS_URL=redis://localhost:6379/0
EMAIL_FROM=northstar@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=northstar@example.com
SMTP_PASSWORD=dummy-app-password
SMTP_USE_TLS=true
```

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_PORT` | `8000` | Port for the FastAPI server |
| `JWT_SECRET` | `NorthStarSecretKey` | Secret for signing access tokens |
| `JWT_REFRESH_SECRET` | `NorthStarRefreshSecretKey` | Secret for signing refresh tokens |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `REDIS_HOST` | `localhost` | Redis server host |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `EMAIL_FROM` | `northstar@example.com` | Sender email address |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP host; for SendGrid use `smtp.sendgrid.net` |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | `northstar@example.com` | SMTP username; for SendGrid use `apikey` |
| `SMTP_PASSWORD` | `dummy-app-password` | SMTP app password or SendGrid API key |
| `SMTP_USE_TLS` | `true` | Whether to use STARTTLS |

---

## Running the Project

### Prerequisites

- Python 3.10+
- MongoDB 4.4+ (local or Atlas)
- Redis 6.0+ (local or managed service)
- SMTP server access (Gmail, SendGrid, or local Mailhog for dev)

### Installation

```bash
pip install -r requirements.txt
```

### Start the API Server

The FastAPI gateway auto-creates MongoDB indexes on startup.

```bash
python -m app.main
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server runs on the configured `GATEWAY_PORT` (default: `8000`). Startup creates all required MongoDB indexes automatically via the `startup` event handler.

### Start the Celery Email Worker

Background email notifications are processed by a dedicated Celery worker connected to Redis.

```bash
celery -A app.core.celery_app:celery_app worker --loglevel=info
```

If `celery` is not on `PATH`, use Python module execution:

```bash
python -m celery -A app.core.celery_app:celery_app worker --loglevel=info
```

The worker:
- Polls Redis for email tasks queued by the API
- Connects to SMTP server using configured credentials
- Logs all send attempts, successes, and failures to MongoDB audit log
- Retries failed sends up to 3 times with 60-second intervals

### Health Check & Documentation

Once running, verify the server is live:

```bash
curl http://localhost:8000/
# { "message": "NorthStar API Gateway is live" }
```

Interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

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