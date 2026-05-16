from enum import Enum


class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    HR = "HR"


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"