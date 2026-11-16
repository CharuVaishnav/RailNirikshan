"""Fill the database with demo departments, users and locations.

Run from the backend folder:  python -m app.seed
All demo users have the password: demo123
"""
from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import Department, Location, User
from .security import hash_password

DEPARTMENTS = [
    ("ENGG", "Engineering"),
    ("ELEC", "Electrical"),
    ("COMM", "Commercial"),
    ("MECH", "Mechanical"),
    ("SNT", "Signal & Telecommunication"),
    ("MED", "Medical"),
    ("SEC", "Security"),
]

# Demo locations on NWR (approximate coordinates; replace with official data from the railway).
LOCATIONS = [
    ("Jaipur Junction", "station", "Jaipur", 26.9196, 75.7878),
    ("Ajmer Junction", "station", "Ajmer", 26.4565, 74.6378),
    ("Jodhpur Junction", "station", "Jodhpur", 26.2847, 73.0213),
    ("Bikaner Junction", "station", "Bikaner", 28.0129, 73.3105),
    ("LC Gate 101 (demo)", "lc_gate", "Jaipur", 26.9001, 75.7500),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Department)) is not None:
            print("Database already has data; nothing to do.")
            return
        depts = {code: Department(code=code, name=name) for code, name in DEPARTMENTS}
        db.add_all(depts.values())
        db.flush()

        pw = hash_password("demo123")
        users = [
            User(username="admin", full_name="System Admin", role="admin", password_hash=pw),
            User(username="officer", full_name="Demo Inspecting Officer", designation="Inspecting Officer",
                 role="officer", password_hash=pw),
            User(username="senior", full_name="Demo Senior Officer", designation="Senior Officer",
                 role="senior", password_hash=pw),
        ]
        for code, d in depts.items():
            users.append(User(username=f"staff_{code.lower()}", full_name=f"Demo {d.name} Staff",
                              designation="Supervisor", role="staff", department_id=d.id, password_hash=pw))
        db.add_all(users)
        db.add_all(Location(name=n, kind=k, division=dv, latitude=la, longitude=lo) for n, k, dv, la, lo in LOCATIONS)
        db.commit()
        print("Seeded demo data. Users: admin, officer, senior, staff_engg, staff_elec, staff_comm, ... "
              "(password: demo123)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
