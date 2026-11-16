"""Admin screens: add and change users, departments and locations. Only the admin role can use these.

Users are never deleted, only switched off, so old inspections and fixes keep the right names.
A department or location can be deleted only while nothing refers to it.
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..models import ComplianceTask, Department, Inspection, Location, Observation, User
from ..schemas import (AdminUserOut, DepartmentCreate, DepartmentEdit, DepartmentOut, LocationIn, LocationOut,
                       UserCreate, UserEdit)
from ..security import hash_password, require_roles

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_roles("admin")

ROLES = ("officer", "staff", "senior", "admin")
LOCATION_KINDS = ("station", "lc_gate", "depot", "office")


def _text(value: str | None, name: str, limit: int) -> str:
    value = (value or "").strip()
    if not value:
        raise HTTPException(400, f"{name} is needed")
    if len(value) > limit:
        raise HTTPException(400, f"{name} is too long (at most {limit} characters)")
    return value


def _email(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) or len(value) > 120:
        raise HTTPException(400, "That email address does not look right")
    return value


def _password(value: str) -> str:
    if len(value) < 6:
        raise HTTPException(400, "The password needs at least 6 characters")
    return hash_password(value)


def _role_and_department(db: Session, role: str, department_id: int | None) -> int | None:
    """Staff belong to one department; the other roles belong to none."""
    if role not in ROLES:
        raise HTTPException(400, f"The role must be one of: {', '.join(ROLES)}")
    if role != "staff":
        return None
    if department_id is None or db.get(Department, department_id) is None:
        raise HTTPException(400, "Choose the department for a staff user")
    return department_id


# ---- users ----------------------------------------------------------------

@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.scalars(select(User).order_by(User.full_name)).all()


@router.post("/users", response_model=AdminUserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    username = body.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.]{3,50}", username):
        raise HTTPException(400, "The username needs 3 to 50 characters: small letters, digits, _ or .")
    if db.scalar(select(User).where(User.username == username)) is not None:
        raise HTTPException(400, f"The username '{username}' is already taken")
    user = User(username=username, password_hash=_password(body.password),
                full_name=_text(body.full_name, "The full name", 100),
                designation=(body.designation or "").strip()[:100], email=_email(body.email), role=body.role,
                department_id=_role_and_department(db, body.role, body.department_id))
    db.add(user)
    db.flush()
    audit.log(db, admin.id, "create", "user", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=AdminUserOut)
def edit_user(user_id: int, body: UserEdit, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and (not body.is_active or body.role != "admin"):
        # otherwise the last admin could lock everyone out of these screens
        raise HTTPException(400, "You cannot switch off your own account or change your own role")
    user.full_name = _text(body.full_name, "The full name", 100)
    user.designation = (body.designation or "").strip()[:100]
    user.email = _email(body.email)
    user.department_id = _role_and_department(db, body.role, body.department_id)
    user.role = body.role
    user.is_active = body.is_active
    if body.password:
        user.password_hash = _password(body.password)
    audit.log(db, admin.id, "edit", "user", user.id)
    db.commit()
    db.refresh(user)
    return user


# ---- departments ----------------------------------------------------------

@router.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(body: DepartmentCreate, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    code = body.code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,20}", code):
        raise HTTPException(400, "The code needs 2 to 20 capital letters or digits, for example ENGG")
    if db.scalar(select(Department).where(Department.code == code)) is not None:
        raise HTTPException(400, f"The code '{code}' is already used")
    dept = Department(code=code, name=_text(body.name, "The department name", 100))
    db.add(dept)
    db.flush()
    audit.log(db, admin.id, "create", "department", dept.id)
    db.commit()
    db.refresh(dept)
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentOut)
def edit_department(dept_id: int, body: DepartmentEdit, db: Session = Depends(get_db),
                    admin: User = Depends(admin_only)):
    dept = db.get(Department, dept_id)
    if dept is None:
        raise HTTPException(404, "Department not found")
    dept.name = _text(body.name, "The department name", 100)
    audit.log(db, admin.id, "edit", "department", dept.id)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/departments/{dept_id}", status_code=204)
def delete_department(dept_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    dept = db.get(Department, dept_id)
    if dept is None:
        raise HTTPException(404, "Department not found")
    used_by = (
        (db.scalar(select(func.count()).select_from(User).where(User.department_id == dept_id)) or 0)
        + (db.scalar(select(func.count()).select_from(ComplianceTask)
                     .where(ComplianceTask.department_id == dept_id)) or 0)
        + (db.scalar(select(func.count()).select_from(Observation)
                     .where(Observation.suggested_department_id == dept_id)) or 0)
    )
    if used_by:
        raise HTTPException(400, "This department has staff or inspection points, so it cannot be deleted")
    db.delete(dept)
    audit.log(db, admin.id, "delete", "department", dept_id)
    db.commit()
    return Response(status_code=204)


# ---- locations ------------------------------------------------------------

def _fill_location(loc: Location, body: LocationIn) -> None:
    if body.kind not in LOCATION_KINDS:
        raise HTTPException(400, f"The type must be one of: {', '.join(LOCATION_KINDS)}")
    if not (-90 <= body.latitude <= 90 and -180 <= body.longitude <= 180):
        raise HTTPException(400, "Latitude must be between -90 and 90, longitude between -180 and 180")
    loc.name = _text(body.name, "The location name", 120)
    loc.kind = body.kind
    loc.division = _text(body.division, "The division", 50)
    loc.latitude, loc.longitude = body.latitude, body.longitude


@router.post("/locations", response_model=LocationOut, status_code=201)
def create_location(body: LocationIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    loc = Location()
    _fill_location(loc, body)
    db.add(loc)
    db.flush()
    audit.log(db, admin.id, "create", "location", loc.id)
    db.commit()
    db.refresh(loc)
    return loc


@router.put("/locations/{location_id}", response_model=LocationOut)
def edit_location(location_id: int, body: LocationIn, db: Session = Depends(get_db),
                  admin: User = Depends(admin_only)):
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(404, "Location not found")
    _fill_location(loc, body)
    audit.log(db, admin.id, "edit", "location", loc.id)
    db.commit()
    db.refresh(loc)
    return loc


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(location_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(404, "Location not found")
    if db.scalar(select(func.count()).select_from(Inspection).where(Inspection.location_id == location_id)):
        raise HTTPException(400, "This location has inspections, so it cannot be deleted")
    db.delete(loc)
    audit.log(db, admin.id, "delete", "location", location_id)
    db.commit()
    return Response(status_code=204)
