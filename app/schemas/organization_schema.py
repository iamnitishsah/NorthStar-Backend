from typing import List
from pydantic import BaseModel


class HierarchyNode(BaseModel):
    employee_id: str
    name: str
    designation: str
    department: str
    role: str
    children: List["HierarchyNode"] = []