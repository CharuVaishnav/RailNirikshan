"""Photo storage. STORAGE_BACKEND chooses where photos are kept:

'local'  a folder on the server disk (free, the default on the laptop)
'db'     inside the database (used by the online copy on Vercel, which has no permanent disk)
'minio'  optional S3-compatible storage: only if you need it, run `pip install minio`

For 'db', pass the request's database session as `db` so the photo is saved or removed
together with the record it belongs to. The other two backends ignore `db`.
"""
import io
import uuid
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models import StoredPhoto


def _new_key(filename: str) -> str:
    ext = Path(filename or "photo.jpg").suffix.lower() or ".jpg"
    return f"{uuid.uuid4().hex}{ext}"


def _minio():
    from minio import Minio

    return Minio(settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, secure=False)


def _with_session(db: Session | None, work) -> None:
    """Run `work(session)`. Without a session from the caller, open one and commit it here."""
    if db is not None:
        work(db)
        return
    own = SessionLocal()
    try:
        work(own)
        own.commit()
    finally:
        own.close()


def save_photo(data: bytes, filename: str, db: Session | None = None, key: str | None = None) -> str:
    """Store the photo and return its key. `key` is only given by the demo data, to get fixed names."""
    key = key or _new_key(filename)
    if settings.storage_backend == "db":
        _with_session(db, lambda s: s.merge(StoredPhoto(key=key, data=data)))
    elif settings.storage_backend == "minio":
        client = _minio()
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        client.put_object(settings.minio_bucket, key, io.BytesIO(data), len(data))
    else:
        folder = Path(settings.local_upload_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / key).write_bytes(data)
    return key


def delete_photo(key: str, db: Session | None = None) -> None:
    """Remove a stored photo. A missing photo is not an error."""
    if settings.storage_backend == "db":
        _with_session(db, lambda s: s.execute(delete(StoredPhoto).where(StoredPhoto.key == key)))
    elif settings.storage_backend == "minio":
        _minio().remove_object(settings.minio_bucket, key)
    else:
        (Path(settings.local_upload_dir) / key).unlink(missing_ok=True)


def delete_demo_photos(db: Session | None = None) -> None:
    """Remove the placeholder photos made by app/demo_seed.py (their keys start with demo_)."""
    if settings.storage_backend == "db":
        _with_session(db, lambda s: s.execute(delete(StoredPhoto).where(StoredPhoto.key.like("demo\\_%", escape="\\"))))
    elif settings.storage_backend == "local":
        for f in Path(settings.local_upload_dir).glob("demo_*.jpg"):
            f.unlink()


def load_photo(key: str) -> bytes:
    """Return the photo, or raise FileNotFoundError."""
    if settings.storage_backend == "db":
        with SessionLocal() as s:
            photo = s.get(StoredPhoto, key)
            if photo is None:
                raise FileNotFoundError(key)
            return photo.data
    if settings.storage_backend == "minio":
        resp = _minio().get_object(settings.minio_bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
    return (Path(settings.local_upload_dir) / key).read_bytes()
