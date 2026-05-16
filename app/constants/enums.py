from enum import Enum


class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    HR = "HR"
    ADMIN = "ADMIN"


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class GoalStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    RETURNED = "RETURNED"
    LOCKED = "LOCKED"


class UoM(str, Enum):
    MIN = "MIN"
    MAX = "MAX"
    TIMELINE = "TIMELINE"
    ZERO = "ZERO"