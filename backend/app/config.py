from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings. Values come from environment variables or the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: SQLite by default so you can start without Docker.
    # With Docker running, use: postgresql+psycopg://rail:rail@localhost:5432/railnirikshan
    database_url: str = "sqlite:///./railnirikshan.db"

    # Security
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_minutes: int = 60 * 12

    # Photo storage: "local" (uploads folder on the server disk, free), "db" (inside the database,
    # used by the online copy on Vercel) or "minio" (optional)
    storage_backend: str = "local"
    local_upload_dir: str = "uploads"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "railnirikshan"

    # AI services (all optional; the app works without them)
    ollama_url: str = ""            # e.g. http://localhost:11434
    ollama_model: str = "qwen2.5:3b"   # small model that runs on a normal CPU
    yolo_model_path: str = ""       # e.g. ../ml/defect_detection/runs/detect/train/weights/best.pt

    # Email alerts (free, e.g. Gmail with an app password). Leave smtp_user empty to switch off.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Compliance rules
    default_deadline_days: int = 7


settings = Settings()
