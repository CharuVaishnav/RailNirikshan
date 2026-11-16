from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..models import ComplianceTask, Inspection, Observation, TaskUpdate, User
from ..schemas import DecisionIn, TaskOut
from ..security import current_user, require_roles
from ..services import ai, notify, storage

router = APIRouter(prefix="/tasks", tags=["compliance tasks"])


def _visible_tasks_query(user: User):
    q = select(ComplianceTask).order_by(ComplianceTask.deadline)
    if user.role == "staff":
        q = q.where(ComplianceTask.department_id == user.department_id)
    elif user.role == "officer":
        q = (q.join(Observation, ComplianceTask.observation_id == Observation.id)
              .join(Inspection, Observation.inspection_id == Inspection.id)
              .where(Inspection.officer_id == user.id))
    return q


def _get_task(db: Session, task_id: int, user: User) -> ComplianceTask:
    task = db.get(ComplianceTask, task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    if user.role == "staff" and task.department_id != user.department_id:
        raise HTTPException(403, "This task belongs to another department")
    if user.role == "officer" and task.observation.inspection.officer_id != user.id:
        raise HTTPException(403, "Not your inspection")
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = _visible_tasks_query(user)
    if status:
        q = q.where(ComplianceTask.status == status)
    return db.scalars(q).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _get_task(db, task_id, user)


@router.post("/{task_id}/fix", response_model=TaskOut)
async def submit_fix(
    task_id: int,
    remark: str = Form(""),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("staff", "admin")),
):
    """Staff report that the issue is fixed, with an after-photo. AI checks the fix."""
    task = _get_task(db, task_id, user)
    if task.status == "closed":
        raise HTTPException(400, "Task already closed")
    photo_key, after_defects = None, []
    if photo is not None:
        data = await photo.read()
        photo_key = storage.save_photo(data, photo.filename)
        after_defects = ai.detect_defects(data)
    obs = task.observation
    verification = ai.verify_fix(
        {"lat": obs.latitude, "lon": obs.longitude, "defects": obs.ai_defects},
        {"lat": latitude, "lon": longitude, "defects": after_defects},
    )
    db.add(TaskUpdate(task_id=task.id, user_id=user.id, remark=remark, photo_key=photo_key,
                      latitude=latitude, longitude=longitude, verification=verification))
    task.status = "fix_submitted"
    audit.log(db, user.id, "submit_fix", "task", task.id)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/close", response_model=TaskOut)
def close_task(task_id: int, body: DecisionIn, db: Session = Depends(get_db),
               user: User = Depends(require_roles("officer", "senior", "admin"))):
    task = _get_task(db, task_id, user)
    if task.status != "fix_submitted":
        raise HTTPException(400, "No fix has been submitted yet")
    task.status = "closed"
    task.closed_at = datetime.utcnow()
    db.add(TaskUpdate(task_id=task.id, user_id=user.id, remark=body.remark or "Fix accepted"))
    audit.log(db, user.id, "close", "task", task.id)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/reject", response_model=TaskOut)
def reject_fix(task_id: int, body: DecisionIn, db: Session = Depends(get_db),
               user: User = Depends(require_roles("officer", "senior", "admin"))):
    task = _get_task(db, task_id, user)
    if task.status != "fix_submitted":
        raise HTTPException(400, "No fix has been submitted yet")
    task.status = "open"
    task.escalation_level += 1
    db.add(TaskUpdate(task_id=task.id, user_id=user.id, remark=body.remark or "Fix rejected"))
    audit.log(db, user.id, "reject", "task", task.id)
    db.commit()
    db.refresh(task)
    return task


@router.post("/run-escalation")
def run_escalation(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "senior"))):
    """Raise the escalation level of every overdue open task.
    Week 4: call this every hour (Windows Task Scheduler, cron, or a loop script) to send free email alerts.
    """
    overdue = db.scalars(select(ComplianceTask).where(
        ComplianceTask.status == "open", ComplianceTask.deadline < datetime.utcnow())).all()
    emailed = 0
    for t in overdue:
        t.escalation_level += 1
        audit.log(db, user.id, "escalate", "task", t.id)
        staff = db.scalars(select(User).where(User.role == "staff", User.department_id == t.department_id,
                                              User.email.is_not(None))).all()
        for u in staff:
            emailed += notify.send_email(
                u.email,
                f"RailNirikshan: point #{t.id} is overdue (level {t.escalation_level})",
                f"Inspection point #{t.id} was due on {t.deadline:%d %b %Y} and is still open.\n\n"
                f"{t.observation.text}\n\nPlease fix it and upload an after-photo in the app.",
            )
    db.commit()
    return {"escalated": len(overdue), "emails_sent": emailed}
