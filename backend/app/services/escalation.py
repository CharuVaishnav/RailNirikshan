"""Overdue points: raise the escalation level and send reminder emails.

A point that is still open after its deadline goes up one step at a time:

    step 1   the deadline has passed    reminder email to the department's staff
    step 2   3 days overdue             second reminder
    step 3   7 days overdue             the senior officers get the email as well

Each step raises the point's escalation level by one. (A rejected fix also raises the level,
in routers/tasks.py, so the level can be higher than the step.)

The check is run every hour by `python -m app.escalate` (Windows Task Scheduler), and can also
be started from the dashboard. It is safe to run as often as you like: the steps a point has
already taken are counted from the audit log, so no step happens twice.
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..models import AuditLog, ComplianceTask, User
from . import notify

STEPS_AFTER_DAYS = (0, 3, 7)


def steps_due(deadline: datetime, now: datetime) -> int:
    """How many steps an open point should have taken by now (0 when it is not overdue)."""
    days_late = (now - deadline).total_seconds() / 86400
    return sum(1 for days in STEPS_AFTER_DAYS if days_late > days)


def _lines(tasks: list[ComplianceTask], now: datetime) -> str:
    out = []
    for t in tasks:
        place = t.observation.inspection.location.name
        out.append(f"#{t.id}  {place}  -  due {t.deadline:%d %b %Y}, {max(0, (now - t.deadline).days)} days overdue, "
                   f"level {t.escalation_level}\n     {t.observation.text}")
    return "\n\n".join(out)


def run(db: Session, actor_id: int | None = None, now: datetime | None = None) -> dict:
    """Escalate every overdue open point that is due for its next step. Returns a short summary."""
    now = now or datetime.utcnow()
    overdue = db.scalars(select(ComplianceTask).where(
        ComplianceTask.status == "open", ComplianceTask.deadline < now).order_by(ComplianceTask.deadline)).all()
    done = dict(db.execute(
        select(AuditLog.entity_id, func.count()).where(AuditLog.action == "escalate", AuditLog.entity == "task")
        .group_by(AuditLog.entity_id)).all())

    raised: list[ComplianceTask] = []
    to_senior: list[ComplianceTask] = []
    for t in overdue:
        due = steps_due(t.deadline, now)
        new_steps = due - done.get(t.id, 0)
        if new_steps <= 0:
            continue
        t.escalation_level += new_steps
        for _ in range(new_steps):
            audit.log(db, actor_id, "escalate", "task", t.id)
        raised.append(t)
        if due >= len(STEPS_AFTER_DAYS):
            to_senior.append(t)

    emails = 0
    by_department: dict[int, list[ComplianceTask]] = {}
    for t in raised:
        by_department.setdefault(t.department_id, []).append(t)
    for dept_id, tasks in by_department.items():
        staff = db.scalars(select(User).where(User.role == "staff", User.department_id == dept_id,
                                              User.is_active, User.email.is_not(None))).all()
        for u in staff:
            emails += notify.send_email(
                u.email,
                f"RailNirikshan: {len(tasks)} overdue point(s) for {tasks[0].department.name}",
                "These inspection points are past their deadline and still open:\n\n"
                f"{_lines(tasks, now)}\n\nPlease fix them and upload an after-photo in RailNirikshan.")
    if to_senior:
        for u in db.scalars(select(User).where(User.role == "senior", User.is_active, User.email.is_not(None))).all():
            emails += notify.send_email(
                u.email,
                f"RailNirikshan: {len(to_senior)} point(s) overdue by a week or more",
                "These inspection points have been escalated to you because they are still open "
                f"a week after the deadline:\n\n{_lines(to_senior, now)}")

    db.commit()
    return {
        "overdue": len(overdue),
        "escalated": len(raised),
        "emails_sent": emails,
        "email_on": bool(settings.smtp_user),
        "points": [{"id": t.id, "level": t.escalation_level, "department": t.department.name} for t in raised],
    }
