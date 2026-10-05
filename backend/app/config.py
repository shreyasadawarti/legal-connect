from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

# Load both the backend-local .env (if any) and the repo-root .env.
_ROOTS = [
    Path(__file__).resolve().parents[1],  # backend/
    Path(__file__).resolve().parents[2],  # repo root (legal-connect/)
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(Path(r) / ".env") for r in _ROOTS],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_env: str = "development"
    app_name: str = "Legal Connect API"
    secret_key: str = "change-this-secret"
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # --- MySQL (application database) ---
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "legal_connect"
    mysql_charset: str = "utf8mb4"
    # Creates any missing tables on startup. Never drops or alters existing
    # tables; schema changes are handled by Alembic (`alembic upgrade head`).
    auto_create_tables: bool = True

    # --- MongoDB (legacy; only used by scripts/migrate_mongodb_to_mysql.py) ---
    mongodb_uri: str = ""
    mongodb_database: str = "legal_connect"

    # --- Cloudinary ---
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder: str = "legal-connect"

    # --- OpenAI-compatible AI ---
    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = ""
    openai_base_url: str = ""

    # --- Email (Resend or SMTP) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    resend_api_key: str = ""

    # --- URLs / CORS ---
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"

    # --- Maps ---
    google_maps_api_key: str = ""

    # --- WebRTC ---
    webrtc_stun_server: str = "stun:stun.l.google.com:19302"
    webrtc_turn_server: str = ""
    webrtc_turn_username: str = ""
    webrtc_turn_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def mysql_dsn(self) -> str:
        """Async SQLAlchemy URL for the local MySQL application database."""
        return (
            f"mysql+asyncmy://{self.mysql_user}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )

    @property
    def mysql_server_dsn(self) -> str:
        """Server-level URL (no database selected) used to CREATE DATABASE."""
        return (
            f"mysql+asyncmy://{self.mysql_user}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/?charset={self.mysql_charset}"
        )

    @property
    def is_mysql_configured(self) -> bool:
        return bool(self.mysql_host and self.mysql_user and self.mysql_database)

    @property
    def is_mongodb_configured(self) -> bool:
        """Legacy. Only scripts/migrate_mongodb_to_mysql.py needs this now."""
        return bool(self.mongodb_uri)

    @property
    def is_cloudinary_configured(self) -> bool:
        return bool(self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret)

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def is_email_configured(self) -> bool:
        return bool(self.smtp_host or self.resend_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
