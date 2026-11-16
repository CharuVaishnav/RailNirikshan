"""Entry point for the online copy on Vercel. It is not used when you run the project on the laptop.

Vercel serves the built web app (dashboard/dist) as plain files and sends every request that
starts with /api/ to this file (see vercel.json). This file hands those requests to the same
FastAPI backend that runs on the laptop, so there is only one copy of the backend code.

Three things are different online, and are set here before the backend is loaded:

1. Database. Vercel has no permanent disk, so the SQLite file cannot be used. When a PostgreSQL
   database (Supabase or Neon) is connected to the Vercel project (Storage tab), Vercel sets its
   address as POSTGRES_URL or DATABASE_URL and the backend uses it. Without one, a temporary SQLite file is used: the site opens, but data can
   disappear at any time, so connect a database.
2. Photos. They are kept inside the database instead of the uploads/ folder.
3. Login secret. If JWT_SECRET is not set in Vercel, one is made from the database address, which
   is private to the Vercel project. The value in the public repository is never used online.
"""
import hashlib
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Neon names the database address DATABASE_URL; Supabase names it POSTGRES_URL.
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (os.environ.get("POSTGRES_URL")
                                  or f"sqlite:///{Path(tempfile.gettempdir()) / 'railnirikshan.db'}")
os.environ.setdefault("STORAGE_BACKEND", "db")
if not os.environ.get("JWT_SECRET"):
    os.environ["JWT_SECRET"] = hashlib.sha256(("jwt:" + os.environ["DATABASE_URL"]).encode()).hexdigest()

from fastapi import FastAPI  # noqa: E402

from app.demo_seed import demo_seed  # noqa: E402
from app.main import app as backend  # noqa: E402

# Create the tables and, if the database is empty, load the demo users, stations and inspections.
# When data is already there this only runs two quick checks.
try:
    demo_seed()
except Exception as exc:  # the site should still start, so the problem shows in the Vercel logs
    print(f"Could not prepare the database: {exc!r}")

# The browser calls /api/..., and the backend's own addresses have no /api in front.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", backend)
