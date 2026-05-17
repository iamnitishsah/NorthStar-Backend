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


class ProgressStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    ON_TRACK = "ON_TRACK"
    COMPLETED = "COMPLETED"


class UOMType(str, Enum):
    NUMERIC = "NUMERIC"
    PERCENTAGE = "PERCENTAGE"
    TIMELINE = "TIMELINE"
    ZERO_BASED = "ZERO_BASED"


class MeasurementType(str, Enum):
    MIN = "MIN"
    MAX = "MAX"