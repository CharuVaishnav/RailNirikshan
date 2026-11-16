from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..database import get_db
from ..models import ComplianceTask, Department, Inspection, Location, Observation, User
from ..schemas import InspectionCreate, InspectionOut, NoteUpdate, ObservationOut, RoutingOverride
from ..security import current_user, require_roles
from ..services import ai, storage

router = APIRouter(prefix="/inspections", tags=["inspections"])


def _get_own_inspection(db: Session, inspection_id: int, user: User) -> Inspection:
    insp = db.get(Inspection, inspection_id)
    if insp is None:
        raise HTTPException(404, "Inspection not found")
    if user.role == "officer" and insp.officer_id != user.id:
        raise HTTPException(403, "Not your inspection")
    return insp


@router.post("", response_model=InspectionOut)
def create_inspection(body: InspectionCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_roles("officer", "admin"))):
    if db.get(Location, body.location_id) is None:
        raise HTTPException(400, "Unknown location")
    insp = Inspection(officer_id=user.id, location_id=body.location_id,
                      inspection_type=body.inspection_type, checklist=body.checklist)
    db.add(insp)
    db.flush()
    audit.log(db, user.id, "create", "inspection", insp.id)
    db.commit()
    db.refresh(insp)
    return insp


@router.get("", response_model=list[InspectionOut])
def list_inspections(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Inspection).order_by(Inspection.created_at.desc())
    if user.role == "officer":
        q = q.where(Inspection.officer_id == user.id)
    return db.scalars(q).all()


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _get_own_inspection(db, inspection_id, user)


@router.post("/{inspection_id}/observations", response_model=ObservationOut)
async def add_observation(
    inspection_id: int,
    text: str = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("officer", "admin")),
):
    insp = _get_own_inspection(db, inspection_id, user)
    if insp.status != "draft":
        raise HTTPException(400, "Inspection is already approved")
    photo_key, defects = None, []
    if photo is not None:
        data = await photo.read()
        photo_key = storage.save_photo(data, photo.filename, db)
        defects = ai.detect_defects(data)
    dept_code = ai.route_department(text)
    dept = db.scalar(select(Department).where(Department.code == dept_code)) if dept_code else None
    obs = Observation(inspection_id=insp.id, text=text, latitude=latitude, longitude=longitude,
                      photo_key=photo_key, ai_defects=defects,
                      suggested_department_id=dept.id if dept else None)
    db.add(obs)
    insp.note_text = ""   # the note no longer matches the observations: it must be generated again
    db.flush()
    audit.log(db, user.id, "add_observation", "observation", obs.id)
    db.commit()
    db.refresh(obs)
    return obs


@router.delete("/{inspection_id}/observations/{obs_id}", status_code=204)
def delete_observation(inspection_id: int, obs_id: int, db: Session = Depends(get_db),
                       user: User = Depends(require_roles("officer", "admin"))):
    """Remove a wrong observation. Only possible while the inspection is still a draft."""
    insp = _get_own_inspection(db, inspection_id, user)
    if insp.status != "draft":
        raise HTTPException(400, "Inspection is already approved")
    obs = db.get(Observation, obs_id)
    if obs is None or obs.inspection_id != inspection_id:
        raise HTTPException(404, "Observation not found")
    if obs.photo_key:
        storage.delete_photo(obs.photo_key, db)
    db.delete(obs)
    insp.note_text = ""
    audit.log(db, user.id, "delete_observation", "observation", obs_id)
    db.commit()
    return Response(status_code=204)


@router.put("/{inspection_id}/observations/{obs_id}/department", response_model=ObservationOut)
def override_department(inspection_id: int, obs_id: int, body: RoutingOverride,
                        db: Session = Depends(get_db), user: User = Depends(require_roles("officer", "admin"))):
    """The officer can correct the AI's department suggestion. Corrections become training data."""
    insp = _get_own_inspection(db, inspection_id, user)
    if insp.status != "draft":
        raise HTTPException(400, "Inspection is already approved")
    obs = db.get(Observation, obs_id)
    if obs is None or obs.inspection_id != inspection_id:
        raise HTTPException(404, "Observation not found")
    if db.get(Department, body.department_id) is None:
        raise HTTPException(400, "Unknown department")
    obs.suggested_department_id = body.department_id
    insp.note_text = ""   # the note names the department of each point, so it must be generated again
    audit.log(db, user.id, "override_department", "observation", obs.id)
    db.commit()
    db.refresh(obs)
    return obs


@router.post("/{inspection_id}/generate-note", response_model=InspectionOut)
def generate_note(inspection_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_roles("officer", "admin"))):
    insp = _get_own_inspection(db, inspection_id, user)
    obs = [{"text": o.text, "department": o.suggested_department.name if o.suggested_department else None}
           for o in insp.observations]
    if not obs:
        raise HTTPException(400, "Add at least one observation first")
    insp.note_text = ai.generate_note(insp.location.name, insp.inspection_type,
                                      insp.created_at.strftime("%d %b %Y"), obs)
    db.commit()
    db.refresh(insp)
    return insp


@router.put("/{inspection_id}/note", response_model=InspectionOut)
def edit_note(inspection_id: int, body: NoteUpdate, db: Session = Depends(get_db),
              user: User = Depends(require_roles("officer", "admin"))):
    insp = _get_own_inspection(db, inspection_id, user)
    insp.note_text = body.note_text
    db.commit()
    db.refresh(insp)
    return insp


@router.post("/{inspection_id}/approve", response_model=InspectionOut)
def approve(inspection_id: int, db: Session = Depends(get_db),
            user: User = Depends(require_roles("officer", "admin"))):
    """Officer approves the note. Every observation becomes a compliance task."""
    insp = _get_own_inspection(db, inspection_id, user)
    if insp.status != "draft":
        raise HTTPException(400, "Already approved")
    missing = [o.id for o in insp.observations if o.suggested_department_id is None]
    if missing:
        raise HTTPException(400, f"Choose a department for observations {missing} before approving")
    deadline = datetime.utcnow() + timedelta(days=settings.default_deadline_days)
    for o in insp.observations:
        db.add(ComplianceTask(observation_id=o.id, department_id=o.suggested_department_id, deadline=deadline))
    insp.status = "approved"
    insp.approved_at = datetime.utcnow()
    audit.log(db, user.id, "approve", "inspection", insp.id)
    db.commit()
    db.refresh(insp)
    return insp


@router.get("/photos/{key}")
def get_photo(key: str, _: User = Depends(current_user)):
    if "/" in key or ".." in key:
        raise HTTPException(400, "Bad key")
    try:
        return Response(storage.load_photo(key), media_type="image/jpeg")
    except FileNotFoundError:
        raise HTTPException(404, "Photo not found")
