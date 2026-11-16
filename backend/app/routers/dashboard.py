from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ComplianceTask, Department, Inspection, Location, Observation, User
from ..security import require_roles

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(require_roles("senior", "admin"))):
    now = datetime.utcnow()
    by_status = dict(db.execute(select(ComplianceTask.status, func.count()).group_by(ComplianceTask.status)).all())
    overdue = db.scalar(select(func.count()).select_from(ComplianceTask).where(
        ComplianceTask.status != "closed", ComplianceTask.deadline < now)) or 0

    by_department = [
        {"department": name, "pending": pending}
        for name, pending in db.execute(
            select(Department.name, func.count(ComplianceTask.id))
            .join(ComplianceTask, ComplianceTask.department_id == Department.id)
            .where(ComplianceTask.status != "closed")
            .group_by(Department.name)
            .order_by(func.count(ComplianceTask.id).desc())
        ).all()
    ]

    by_location = [
        {"location": name, "latitude": lat, "longitude": lon, "pending": pending}
        for name, lat, lon, pending in db.execute(
            select(Location.name, Location.latitude, Location.longitude, func.count(ComplianceTask.id))
            .join(Inspection, Inspection.location_id == Location.id)
            .join(Observation, Observation.inspection_id == Inspection.id)
            .join(ComplianceTask, ComplianceTask.observation_id == Observation.id)
            .where(ComplianceTask.status != "closed")
            .group_by(Location.name, Location.latitude, Location.longitude)
        ).all()
    ]

    closed = db.scalars(select(ComplianceTask).where(ComplianceTask.closed_at.is_not(None))).all()
    avg_days = round(sum((t.closed_at - t.created_at).total_seconds() for t in closed) / 86400 / len(closed), 1) if closed else None

    return {
        "inspections": db.scalar(select(func.count()).select_from(Inspection)) or 0,
        "tasks_by_status": by_status,
        "overdue": overdue,
        "pending_by_department": by_department,
        "pending_by_location": by_location,
        "avg_days_to_close": avg_days,
    }
