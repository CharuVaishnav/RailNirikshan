"""Photo storage. 'local' saves to a folder on the server disk (free, the default).
'minio' is optional S3-compatible storage: only if you need it, run `pip install minio`."""
import io
import uuid
from pathlib import Path

from ..config import settings


def _new_key(filename: str) -> str:
    ext = Path(filename or "photo.jpg").suffix.lower() or ".jpg"
    return f"{uuid.uuid4().hex}{ext}"


def save_photo(data: bytes, filename: str) -> str:
    """Store the photo and return its key."""
    key = _new_key(filename)
    if settings.storage_backend == "minio":
        from minio import Minio

        client = Minio(settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, secure=False)
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        client.put_object(settings.minio_bucket, key, io.BytesIO(data), len(data))
    else:
        folder = Path(settings.local_upload_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / key).write_bytes(data)
    return key


def delete_photo(key: str) -> None:
    """Remove a stored photo. A missing file is not an error."""
    if settings.storage_backend == "minio":
        from minio import Minio

        client = Minio(settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, secure=False)
        client.remove_object(settings.minio_bucket, key)
    else:
        (Path(settings.local_upload_dir) / key).unlink(missing_ok=True)


def load_photo(key: str) -> bytes:
    if settings.storage_backend == "minio":
        from minio import Minio

        client = Minio(settings.minio_endpoint, settings.minio_access_key, settings.minio_secret_key, secure=False)
        resp = client.get_object(settings.minio_bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
    return (Path(settings.local_upload_dir) / key).read_bytes()
