from typing import List, Optional
from pydantic import BaseModel


class HierarchyNode(BaseModel):
    employee_id: str
    name: str
    designation: str
    department: str
    role: str
    manager_id: Optional[str] = None
    children: List["HierarchyNode"] = []
