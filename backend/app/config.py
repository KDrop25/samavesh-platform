import base64
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Dev/test defaults only. get_settings() refuses to start in prod with either of them.
DEV_SECRET = "dev-only-secret-change-me-before-any-deploy"
DEV_DATA_KEYS = "1:" + base64.b64encode(bytes(32)).decode()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "dev"  # dev | prod
    database_url: str = "sqlite:///./samavesh.db"
    secret_key: str = DEV_SECRET  # signs JWTs and HMACs verification codes
    # "<id>:<base64 32-byte key>,..." - highest id encrypts, all ids decrypt (rotation).
    data_encryption_keys: str = DEV_DATA_KEYS
    frontend_origin: str = "http://localhost:3210"
    smtp_host: str = ""  # empty = dev outbox (console + dev_emails table)
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "Samavesh <no-reply@samavesh.local>"
    jobs_secret: str = ""  # guards POST /internal/jobs/run

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def sqlalchemy_url(self) -> str:
        # Neon/Render hand out postgres:// or postgresql:// URLs; we use the psycopg 3 driver.
        for prefix in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefix):
                return "postgresql+psycopg://" + self.database_url[len(prefix):]
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    weak = s.secret_key == DEV_SECRET or len(s.secret_key) < 32 or s.data_encryption_keys == DEV_DATA_KEYS
    if s.is_prod and weak:
        raise RuntimeError("Set SECRET_KEY (32+ chars) and DATA_ENCRYPTION_KEYS in production")
    return s
