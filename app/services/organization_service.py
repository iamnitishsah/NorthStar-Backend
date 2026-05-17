from app.db.database import db
from app.schemas.organization_schema import HierarchyNode

users = db.users


async def get_organization_hierarchy() -> list[HierarchyNode]:
    employees = await users.find(
        {"is_active": True},
        {
            "_id": 0,
            "employee_id": 1,
            "name": 1,
            "designation": 1,
            "department": 1,
            "role": 1,
            "manager_id": 1
        }
    ).to_list(length=None)

    employee_map = {}

    for employee in employees:
        employee_map[employee["employee_id"]] = {
            "employee_id": employee["employee_id"],
            "name": employee["name"],
            "designation": employee.get("designation"),
            "department": employee.get("department"),
            "role": employee.get("role"),
            "manager_id": employee.get("manager_id"),
            "children": []
        }

    roots = []

    for employee in employee_map.values():
        manager_id = employee.get("manager_id")

        if not manager_id:
            roots.append(employee)
            continue

        if manager_id == employee["employee_id"]:
            roots.append(employee)
            continue

        manager = employee_map.get(manager_id)

        if manager:
            manager["children"].append(employee)

        else:
            roots.append(employee)


    def clean_node(node: dict) -> dict:

        return {
            "employee_id": node["employee_id"],
            "name": node["name"],
            "designation": node["designation"],
            "department": node["department"],
            "role": node["role"],
            "children": [
                clean_node(child)
                for child in node["children"]
            ]
        }

    cleaned_roots = [
        clean_node(root)
        for root in roots
    ]


    return True, [HierarchyNode(**root) for root in cleaned_roots]