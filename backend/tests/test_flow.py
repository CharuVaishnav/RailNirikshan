"""End-to-end test of the full inspection cycle. Run from the backend folder:  pytest -q"""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["LOCAL_UPLOAD_DIR"] = f"{_tmp}/uploads"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

seed()
client = TestClient(app)


def login(username: str) -> dict:
    r = client.post("/auth/login", json={"username": username, "password": "demo123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_full_inspection_cycle():
    officer = login("officer")

    # 1. Officer starts an inspection
    loc = client.get("/locations", headers=officer).json()[0]
    insp = client.post("/inspections", headers=officer,
                       json={"location_id": loc["id"], "inspection_type": "station",
                             "checklist": {"platform_clean": False, "lights_working": True}}).json()
    assert insp["status"] == "draft"

    # 2. Adds observations (one with a photo); AI suggests the department
    o1 = client.post(f"/inspections/{insp['id']}/observations", headers=officer,
                     data={"text": "Two lights not working on platform 3 foot over bridge",
                           "latitude": loc["latitude"], "longitude": loc["longitude"]},
                     files={"photo": ("before.jpg", b"fake-image-bytes", "image/jpeg")}).json()
    assert o1["suggested_department"]["code"] == "ELEC"
    assert o1["photo_key"]

    o2 = client.post(f"/inspections/{insp['id']}/observations", headers=officer,
                     data={"text": "Litter and garbage near waiting hall entrance"}).json()
    assert o2["suggested_department"]["code"] == "COMM"

    # 3. AI drafts the note, officer approves -> tasks created
    note = client.post(f"/inspections/{insp['id']}/generate-note", headers=officer).json()["note_text"]
    assert "1." in note and "2." in note
    approved = client.post(f"/inspections/{insp['id']}/approve", headers=officer).json()
    assert approved["status"] == "approved"

    # 4. Electrical staff see only their task and submit a fix
    elec = login("staff_elec")
    tasks = client.get("/tasks", headers=elec).json()
    assert len(tasks) == 1
    fixed = client.post(f"/tasks/{tasks[0]['id']}/fix", headers=elec,
                        data={"remark": "Replaced both LED fittings",
                              "latitude": loc["latitude"] + 0.0001, "longitude": loc["longitude"]},
                        files={"photo": ("after.jpg", b"fake-after-bytes", "image/jpeg")}).json()
    assert fixed["status"] == "fix_submitted"
    assert fixed["updates"][-1]["verification"]["result"] == "looks_fixed"

    # Commercial staff cannot touch the electrical task
    comm = login("staff_comm")
    assert client.post(f"/tasks/{tasks[0]['id']}/fix", headers=comm, data={"remark": "x"}).status_code == 403

    # 5. Officer closes it
    closed = client.post(f"/tasks/{tasks[0]['id']}/close", headers=officer, json={"remark": "Verified"}).json()
    assert closed["status"] == "closed"

    # 6. Senior officer dashboard
    senior = login("senior")
    s = client.get("/dashboard/summary", headers=senior).json()
    assert s["tasks_by_status"].get("closed") == 1
    assert s["tasks_by_status"].get("open") == 1
    assert s["pending_by_department"][0]["department"] == "Commercial"


def test_officer_can_remove_an_observation_from_a_draft():
    officer = login("officer")
    loc = client.get("/locations", headers=officer).json()[0]
    insp = client.post("/inspections", headers=officer,
                       json={"location_id": loc["id"], "inspection_type": "station", "checklist": {}}).json()
    base = f"/inspections/{insp['id']}"
    keep = client.post(f"{base}/observations", headers=officer, data={"text": "Fan not working in waiting room"}).json()
    wrong = client.post(f"{base}/observations", headers=officer, data={"text": "Garbage near ticket counter"},
                        files={"photo": ("p.jpg", b"fake-image-bytes", "image/jpeg")}).json()
    assert client.post(f"{base}/generate-note", headers=officer).json()["note_text"]

    # removing a point deletes it and clears the note, because the note no longer matches
    assert client.delete(f"{base}/observations/{wrong['id']}", headers=officer).status_code == 204
    after = client.get(base, headers=officer).json()
    assert [o["id"] for o in after["observations"]] == [keep["id"]]
    assert after["note_text"] == ""
    assert client.get(f"/inspections/photos/{wrong['photo_key']}", headers=officer).status_code == 404

    # staff cannot remove points, and nothing can be removed after approval
    assert client.delete(f"{base}/observations/{keep['id']}", headers=login("staff_elec")).status_code == 403
    client.post(f"{base}/generate-note", headers=officer)
    assert client.post(f"{base}/approve", headers=officer).json()["status"] == "approved"
    assert client.delete(f"{base}/observations/{keep['id']}", headers=officer).status_code == 400


def test_photos_can_be_kept_in_the_database(monkeypatch):
    """The online copy (Vercel) has no disk, so photos go into the database: STORAGE_BACKEND=db."""
    from app.config import settings

    monkeypatch.setattr(settings, "storage_backend", "db")
    assert client.get("/health").json()["photos"] == "db"

    officer = login("officer")
    loc = client.get("/locations", headers=officer).json()[0]
    insp = client.post("/inspections", headers=officer,
                       json={"location_id": loc["id"], "inspection_type": "station", "checklist": {}}).json()
    base = f"/inspections/{insp['id']}"
    obs = client.post(f"{base}/observations", headers=officer, data={"text": "Tube light fused on platform 2"},
                      files={"photo": ("p.jpg", b"photo-kept-in-database", "image/jpeg")}).json()

    photo = client.get(f"/inspections/photos/{obs['photo_key']}", headers=officer)
    assert photo.status_code == 200 and photo.content == b"photo-kept-in-database"

    assert client.delete(f"{base}/observations/{obs['id']}", headers=officer).status_code == 204
    assert client.get(f"/inspections/photos/{obs['photo_key']}", headers=officer).status_code == 404


def test_note_can_be_downloaded_as_pdf():
    officer = login("officer")
    loc = client.get("/locations", headers=officer).json()[0]
    insp = client.post("/inspections", headers=officer,
                       json={"location_id": loc["id"], "inspection_type": "station",
                             "checklist": {"lighting": False, "fans": True}}).json()
    base = f"/inspections/{insp['id']}"
    client.post(f"{base}/observations", headers=officer, data={"text": "Tube light fused on platform 2 – urgent"},
                files={"photo": ("p.jpg", b"not-a-real-picture", "image/jpeg")})

    # a draft can be exported too, and a photo that cannot be read is simply left out
    draft = client.get(f"{base}/note.pdf", headers=officer)
    assert draft.status_code == 200 and draft.headers["content-type"] == "application/pdf"
    assert draft.content.startswith(b"%PDF-")

    client.post(f"{base}/generate-note", headers=officer)
    client.post(f"{base}/approve", headers=officer)
    issued = client.get(f"{base}/note.pdf", headers=login("senior"))
    assert issued.status_code == 200 and issued.content.startswith(b"%PDF-")
    assert f"inspection_note_{insp['id']}.pdf" in issued.headers["content-disposition"]
    assert client.get(f"{base}/note.pdf").status_code == 401


def test_overdue_points_are_escalated_once_per_step(monkeypatch):
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import ComplianceTask, User
    from app.services import notify

    officer, senior = login("officer"), login("senior")
    client.post("/tasks/run-escalation", headers=senior)   # clear anything left by the tests above
    loc = client.get("/locations", headers=officer).json()[0]
    insp = client.post("/inspections", headers=officer,
                       json={"location_id": loc["id"], "inspection_type": "station", "checklist": {}}).json()
    base = f"/inspections/{insp['id']}"
    client.post(f"{base}/observations", headers=officer, data={"text": "Exposed wiring near water cooler switch board"})
    client.post(f"{base}/generate-note", headers=officer)
    client.post(f"{base}/approve", headers=officer)
    task_id = [t for t in client.get("/tasks", headers=officer).json() if t["status"] == "open"][-1]["id"]

    sent = []
    monkeypatch.setattr(notify, "send_email", lambda to, subject, body: sent.append((to, subject, body)) or True)

    def make_overdue(days: float):
        with SessionLocal() as db:
            db.get(ComplianceTask, task_id).deadline = datetime.utcnow() - timedelta(days=days)
            db.scalar(select(User).where(User.username == "staff_elec")).email = "elec@example.com"
            db.commit()

    # not overdue yet: nothing happens
    assert client.post("/tasks/run-escalation", headers=senior).json()["escalated"] == 0

    # one hour past the deadline: step 1, one email to the department, and only once
    make_overdue(1 / 24)
    first = client.post("/tasks/run-escalation", headers=senior).json()
    assert first["escalated"] == 1 and first["points"] == [{"id": task_id, "level": 1, "department": "Electrical"}]
    assert len(sent) == 1 and sent[0][0] == "elec@example.com" and f"#{task_id}" in sent[0][2]
    assert client.post("/tasks/run-escalation", headers=senior).json()["escalated"] == 0
    assert len(sent) == 1

    # four days overdue: step 2
    make_overdue(4)
    assert client.post("/tasks/run-escalation", headers=senior).json()["points"][0]["level"] == 2
    assert client.get(f"/tasks/{task_id}", headers=senior).json()["escalation_level"] == 2

    # staff cannot start the check
    assert client.post("/tasks/run-escalation", headers=login("staff_elec")).status_code == 403


def test_admin_manages_users_departments_and_locations():
    admin = login("admin")

    # a new department, and a staff user in it who can sign in
    dept = client.post("/admin/departments", headers=admin, json={"code": "optg", "name": "Operating"})
    assert dept.status_code == 201 and dept.json()["code"] == "OPTG"
    dept_id = dept.json()["id"]
    assert client.post("/admin/departments", headers=admin, json={"code": "OPTG", "name": "Again"}).status_code == 400

    new_user = {"username": "Staff_Optg", "password": "secret1", "full_name": "Operating Supervisor",
                "designation": "Supervisor", "email": "optg@example.com", "role": "staff"}
    assert client.post("/admin/users", headers=admin, json=new_user).status_code == 400      # staff need a department
    made = client.post("/admin/users", headers=admin, json={**new_user, "department_id": dept_id})
    assert made.status_code == 201 and made.json()["username"] == "staff_optg" and made.json()["is_active"] is True
    user_id = made.json()["id"]
    assert client.post("/admin/users", headers=admin, json={**new_user, "department_id": dept_id}).status_code == 400
    assert client.post("/admin/users", headers=admin,
                       json={**new_user, "username": "x2y", "password": "123", "department_id": dept_id}).status_code == 400

    signed_in = client.post("/auth/login", json={"username": "staff_optg", "password": "secret1"})
    assert signed_in.status_code == 200
    token = {"Authorization": f"Bearer {signed_in.json()['access_token']}"}
    assert client.get("/tasks", headers=token).status_code == 200

    # a department with staff cannot be deleted; it can be renamed
    assert client.delete(f"/admin/departments/{dept_id}", headers=admin).status_code == 400
    assert client.put(f"/admin/departments/{dept_id}", headers=admin, json={"name": "Operating Dept"}).json()["name"] == "Operating Dept"

    # switching the account off stops the login and the token that was already issued
    edit = {"full_name": "Operating Supervisor", "designation": "Supervisor", "email": "", "role": "staff",
            "department_id": dept_id, "is_active": False}
    off = client.put(f"/admin/users/{user_id}", headers=admin, json=edit)
    assert off.status_code == 200 and off.json()["is_active"] is False and off.json()["email"] is None
    assert client.post("/auth/login", json={"username": "staff_optg", "password": "secret1"}).status_code == 401
    assert client.get("/tasks", headers=token).status_code == 401

    # switched on again with a new password
    client.put(f"/admin/users/{user_id}", headers=admin, json={**edit, "is_active": True, "password": "newpass9"})
    assert client.post("/auth/login", json={"username": "staff_optg", "password": "newpass9"}).status_code == 200

    # the admin cannot lock themselves out
    me = next(u for u in client.get("/admin/users", headers=admin).json() if u["username"] == "admin")
    own = {"full_name": me["full_name"], "designation": "", "role": "admin", "is_active": False}
    assert client.put(f"/admin/users/{me['id']}", headers=admin, json=own).status_code == 400
    assert client.put(f"/admin/users/{me['id']}", headers=admin, json={**own, "is_active": True, "role": "senior"}).status_code == 400

    # locations: add, change, delete; one with inspections cannot be deleted
    halt = {"name": "Zz Test Halt", "kind": "station", "division": "Jaipur", "latitude": 26.8, "longitude": 75.8}
    assert client.post("/admin/locations", headers=admin, json={**halt, "latitude": 126.8}).status_code == 400
    loc = client.post("/admin/locations", headers=admin, json=halt).json()
    changed = client.put(f"/admin/locations/{loc['id']}", headers=admin, json={**halt, "kind": "depot"})
    assert changed.json()["kind"] == "depot"
    assert client.delete(f"/admin/locations/{loc['id']}", headers=admin).status_code == 204
    used = client.get("/inspections", headers=admin).json()[0]["location"]["id"]
    assert client.delete(f"/admin/locations/{used}", headers=admin).status_code == 400

    # only the admin can use these screens
    for other in ("senior", "officer", "staff_elec"):
        assert client.get("/admin/users", headers=login(other)).status_code == 403
    assert client.post("/admin/departments", headers=login("senior"), json={"code": "NEW", "name": "New"}).status_code == 403


def test_roles_are_enforced():
    staff = login("staff_engg")
    assert client.post("/inspections", headers=staff, json={"location_id": 1, "inspection_type": "station"}).status_code == 403
    assert client.get("/dashboard/summary", headers=staff).status_code == 403
    assert client.get("/tasks").status_code == 401
