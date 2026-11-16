"""Request and response shapes for the API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class DepartmentOut(ORM):
    id: int
    code: str
    name: str


class UserOut(ORM):
    id: int
    username: str
    full_name: str
    designation: str
    role: str
    department: DepartmentOut | None = None


class LocationOut(ORM):
    id: int
    name: str
    kind: str
    division: str
    latitude: float
    longitude: float


class InspectionCreate(BaseModel):
    location_id: int
    inspection_type: str
    checklist: dict = {}


class ObservationOut(ORM):
    id: int
    text: str
    photo_key: str | None
    latitude: float | None
    longitude: float | None
    ai_defects: list
    suggested_department: DepartmentOut | None = None
    created_at: datetime


class InspectionOut(ORM):
    id: int
    inspection_type: str
    status: str
    checklist: dict
    note_text: str
    created_at: datetime
    approved_at: datetime | None
    location: LocationOut
    officer: UserOut
    observations: list[ObservationOut] = []


class NoteUpdate(BaseModel):
    note_text: str


class RoutingOverride(BaseModel):
    department_id: int


class TaskUpdateOut(ORM):
    id: int
    remark: str
    photo_key: str | None
    verification: dict
    created_at: datetime
    user: UserOut


class TaskOut(ORM):
    id: int
    status: str
    deadline: datetime
    escalation_level: int
    created_at: datetime
    closed_at: datetime | None
    department: DepartmentOut
    observation: ObservationOut
    updates: list[TaskUpdateOut] = []


class DecisionIn(BaseModel):
    remark: str = ""
