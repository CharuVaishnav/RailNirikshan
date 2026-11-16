from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, dashboard, inspections, tasks


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creating tables at startup is fine for development.
    # Switch to Alembic migrations once the schema settles.
    Base.metadata.create_all(bind=engine)
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
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(inspections.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)
