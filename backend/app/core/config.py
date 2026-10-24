"""Application configuration via pydantic-settings.

Settings are loaded from environment variables (and a local .env file in
development). See .env.example for the full list.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="development")
    api_prefix: str = Field(default="/api")

    # Gate for unauthenticated staff/admin mutation endpoints. Until real auth
    # lands (later milestone), these endpoints are only enabled in development.
    # Leave unset to derive from APP_ENV; set explicitly to override.
    allow_unauthenticated_admin: bool | None = Field(default=None)

    # Async SQLAlchemy URL, e.g.
    # postgresql+asyncpg://civicroute:civicroute@localhost:5432/civicroute
    database_url: str = Field(
        default="postgresql+asyncpg://civicroute:civicroute@localhost:5433/civicroute"
    )

    # Allowed CORS origins for the frontend, as a comma-separated string.
    # Exposed as a parsed list via the `cors_origins` property. Kept as a plain
    # str so pydantic-settings does not attempt to JSON-decode the env value.
    cors_origins_raw: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def admin_endpoints_enabled(self) -> bool:
        """Whether unauthenticated staff/admin mutations are permitted.

        Defaults to development-only. Can be force-enabled/disabled via the
        ALLOW_UNAUTHENTICATED_ADMIN env var (not recommended for production).
        """
        if self.allow_unauthenticated_admin is not None:
            return self.allow_unauthenticated_admin
        return self.is_development


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
