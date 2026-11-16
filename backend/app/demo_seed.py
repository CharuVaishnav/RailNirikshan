"""Fill the database with realistic DEMO data so the dashboard looks full.

Run from the backend folder:

    python -m app.demo_seed            # add demo inspections (does nothing if some already exist)
    python -m app.demo_seed --reset    # wipe all inspections/tasks and create the demo data again

It creates 10 inspections across NWR stations, observations for every department,
placeholder before/after photos, and tasks in every state:
open, open + overdue (escalated), fix submitted, rejected once, and closed.

Everything here is made-up demo data. The department of each observation is chosen by the
same AI routing function the app uses (services/ai.py), and notes come from generate_note().
"""
import io
import sys
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import delete, func, select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import AuditLog, ComplianceTask, Department, Inspection, Location, Observation, TaskUpdate, User
from .seed import seed
from .services import ai, storage

# Extra NWR stations so the map has more points (approximate coordinates).
EXTRA_LOCATIONS = [
    ("Udaipur City", "station", "Ajmer", 24.5718, 73.6938),
    ("Alwar Junction", "station", "Jaipur", 27.5610, 76.6250),
    ("Abu Road", "station", "Ajmer", 24.4800, 72.7800),
    ("Sri Ganganagar Junction", "station", "Bikaner", 29.9200, 73.8800),
]

# Task states used below:
#   open      - waiting for the department
#   fix       - staff submitted a fix with an after-photo (senior officer can Accept / Reject)
#   doubtful  - fix submitted, but from far away, so the AI check says "doubtful"
#   rejected  - a fix was rejected once, the point is open again at escalation level 1
#   closed    - fix accepted (number = days taken to close)
#
# (location, inspection type, days ago, approved?, [(observation, state, days to close, fix remark)])
INSPECTIONS = [
    ("Jaipur Junction", "station", 12, True, [
        ("Two lights not working on platform 3 foot over bridge", "closed", 2, "Replaced both LED fittings"),
        ("Litter and garbage near waiting hall entrance", "closed", 1, "Area cleaned, extra dustbin placed"),
        ("Roof leak above platform 2 seating area near bench", "open", None, ""),
        ("CCTV camera at main entrance not recording", "fix", None, "Camera DVR replaced and tested"),
    ]),
    ("Ajmer Junction", "station", 10, True, [
        ("Fire extinguisher missing near parcel office", "open", None, ""),
        ("Drinking water tap broken on platform 1", "closed", 3, "New tap fitted, water flow checked"),
        ("Ceiling fan not working in second class waiting room", "fix", None, "Fan capacitor changed, working now"),
    ]),
    ("Jodhpur Junction", "station", 8, True, [
        ("Cracked tiles on platform 1 floor near exit", "fix", None, "Six tiles replaced and levelled"),
        ("Food stall hygiene poor, pest seen near pantry store", "closed", 4, "Pest control done, stall owner warned"),
        ("Passenger display board on platform 2 showing wrong information", "open", None, ""),
    ]),
    ("Bikaner Junction", "station", 6, True, [
        ("Broken bench in general waiting area", "fix", None, "Bench repaired and repainted"),
        ("Unauthorised vendors on platform 1, RPF presence needed", "closed", 2, "RPF patrol posted, vendors removed"),
        ("Exposed wiring near water cooler switch board", "open", None, ""),
    ]),
    ("LC Gate 101 (demo)", "lc_gate", 5, True, [
        ("Level crossing boom barrier signal lamp dim", "open", None, ""),
        ("Road surface cracked and waterlogged near gate lodge wall", "doubtful", None, "Patch work done"),
    ]),
    ("Udaipur City", "station", 4, True, [
        ("Waterlogging near drain at platform end", "rejected", None, "Drain cleaned"),
        ("Dust and litter in waiting hall", "closed", 1, "Deep cleaning done"),
        ("First aid box empty at station master office", "open", None, ""),
    ]),
    ("Alwar Junction", "coach", 3, True, [
        ("Coach window glass broken in S4", "fix", None, "Window glass replaced"),
        ("Berth cushion torn in coach B2", "open", None, ""),
        ("Pantry car door latch not locking", "open", None, ""),
    ]),
    ("Abu Road", "station", 2, True, [
        ("Platform signage damaged and faded", "open", None, ""),
        ("Lift not working on platform 1", "open", None, ""),
    ]),
    ("Sri Ganganagar Junction", "station", 1, True, [
        ("PA system announcements not audible on platform 2", "open", None, ""),
        ("Garbage bins overflowing near ticket counter", "open", None, ""),
        ("Security staff absent at entry gate baggage scanner", "open", None, ""),
    ]),
    # One draft left unapproved, so the officer app has something in progress to show.
    ("Jaipur Junction", "station", 0, False, [
        ("Escalator stopped on platform 1", None, None, ""),
        ("Paint peeling on waiting room wall", None, None, ""),
    ]),
]

