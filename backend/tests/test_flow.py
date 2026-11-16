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


def test_roles_are_enforced():
    staff = login("staff_engg")
    assert client.post("/inspections", headers=staff, json={"location_id": 1, "inspection_type": "station"}).status_code == 403
    assert client.get("/dashboard/summary", headers=staff).status_code == 403
    assert client.get("/tasks").status_code == 401
