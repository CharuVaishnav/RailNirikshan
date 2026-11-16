"""Database tables for RailNirikshan."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.utcnow()


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)   # e.g. ENGG, ELEC, COMM
    name: Mapped[str] = mapped_column(String(100))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    designation: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)   # for free email alerts
    # roles: admin, officer (inspects), staff (fixes), senior (views dashboard)
    role: Mapped[str] = mapped_column(String(20))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    department: Mapped[Department | None] = relationship()


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(30))          # station, lc_gate, depot, office
    division: Mapped[str] = mapped_column(String(50))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class Inspection(Base):
    __tablename__ = "inspections"
    id: Mapped[int] = mapped_column(primary_key=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    inspection_type: Mapped[str] = mapped_column(String(30))  # station, lc_gate, coach, pantry, ...
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, approved
    checklist: Mapped[dict] = mapped_column(JSON, default=dict)
    note_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    officer: Mapped[User] = relationship()
    location: Mapped[Location] = relationship()
    observations: Mapped[list["Observation"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"))
    text: Mapped[str] = mapped_column(Text)
    photo_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_defects: Mapped[list] = mapped_column(JSON, default=list)
    suggested_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    inspection: Mapped[Inspection] = relationship(back_populates="observations")
    suggested_department: Mapped[Department | None] = relationship()


class ComplianceTask(Base):
    __tablename__ = "compliance_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    deadline: Mapped[datetime] = mapped_column(DateTime)
    # open -> fix_submitted -> closed   (or back to open if the fix is rejected)
    status: Mapped[str] = mapped_column(String(20), default="open")
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    observation: Mapped[Observation] = relationship()
    department: Mapped[Department] = relationship()
    updates: Mapped[list["TaskUpdate"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskUpdate(Base):
    __tablename__ = "task_updates"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("compliance_tasks.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    remark: Mapped[str] = mapped_column(Text, default="")
    photo_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    task: Mapped[ComplianceTask] = relationship(back_populates="updates")
    user: Mapped[User] = relationship()


class StoredPhoto(Base):
    """A photo kept inside the database. Used only when STORAGE_BACKEND=db,
    which is how the online copy on Vercel works (it has no permanent disk)."""
    __tablename__ = "stored_photos"
    key: Mapped[str] = mapped_column(String(300), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