# Checklist item ids for each inspection type. Keep in step with mobile/assets/checklists/*.json
# (the web app has its own copy in dashboard/src/checklists).
CHECKLIST_ITEMS = {
    "station": ["platform_clean", "waiting_hall", "toilets", "drinking_water", "lighting", "fans", "signage",
                "pa_system", "fire_safety", "drainage", "enquiry", "first_aid"],
    "lc_gate": ["gate_operation", "gate_lamp", "road_signs", "road_surface", "telephone", "records", "gateman",
                "visibility"],
    "coach": ["coach_clean", "berths", "doors_windows", "lights_fans", "toilets", "fire_safety", "emergency"],
}

# Items the officer marked "not OK" in each demo inspection (same order as INSPECTIONS, matching its observations).
NOT_OK = [
    ["lighting", "waiting_hall"],
    ["fire_safety", "drinking_water", "fans"],
    ["signage"],
    ["waiting_hall"],
    ["gate_lamp", "road_surface"],
    ["drainage", "waiting_hall", "first_aid"],
    ["doors_windows", "berths"],
    ["signage"],
    ["pa_system", "platform_clean"],
    ["lighting"],
]

DEPT_COLOURS = {
    "ENGG": (120, 98, 70), "ELEC": (190, 150, 40), "COMM": (60, 120, 90), "MECH": (80, 95, 125),
    "SNT": (95, 80, 140), "MED": (150, 80, 100), "SEC": (70, 80, 90),
}


def _font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)   # no system font (for example on Vercel): Pillow's built-in font


def _wrap(text: str, width: int = 44) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line]


def make_photo(kind: str, text: str, place: str, when: datetime, dept_code: str) -> bytes:
    """Draw a simple placeholder 'photo' (JPEG): BEFORE = problem, AFTER = fixed."""
    w, h = 640, 480
    base = DEPT_COLOURS.get(dept_code, (90, 90, 90))
    after = kind == "AFTER"
    img = Image.new("RGB", (w, h), tuple(min(255, c + 70) for c in base) if after else base)
    d = ImageDraw.Draw(img)
    # a simple "platform" scene: floor, edge line and pillars
    d.rectangle([0, 330, w, h], fill=(170, 170, 165) if after else (120, 118, 112))
    d.rectangle([0, 322, w, 334], fill=(235, 200, 40))
    for x in (90, 300, 510):
        d.rectangle([x, 150, x + 26, 330], fill=(60, 60, 66))
    if after:
        d.line([(250, 395), (290, 435), (380, 350)], fill=(30, 140, 60), width=16)   # tick mark
    else:
        d.line([(260, 360), (370, 440)], fill=(183, 49, 44), width=16)               # cross mark
        d.line([(370, 360), (260, 440)], fill=(183, 49, 44), width=16)
    # banner and caption
    d.rectangle([0, 0, w, 56], fill=(30, 140, 60) if after else (183, 49, 44))
    d.text((16, 12), f"{kind}  -  DEMO PLACEHOLDER PHOTO", font=_font(26), fill="white")
    y = 70
    for line in _wrap(text):
        d.text((16, y), line, font=_font(24), fill="white")
        y += 30
    d.rectangle([0, h - 34, w, h], fill=(27, 42, 74))
    d.text((16, h - 28), f"{place}   |   {when:%d %b %Y %H:%M} UTC", font=_font(18), fill="white")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def reset(db) -> None:
    """Delete all inspections, tasks and demo photos. Users, departments and locations stay."""
    for model in (TaskUpdate, ComplianceTask, Observation, Inspection, AuditLog):
        db.execute(delete(model))
    storage.delete_demo_photos(db)
    db.commit()


