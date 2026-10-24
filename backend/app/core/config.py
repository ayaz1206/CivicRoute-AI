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

    # --- Auth (M5) ---
    # Secret for signing JWTs. MUST be overridden in production via env.
    jwt_secret: str = Field(default="dev-insecure-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=720)
    # Optional bootstrap admin created by `python -m app.seed` in development.
    bootstrap_admin_email: str | None = Field(default=None)
    bootstrap_admin_password: str | None = Field(default=None)

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

    # --- LLM provider (M3) ---
    # Provider adapter to use: "fake" (deterministic, no network/keys),
    # "openai", or "anthropic". Defaults to "fake" so the system runs offline.
    llm_provider: str = Field(default="fake")
    llm_model: str | None = Field(default=None)
    llm_api_key: str | None = Field(default=None)
    # Confidence thresholds for auto vs. human review (M3).
    agent_review_threshold: float = Field(default=0.7)

    # --- Embeddings / duplicate detection (M4) ---
    embedding_provider: str = Field(default="fake")
    embedding_model: str | None = Field(default=None)
    # Vector dimension. Must match the DB column (see migration). 384 for fake.
    embedding_dim: int = Field(default=384)
    # Cosine-similarity floor for a complaint to be a duplicate candidate (0..1).
    # Calibrated for OpenAI text-embedding-3-small: measured positives 0.85-0.92
    # vs. unrelated 0.63-0.71, so 0.78 sits in the clean gap. Lower this only for
    # embedders whose unrelated-pair similarities are much closer to zero.
    duplicate_similarity_threshold: float = Field(default=0.78)
    # Retrieval floor: raw cosine below this is never considered (keeps KNN
    # noise out). Candidates between this floor and the decision threshold are
    # still scored, so location/category evidence can lift a borderline true
    # duplicate over the line. The decision uses the COMBINED score, not raw
    # cosine, against duplicate_similarity_threshold.
    duplicate_retrieval_floor: float = Field(default=0.6)
    # Max distance (meters) for coordinates to count as a location MATCH.
    duplicate_location_radius_m: float = Field(default=200.0)
    # Distance (meters) beyond which two coordinates are a clear location
    # MISMATCH (distinct places). Between radius and this is "near"/ambiguous.
    duplicate_location_mismatch_m: float = Field(default=1000.0)
    # Text-overlap (Jaccard) at/above this is a location MATCH; at/below the
    # low bound is a MISMATCH; in between is ambiguous (treated as unknown).
    duplicate_location_text_match: float = Field(default=0.5)
    duplicate_location_text_mismatch: float = Field(default=0.1)

    # --- LLM safeguards & rate limiting (M5) ---
    llm_timeout_seconds: float = Field(default=20.0)
    llm_max_output_tokens: int = Field(default=512)
    llm_max_retries: int = Field(default=2)
    # Simple in-process rate limit for expensive endpoints (per client/minute).
    rate_limit_per_minute: int = Field(default=30)
    rate_limit_enabled: bool = Field(default=True)

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
