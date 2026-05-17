from collections import defaultdict
from app.constants.enums import GoalStatus
from app.db.database import db

goals = db.goals
users = db.users


def _enum_value(value):
    if hasattr(value, "value"):
        return value.value
    return value


def _empty_quarter_totals():
    return {
        str(quarter): {
            "progress_total": 0,
            "completed_goals": 0,
        }
        for quarter in range(1, 5)
    }


def _quarter_summary(totals: dict) -> dict:
    summary = {}
    previous_average = None

    for quarter in range(1, 5):
        key = str(quarter)
        completed_goals = totals[key]["completed_goals"]
        average_progress = None
        qoq_delta = None

        if completed_goals:
            average_progress = round(
                totals[key]["progress_total"] / completed_goals,
                2
            )
            if previous_average is not None:
                qoq_delta = round(average_progress - previous_average, 2)
            previous_average = average_progress

        summary[f"q{quarter}"] = {
            "average_progress_percentage": average_progress,
            "completed_goals": completed_goals,
            "qoq_delta": qoq_delta,
        }

    return summary


async def qoq_analytics() -> dict:
    employee_totals = {}
    team_totals = {}

    user_map = {}
    users_cursor = users.find(
        {},
        {"_id": 0, "employee_id": 1, "name": 1, "manager_id": 1}
    )
    async for user in users_cursor:
        user_map[user["employee_id"]] = user

    goals_cursor = goals.find({"status": GoalStatus.LOCKED})
    async for goal in goals_cursor:
        employee_id = goal.get("employee_id")
        employee_name = goal.get("employee_name")
        manager_id = goal.get("manager_id")

        if employee_id not in employee_totals:
            employee_totals[employee_id] = {
                "employee_id": employee_id,
                "employee_name": employee_name,
                "manager_id": manager_id,
                "manager_name": user_map.get(manager_id, {}).get("name"),
                "goal_count": 0,
                "quarters": _empty_quarter_totals(),
            }

        if manager_id not in team_totals:
            team_totals[manager_id] = {
                "manager_id": manager_id,
                "manager_name": user_map.get(manager_id, {}).get("name"),
                "employee_ids": set(),
                "goal_count": 0,
                "quarters": _empty_quarter_totals(),
            }

        employee_totals[employee_id]["goal_count"] += 1
        team_totals[manager_id]["goal_count"] += 1
        team_totals[manager_id]["employee_ids"].add(employee_id)

        quarter_data = goal.get("quarter") or {}
        for quarter in range(1, 5):
            key = str(quarter)
            progress = (quarter_data.get(key) or {}).get("progress_percentage")
            if progress is None:
                continue

            employee_totals[employee_id]["quarters"][key]["progress_total"] += progress
            employee_totals[employee_id]["quarters"][key]["completed_goals"] += 1
            team_totals[manager_id]["quarters"][key]["progress_total"] += progress
            team_totals[manager_id]["quarters"][key]["completed_goals"] += 1

    employees = []
    for employee in employee_totals.values():
        employees.append(
            {
                "employee_id": employee["employee_id"],
                "employee_name": employee["employee_name"],
                "manager_id": employee["manager_id"],
                "manager_name": employee["manager_name"],
                "goal_count": employee["goal_count"],
                "quarters": _quarter_summary(employee["quarters"]),
            }
        )

    teams = []
    for team in team_totals.values():
        teams.append(
            {
                "manager_id": team["manager_id"],
                "manager_name": team["manager_name"],
                "employee_count": len(team["employee_ids"]),
                "goal_count": team["goal_count"],
                "quarters": _quarter_summary(team["quarters"]),
            }
        )

    return {
        "employees": sorted(employees, key=lambda item: item["employee_name"] or ""),
        "teams": sorted(teams, key=lambda item: item["manager_name"] or ""),
    }


def _new_distribution_bucket(label: str) -> dict:
    return {
        "label": label,
        "goal_count": 0,
        "total_weightage": 0,
        "progress_total": 0,
        "progress_count": 0,
        "status_breakdown": defaultdict(int),
    }


def _add_goal_to_bucket(bucket: dict, goal: dict) -> None:
    bucket["goal_count"] += 1
    bucket["total_weightage"] += goal.get("weightage") or 0
    bucket["status_breakdown"][_enum_value(goal.get("status"))] += 1

    progress = goal.get("progress_percentage")
    if progress is not None:
        bucket["progress_total"] += progress
        bucket["progress_count"] += 1


def _finalize_distribution_bucket(bucket: dict) -> dict:
    average_progress = None
    if bucket["progress_count"]:
        average_progress = round(
            bucket["progress_total"] / bucket["progress_count"],
            2
        )

    return {
        "label": bucket["label"],
        "goal_count": bucket["goal_count"],
        "total_weightage": bucket["total_weightage"],
        "average_progress_percentage": average_progress,
        "status_breakdown": dict(bucket["status_breakdown"]),
    }


async def distribution_analytics() -> dict:
    by_thrust_area = {}
    by_uom_type = {}
    matrix = {}
    total_goals = 0

    goals_cursor = goals.find({})
    async for goal in goals_cursor:
        total_goals += 1
        thrust_area = goal.get("thrust_area") or "Unspecified"
        uom_type = _enum_value(goal.get("uom_type")) or "Unspecified"
        matrix_key = f"{thrust_area}::{uom_type}"

        if thrust_area not in by_thrust_area:
            by_thrust_area[thrust_area] = _new_distribution_bucket(thrust_area)
        if uom_type not in by_uom_type:
            by_uom_type[uom_type] = _new_distribution_bucket(uom_type)
        if matrix_key not in matrix:
            matrix[matrix_key] = _new_distribution_bucket(matrix_key)
            matrix[matrix_key]["thrust_area"] = thrust_area
            matrix[matrix_key]["uom_type"] = uom_type

        _add_goal_to_bucket(by_thrust_area[thrust_area], goal)
        _add_goal_to_bucket(by_uom_type[uom_type], goal)
        _add_goal_to_bucket(matrix[matrix_key], goal)

    matrix_rows = []
    for bucket in matrix.values():
        row = _finalize_distribution_bucket(bucket)
        row["thrust_area"] = bucket["thrust_area"]
        row["uom_type"] = bucket["uom_type"]
        row.pop("label", None)
        matrix_rows.append(row)

    return {
        "total_goals": total_goals,
        "by_thrust_area": sorted(
            [_finalize_distribution_bucket(bucket) for bucket in by_thrust_area.values()],
            key=lambda item: item["label"],
        ),
        "by_uom_type": sorted(
            [_finalize_distribution_bucket(bucket) for bucket in by_uom_type.values()],
            key=lambda item: item["label"],
        ),
        "by_thrust_area_and_uom_type": sorted(
            matrix_rows,
            key=lambda item: (item["thrust_area"], item["uom_type"]),
        ),
    }
