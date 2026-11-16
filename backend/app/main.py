from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, ensure_schema
from .routers import admin, auth, dashboard, inspections, tasks


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creating tables at startup is fine for development.
    # Switch to Alembic migrations once the schema settles.
    ensure_schema()
    yield


app = FastAPI(
    title="RailNirikshan API",
    description="AI-powered smart inspection and compliance system for Indian Railways",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # the React dashboard in development
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    # "database" and "photos" show where data is kept: useful to check the online copy is set up properly.
    return {"status": "ok", "database": engine.dialect.name, "photos": settings.storage_backend}


app.include_router(auth.router)
app.include_router(inspections.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
