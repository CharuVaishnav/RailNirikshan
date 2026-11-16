from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _database_url(url: str) -> str:
    """A hosted PostgreSQL (for example Neon on Vercel) gives an address that starts with
    postgres:// or postgresql://. SQLAlchemy also needs the driver name, so add it here."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


database_url = _database_url(settings.database_url)

if database_url.startswith("sqlite"):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
elif database_url.startswith("postgresql+psycopg"):
    # pool_pre_ping / pool_recycle: a hosted database closes idle connections, so check each one before use.
    # prepare_threshold=None: hosted databases sit behind a connection pooler that cannot keep prepared statements.
    engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300,
                           connect_args={"prepare_threshold": None})
else:
    engine = create_engine(database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
