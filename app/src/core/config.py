import os
from dataclasses import dataclass


DEFAULT_DATABASE_URL = (
    "postgresql://menuscan:localdev@localhost:54320/menuscan"
)
DEFAULT_CORS_ORIGINS = ("http://localhost:5173",)


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    database_url: str
    app_env: str
    log_level: str
    api_v1_prefix: str
    cors_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "Settings":
        raw_origins = os.getenv("CORS_ORIGINS")
        cors_origins = (
            tuple(
                origin.strip()
                for origin in raw_origins.split(",")
                if origin.strip()
            )
            if raw_origins is not None
            else DEFAULT_CORS_ORIGINS
        )
        if "*" in cors_origins:
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' when credentials are enabled"
            )

        api_v1_prefix = os.getenv("API_V1_PREFIX", "/api/v1").strip()
        if not api_v1_prefix.startswith("/"):
            api_v1_prefix = f"/{api_v1_prefix}"
        api_v1_prefix = api_v1_prefix.rstrip("/") or "/"

        return cls(
            database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            api_v1_prefix=api_v1_prefix,
            cors_origins=cors_origins,
        )


settings = Settings.from_environment()
