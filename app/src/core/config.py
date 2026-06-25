import os
from dataclasses import dataclass


DEFAULT_DATABASE_URL = (
    "postgresql://menuscan:localdev@localhost:54320/menuscan"
)
DEFAULT_MAGIC_LINK_BASE_URL = "http://localhost:5173"
DEFAULT_CORS_ORIGINS = ("http://localhost:5173",)

DEFAULT_EMAIL_PROVIDER = "console"
DEFAULT_EMAIL_FROM_ADDRESS = ""
DEFAULT_EMAIL_API_BASE_URL = "https://api.resend.com"
DEFAULT_EMAIL_TIMEOUT_SECONDS = "10"

SUPPORTED_EMAIL_PROVIDERS = ("console", "resend")


@dataclass(frozen=True, slots=True)
class EmailConfig:
    """Email provider configuration.

    Provider selection is env-driven (``EMAIL_PROVIDER``). ``console`` is the
    dev/test no-op; ``resend`` calls the Resend transactional API. Secrets
    (``api_key``) come from env and are never logged.
    """

    provider: str
    from_address: str
    api_key: str | None
    api_base_url: str
    timeout_seconds: float

    def is_configured(self) -> bool:
        """True when the active provider has everything it needs to send."""
        if self.provider == "console":
            return True
        return bool(self.from_address) and bool(self.api_key)


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    database_url: str
    magic_link_base_url: str
    app_env: str
    log_level: str
    api_v1_prefix: str
    cors_origins: tuple[str, ...]
    email: EmailConfig
    secret_key: str = "menuscan-default-insecure-secret-key-change-this-in-production"

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

        email = _load_email_config()
        if email.provider not in SUPPORTED_EMAIL_PROVIDERS:
            raise ValueError(
                f"EMAIL_PROVIDER={email.provider!r} is not supported; "
                f"choose one of {SUPPORTED_EMAIL_PROVIDERS}"
            )
        # Startup fail-fast: a non-console provider is unusable without its
        # required config. This is the readiness guarantee for email.
        if email.provider != "console" and not email.is_configured():
            raise ValueError(
                f"EMAIL_PROVIDER={email.provider!r} requires "
                "EMAIL_FROM_ADDRESS and EMAIL_API_KEY"
            )

        return cls(
            database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
            magic_link_base_url=os.getenv(
                "MAGIC_LINK_BASE_URL", DEFAULT_MAGIC_LINK_BASE_URL
            ).rstrip("/"),
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            api_v1_prefix=api_v1_prefix,
            cors_origins=cors_origins,
            email=email,
            secret_key=os.getenv(
                "SECRET_KEY",
                "menuscan-default-insecure-secret-key-change-this-in-production",
            ),
        )


def _load_email_config() -> EmailConfig:
    return EmailConfig(
        provider=os.getenv("EMAIL_PROVIDER", DEFAULT_EMAIL_PROVIDER),
        from_address=os.getenv("EMAIL_FROM_ADDRESS", DEFAULT_EMAIL_FROM_ADDRESS),
        api_key=os.getenv("EMAIL_API_KEY"),
        api_base_url=os.getenv(
            "EMAIL_API_BASE_URL", DEFAULT_EMAIL_API_BASE_URL
        ).rstrip("/"),
        timeout_seconds=float(
            os.getenv("EMAIL_TIMEOUT_SECONDS", DEFAULT_EMAIL_TIMEOUT_SECONDS)
        ),
    )


settings = Settings.from_environment()
