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

    # --- Boston 311 ingestion (M2) ---
    # CKAN datastore endpoint + the resource id for recent 311 data.
    boston_311_base_url: str = Field(
        default="https://data.boston.gov/api/3/action/datastore_search"
    )
    boston_311_resource_id: str = Field(
        default="9d7c2214-4709-478a-a2e8-fb2020a5bb94"  # 311 Service Requests - 2025
    )
    # Default cap for how many recent records to ingest.
    boston_311_max_records: int = Field(default=5000)
    # Page size per API request (CKAN allows up to ~32000; keep modest).
    boston_311_page_size: int = Field(default=1000)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def admin_endpoints_enabled(self) -> bool:
        """Whether unauthenticated staff/admin mutations are permitted.

        Hard rule: in production, unauthenticated admin access is ALWAYS
        disabled — the ALLOW_UNAUTHENTICATED_ADMIN override cannot turn it on.
        This prevents a misconfigured deployment from exposing staff operations
        before real authentication exists.

        Outside production, the override (if set) wins; otherwise access is
        enabled only in development. Any non-development, non-production
        environment (e.g. staging) defaults to disabled.
        """
        if self.is_production:
            return False
        if self.allow_unauthenticated_admin is not None:
            return self.allow_unauthenticated_admin
        return self.is_development


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
