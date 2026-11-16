from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


# Extra words some hosts put at the end of the address for other tools. The PostgreSQL driver
# refuses an address that contains them, so they are removed.
_NOT_FOR_THE_DRIVER = {"supa", "pgbouncer", "connection_limit", "pool_timeout"}


def _database_url(url: str) -> str:
    """A hosted PostgreSQL (Supabase or Neon on Vercel) gives an address that starts with
    postgres:// or postgresql://. SQLAlchemy also needs the driver name, so add it here."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    if url.startswith("postgresql+psycopg://") and "?" in url:
        address, options = url.split("?", 1)
        keep = [o for o in options.split("&") if o and o.split("=")[0] not in _NOT_FOR_THE_DRIVER]
        url = address + ("?" + "&".join(keep) if keep else "")
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