def demo_seed(do_reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    seed()  # departments, users and the base locations (skips itself if already done)
    db = SessionLocal()
    try:
        if do_reset:
            reset(db)
        elif db.scalar(select(func.count()).select_from(Inspection)):
            print("There are already inspections in the database. "
                  "Run  python -m app.demo_seed --reset  to wipe them and load fresh demo data.")
            return

        for n, k, dv, la, lo in EXTRA_LOCATIONS:
            if db.scalar(select(Location).where(Location.name == n)) is None:
                db.add(Location(name=n, kind=k, division=dv, latitude=la, longitude=lo))
        db.flush()

        depts = {d.code: d for d in db.scalars(select(Department)).all()}
        officer = db.scalar(select(User).where(User.username == "officer"))
        senior = db.scalar(select(User).where(User.username == "senior"))
        staff = {u.department_id: u for u in db.scalars(select(User).where(User.role == "staff")).all()}
        now = datetime.utcnow()
        n_obs = 0
        counts: dict[str, int] = {}

        for number, (loc_name, kind, days_ago, approved, points) in enumerate(INSPECTIONS):
            loc = db.scalar(select(Location).where(Location.name == loc_name))
            created = now - timedelta(days=days_ago, hours=3 if days_ago else 1)
            checklist = {item: item not in NOT_OK[number] for item in CHECKLIST_ITEMS[kind]}
            insp = Inspection(officer_id=officer.id, location_id=loc.id, inspection_type=kind,
                              checklist=checklist, created_at=created)
            db.add(insp)
            db.flush()
            note_items = []

            for i, (text, state, close_days, remark) in enumerate(points):
                n_obs += 1
                code = ai.route_department(text)          # the real AI routing baseline
                if code is None:
                    raise SystemExit(f"Routing found no department for: {text!r}")
                dept = depts[code]
                lat, lon = loc.latitude + 0.0002 * (i + 1), loc.longitude + 0.0001 * (i + 1)
                seen_at = created + timedelta(minutes=10 * (i + 1))
                before_key = storage.save_photo(make_photo("BEFORE", text, loc.name, seen_at, code), "",
                                                db, key=f"demo_{n_obs:02d}_before.jpg")
                obs = Observation(inspection_id=insp.id, text=text, photo_key=before_key, latitude=lat, longitude=lon,
                                  ai_defects=[], suggested_department_id=dept.id, created_at=seen_at)
                db.add(obs)
                db.flush()
                note_items.append({"text": text, "department": dept.name})
                if not approved:
                    continue

                issued = created + timedelta(hours=1)
                task = ComplianceTask(observation_id=obs.id, department_id=dept.id, created_at=issued,
                                      deadline=issued + timedelta(days=settings.default_deadline_days))
                db.add(task)
                db.flush()
                overdue = task.deadline < now

                if state in ("fix", "doubtful", "rejected", "closed"):
                    fixed_at = issued + timedelta(days=close_days) if close_days else min(
                        now - timedelta(hours=5), issued + timedelta(days=2))
                    # a real fix is done at the same spot; the "doubtful" one is sent from about 1 km away
                    f_lat, f_lon = (lat + 0.01, lon) if state == "doubtful" else (lat + 0.00005, lon)
                    check = ai.verify_fix({"lat": lat, "lon": lon, "defects": []},
                                          {"lat": f_lat, "lon": f_lon, "defects": []})
                    after_key = storage.save_photo(make_photo("AFTER", remark, loc.name, fixed_at, code), "",
                                                   db, key=f"demo_{n_obs:02d}_after.jpg")
                    db.add(TaskUpdate(task_id=task.id, user_id=staff[dept.id].id, remark=remark, photo_key=after_key,
                                      latitude=f_lat, longitude=f_lon, verification=check,
                                      created_at=fixed_at - timedelta(hours=2)))
                    task.status = "fix_submitted"
                if state == "closed":
                    task.status, task.closed_at = "closed", fixed_at
                    db.add(TaskUpdate(task_id=task.id, user_id=senior.id, remark="Fix accepted", created_at=fixed_at))
                elif state == "rejected":
                    task.status, task.escalation_level = "open", 1
                    db.add(TaskUpdate(task_id=task.id, user_id=senior.id, created_at=fixed_at,
                                      remark="Fix rejected: water still standing, clean the drain fully"))
                elif state == "open" and overdue:
                    task.escalation_level = 2 if days_ago >= 10 else 1   # as if the escalation job already ran

                label = "overdue (not closed)" if overdue and task.status != "closed" else None
                counts[task.status] = counts.get(task.status, 0) + 1
                if label:
                    counts[label] = counts.get(label, 0) + 1

            if approved:
                insp.note_text = ai.generate_note(loc.name, kind, created.strftime("%d %b %Y"), note_items)
                insp.status, insp.approved_at = "approved", created + timedelta(hours=1)

        db.commit()
        print(f"Demo data ready: {len(INSPECTIONS)} inspections, {n_obs} observations with photos.")
        print("Tasks: " + ", ".join(f"{k} = {v}" for k, v in sorted(counts.items())))
    finally:
        db.close()


if __name__ == "__main__":
    demo_seed(do_reset="--reset" in sys.argv)
