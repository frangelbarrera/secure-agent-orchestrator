import os
from enum import StrEnum

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known-insecure default values that must never be used outside LOCAL env.
_INSECURE_SECRET_KEY_DEFAULT = "secret-key"
_INSECURE_ADMIN_PASSWORD_DEFAULT = "!Ch4ng3Th1sP4ssW0rd!"


class AppSettings(BaseSettings):
    APP_NAME: str = "Secure Agent Orchestrator"
    APP_DESCRIPTION: str | None = None
    APP_VERSION: str | None = None
    LICENSE_NAME: str | None = None
    CONTACT_NAME: str | None = None
    CONTACT_EMAIL: str | None = None


class CryptSettings(BaseSettings):
    # No default. LOCAL env may set SECRET_KEY explicitly; any non-LOCAL env MUST set it
    # to a strong value. Validators below enforce this at startup.
    SECRET_KEY: SecretStr = SecretStr(_INSECURE_SECRET_KEY_DEFAULT)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


class DatabaseSettings(BaseSettings):
    pass


class SQLiteSettings(DatabaseSettings):
    SQLITE_URI: str = "./sql_app.db"
    SQLITE_SYNC_PREFIX: str = "sqlite:///"
    SQLITE_ASYNC_PREFIX: str = "sqlite+aiosqlite:///"


class FirstUserSettings(BaseSettings):
    ADMIN_NAME: str = "admin"
    ADMIN_EMAIL: str = "admin@admin.com"
    ADMIN_USERNAME: str = "admin"
    # No default. LOCAL env may keep the placeholder; any non-LOCAL env MUST override it.
    ADMIN_PASSWORD: str = _INSECURE_ADMIN_PASSWORD_DEFAULT


class TestSettings(BaseSettings): ...


class ClientSideCacheSettings(BaseSettings):
    CLIENT_CACHE_MAX_AGE: int = 60


class DefaultRateLimitSettings(BaseSettings):
    DEFAULT_RATE_LIMIT_LIMIT: int = 10
    DEFAULT_RATE_LIMIT_PERIOD: int = 3600


class CRUDAdminSettings(BaseSettings):
    # Default-off in any non-LOCAL environment. Even in LOCAL it is opt-in for safety.
    CRUD_ADMIN_ENABLED: bool = False
    CRUD_ADMIN_MOUNT_PATH: str = "/admin"

    CRUD_ADMIN_ALLOWED_IPS_LIST: list[str] | None = ["127.0.0.1", "::1"]
    CRUD_ADMIN_ALLOWED_NETWORKS_LIST: list[str] | None = None
    CRUD_ADMIN_MAX_SESSIONS: int = 10
    CRUD_ADMIN_SESSION_TIMEOUT: int = 1440
    SESSION_SECURE_COOKIES: bool = True

    CRUD_ADMIN_TRACK_EVENTS: bool = True
    CRUD_ADMIN_TRACK_SESSIONS: bool = True

    CRUD_ADMIN_REDIS_ENABLED: bool = False
    CRUD_ADMIN_REDIS_HOST: str = "localhost"
    CRUD_ADMIN_REDIS_PORT: int = 6379
    CRUD_ADMIN_REDIS_DB: int = 0
    CRUD_ADMIN_REDIS_PASSWORD: str | None = None
    CRUD_ADMIN_REDIS_SSL: bool = False


class EnvironmentOption(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentSettings(BaseSettings):
    ENVIRONMENT: EnvironmentOption = EnvironmentOption.LOCAL


class CORSSettings(BaseSettings):
    # Restrictive defaults. `*` is forbidden in non-LOCAL environments (see validator below).
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_HEADERS: list[str] = ["Authorization", "Content-Type", "Accept"]


class Settings(
    AppSettings,
    SQLiteSettings,
    CryptSettings,
    FirstUserSettings,
    TestSettings,
    ClientSideCacheSettings,
    DefaultRateLimitSettings,
    CRUDAdminSettings,
    EnvironmentSettings,
    CORSSettings,
):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def _validate_secret_key(cls, v: SecretStr) -> SecretStr:
        # Always reject the known-insecure default at the field level so even LOCAL
        # developers get a loud warning if they forget to override it.
        if v.get_secret_value() == _INSECURE_SECRET_KEY_DEFAULT:
            raise ValueError(
                "SECRET_KEY is set to the known-insecure placeholder 'secret-key'. "
                'Generate a strong key with: python -c "import secrets; print(secrets.token_urlsafe(32))" '
                "and set it as the SECRET_KEY env var."
            )
        if len(v.get_secret_value()) < 32:
            raise ValueError(
                f"SECRET_KEY must be at least 32 characters long (got {len(v.get_secret_value())}). "
                'Use: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return v

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def _validate_admin_password(cls, v: str) -> str:
        if v == _INSECURE_ADMIN_PASSWORD_DEFAULT:
            raise ValueError(
                "ADMIN_PASSWORD is set to the known-insecure placeholder. "
                "Set a strong, unique password via the ADMIN_PASSWORD env var."
            )
        if len(v) < 12:
            raise ValueError(f"ADMIN_PASSWORD must be at least 12 characters long (got {len(v)}).")
        return v

    @model_validator(mode="after")
    def _validate_cors_for_environment(self) -> "Settings":
        if self.ENVIRONMENT != EnvironmentOption.LOCAL:
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CORS_ORIGINS cannot contain '*' in non-LOCAL environments "
                    f"(current ENVIRONMENT={self.ENVIRONMENT.value}). "
                    "List explicit origins, e.g. ['https://app.example.com']."
                )
            if "*" in self.CORS_METHODS:
                raise ValueError(
                    "CORS_METHODS cannot contain '*' in non-LOCAL environments. List explicit HTTP methods."
                )
            if "*" in self.CORS_HEADERS:
                raise ValueError(
                    "CORS_HEADERS cannot contain '*' in non-LOCAL environments. List explicit header names."
                )
        return self


settings = Settings()
