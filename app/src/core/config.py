import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path


DEFAULT_DATABASE_URL = "postgresql://menuscan:localdev@localhost:5432/menuscan"
DEFAULT_MAGIC_LINK_BASE_URL = "http://localhost:5173"
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

DEFAULT_EMAIL_PROVIDER = "console"
DEFAULT_EMAIL_FROM_ADDRESS = ""
DEFAULT_EMAIL_API_BASE_URL = "https://api.resend.com"
DEFAULT_EMAIL_TIMEOUT_SECONDS = "10"

DEFAULT_STORAGE_PROVIDER = "local"
DEFAULT_STORAGE_LOCAL_ROOT = "storage/objects"
DEFAULT_STORAGE_SIGNED_URL_SECONDS = "300"

DEFAULT_OCR_PROVIDER = "fake"
DEFAULT_OCR_TIMEOUT_SECONDS = "10"
DEFAULT_OCR_MAX_IMAGE_DIMENSION = "2000"
DEFAULT_OCR_CONTRAST_FACTOR = "1.1"
DEFAULT_GOOGLE_VISION_API_BASE_URL = "https://vision.googleapis.com/v1"

DEFAULT_LLM_PROVIDER = "rule_based"
# Per-parse ceiling. With model "thinking" disabled and the pre-aligned CSV
# anchor, even large menus parse well under this on gemini-3.1-flash-lite, so a
# call that exceeds it is stuck — fail fast to the fallback model instead of
# dragging the scan out. Target: scan → menu in ~100s.
DEFAULT_LLM_TIMEOUT_SECONDS = "100"
DEFAULT_LLM_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_LLM_MODEL = "gemini-3.1-flash-lite"
# Multimodal parsing: attach the menu page image(s) to the Gemini parse call
# alongside OCR text (ADR 0003). The image drives layout / column-price
# association / grouping; OCR text stays the character-and-price anchor. Only
# the "gemini" provider consumes it; rule-based ignores images.
DEFAULT_LLM_MULTIMODAL = "true"
# Downscale ceiling for images sent to the LLM. Smaller than the OCR ceiling to
# bound image-token cost and latency, since the model reads layout, not fine print.
DEFAULT_LLM_IMAGE_MAX_DIMENSION = "1536"
# Pre-align OCR into a deterministic (name, price, size) CSV and embed it in the
# parse prompt as a strong name↔price anchor (OCR → CSV → LLM). Off sends only
# the plain OCR text / coordinate dump.
DEFAULT_LLM_PREALIGN_CSV = "true"
# Secondary Gemini model tried automatically when the primary model
# (gemini-3.1-flash-lite) is quota-exhausted (429) or unavailable, before
# degrading to the rule-based parser. It draws on a separate daily quota.
DEFAULT_LLM_FALLBACK_MODEL = "gemini-2.5-flash"
DEFAULT_SECRET_KEY = "menuscan-default-insecure-secret-key-change-this-in-production"
DEFAULT_SCAN_STALE_TIMEOUT_MINUTES = "10"
# Minimum seconds between two AI-backed calls per subject (anti-spam throttle),
# not a daily quota. Scan (OCR+LLM) is the heaviest so it gets the longer gap.
DEFAULT_SCAN_MIN_GAP_SECONDS = "10"
DEFAULT_CHAT_MIN_GAP_SECONDS = "5"
# Chat is interactive: a diner is watching a spinner. Nothing like the 100s the
# scan parse is allowed, which chat used to inherit by accident.
DEFAULT_CHAT_LLM_TIMEOUT_SECONDS = "20"
# Enrichment runs in batches behind the menu screen. Generous, but not scan-sized.
DEFAULT_ENRICH_LLM_TIMEOUT_SECONDS = "60"

# Currency conversion. open.er-api.com is free, requires no API key, supports
# VND + ~160 currencies, and is CORS-friendly. Rates are cached in-process.
DEFAULT_EXCHANGE_RATE_API_BASE_URL = "https://open.er-api.com/v6"
DEFAULT_EXCHANGE_RATE_TIMEOUT_SECONDS = "10"
DEFAULT_EXCHANGE_RATE_CACHE_TTL_SECONDS = "3600"
# Refresh-token cookie SameSite attribute. "lax" (default) is safe for
# same-origin deployments and protects /auth/refresh + /auth/logout from CSRF
# without needing a token. Set "none" ONLY for cross-origin production (FE and
# BE on different domains) — and then CSRF defense shifts to Origin checks
# baked into those endpoints.
DEFAULT_SESSION_COOKIE_SAMESITE = "lax"

SUPPORTED_EMAIL_PROVIDERS = ("console", "resend", "gmail_smtp")
SUPPORTED_STORAGE_PROVIDERS = ("local", "s3")
SUPPORTED_OCR_PROVIDERS = ("fake", "google_vision")
SUPPORTED_LLM_PROVIDERS = ("rule_based", "gemini")
SUPPORTED_COOKIE_SAMESITE = ("lax", "none", "strict")


def _load_local_env_file() -> None:
    """Load root env/.env.local for direct local app runs.

    The PowerShell task runners already load this file. This fallback covers
    teammates who start the backend directly with uvicorn. Existing environment
    variables win, and pytest is skipped to keep tests hermetic.
    """
    if any("pytest" in Path(arg).name for arg in sys.argv):
        return

    env_file = Path(__file__).resolve().parents[3] / "env" / ".env.local"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True, slots=True)
class EmailConfig:
    """Email provider configuration.

    Provider selection is env-driven (``EMAIL_PROVIDER``). ``console`` is the
    dev/test no-op; ``resend`` calls the Resend transactional API; ``gmail_smtp``
    sends via Gmail SMTP with an App Password. Secrets (``api_key``,
    ``smtp_password``) come from env and are never logged.
    """

    provider: str
    from_address: str
    api_key: str | None
    api_base_url: str
    timeout_seconds: float
    smtp_username: str | None = None
    smtp_password: str | None = None

    def is_configured(self) -> bool:
        """True when the active provider has everything it needs to send."""
        if self.provider == "console":
            return True
        if self.provider == "gmail_smtp":
            return (
                bool(self.smtp_username)
                and bool(self.smtp_password)
                and bool(self.from_address)
            )
        return bool(self.from_address) and bool(self.api_key)


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """Private object-storage configuration.

    ``local`` is for development and tests. ``s3`` targets S3-compatible
    object storage and requires every credential/bucket setting to be present.
    Buckets are private by default; access is through backend authorization or
    short-lived signed URLs.
    """

    provider: str
    local_root: str
    bucket_name: str | None
    endpoint_url: str | None
    region: str
    access_key_id: str | None
    secret_access_key: str | None
    session_token: str | None
    signed_url_seconds: int

    def is_configured(self) -> bool:
        if self.provider == "local":
            return True
        return all(
            (
                self.bucket_name,
                self.endpoint_url,
                self.access_key_id,
                self.secret_access_key,
            )
        )


@dataclass(frozen=True, slots=True)
class OcrConfig:
    """OCR provider and preprocessing configuration."""

    provider: str
    timeout_seconds: float
    max_image_dimension: int
    contrast_factor: float
    google_vision_api_key: str | None
    google_vision_api_base_url: str
    google_vision_model: str

    def is_configured(self) -> bool:
        if self.provider == "fake":
            return True
        return bool(self.google_vision_api_key)


@dataclass(frozen=True, slots=True)
class LlmConfig:
    """LLM parser configuration.

    ``rule_based`` is the dev/test default. ``gemini`` calls the Google Gemini
    REST API using a key from environment variables; secrets are never logged.
    """

    provider: str
    model: str
    api_key: str | None
    api_base_url: str
    timeout_seconds: float
    fallback_model: str | None = None
    multimodal: bool = True
    prealign_csv: bool = True
    image_max_dimension: int = int(DEFAULT_LLM_IMAGE_MAX_DIMENSION)
    # Key pool tried in order; a 429/quota on one key rotates to the next for the
    # same model before degrading to the next model in ``models``.
    api_keys: tuple[str, ...] = ()
    # Model failover chain (strongest first). Each model uses the full key pool.
    models: tuple[str, ...] = ()

    def is_configured(self) -> bool:
        if self.provider == "rule_based":
            return True
        return bool(self.api_key)


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
    storage: StorageConfig
    llm: LlmConfig = field(
        default_factory=lambda: LlmConfig(
            provider=DEFAULT_LLM_PROVIDER,
            model=DEFAULT_LLM_MODEL,
            api_key=None,
            api_base_url=DEFAULT_LLM_API_BASE_URL,
            timeout_seconds=float(DEFAULT_LLM_TIMEOUT_SECONDS),
        )
    )
    # Chat's own LLM config (independent from scan). See _load_chat_llm_config.
    chat_llm: LlmConfig = field(
        default_factory=lambda: LlmConfig(
            provider=DEFAULT_LLM_PROVIDER,
            model=DEFAULT_LLM_MODEL,
            api_key=None,
            api_base_url=DEFAULT_LLM_API_BASE_URL,
            timeout_seconds=float(DEFAULT_LLM_TIMEOUT_SECONDS),
        )
    )
    # Enrichment's own LLM config. See _load_enrich_llm_config.
    enrich_llm: LlmConfig = field(
        default_factory=lambda: LlmConfig(
            provider=DEFAULT_LLM_PROVIDER,
            model=DEFAULT_LLM_MODEL,
            api_key=None,
            api_base_url=DEFAULT_LLM_API_BASE_URL,
            timeout_seconds=float(DEFAULT_LLM_TIMEOUT_SECONDS),
        )
    )
    ocr: OcrConfig = field(
        default_factory=lambda: OcrConfig(
            provider=DEFAULT_OCR_PROVIDER,
            timeout_seconds=float(DEFAULT_OCR_TIMEOUT_SECONDS),
            max_image_dimension=int(DEFAULT_OCR_MAX_IMAGE_DIMENSION),
            contrast_factor=float(DEFAULT_OCR_CONTRAST_FACTOR),
            google_vision_api_key=None,
            google_vision_api_base_url=DEFAULT_GOOGLE_VISION_API_BASE_URL,
            google_vision_model="DOCUMENT_TEXT_DETECTION",
        )
    )
    secret_key: str = DEFAULT_SECRET_KEY
    scan_stale_timeout_minutes: int = int(DEFAULT_SCAN_STALE_TIMEOUT_MINUTES)
    exchange_rate_api_base_url: str = DEFAULT_EXCHANGE_RATE_API_BASE_URL
    exchange_rate_timeout_seconds: float = float(DEFAULT_EXCHANGE_RATE_TIMEOUT_SECONDS)
    exchange_rate_cache_ttl_seconds: int = int(DEFAULT_EXCHANGE_RATE_CACHE_TTL_SECONDS)
    scan_min_gap_seconds: int = int(DEFAULT_SCAN_MIN_GAP_SECONDS)
    chat_min_gap_seconds: int = int(DEFAULT_CHAT_MIN_GAP_SECONDS)
    session_cookie_samesite: str = DEFAULT_SESSION_COOKIE_SAMESITE

    @classmethod
    def from_environment(cls) -> "Settings":

        app_env = os.getenv("APP_ENV", "development")
        secret_key = _env_or_default("SECRET_KEY", DEFAULT_SECRET_KEY)
        # Startup fail-fast: refuse to boot a non-dev/test deployment that is
        # still signing JWTs with the public default secret. Same philosophy as
        # the CORS/storage/email/LLM checks below — better to refuse than to
        # silently ship a forgeable-token deployment.
        if app_env not in {"development", "test"} and secret_key == DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be set to a non-default value when "
                f"APP_ENV={app_env!r} (the built-in default is public and "
                "insecure)"
            )

        raw_origins = os.getenv("CORS_ORIGINS")
        cors_origins = (
            tuple(
                origin.strip().rstrip("/")
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
            if email.provider == "gmail_smtp":
                raise ValueError(
                    "EMAIL_PROVIDER='gmail_smtp' requires "
                    "EMAIL_FROM_ADDRESS, EMAIL_SMTP_USERNAME and EMAIL_SMTP_PASSWORD"
                )
            raise ValueError(
                f"EMAIL_PROVIDER={email.provider!r} requires "
                "EMAIL_FROM_ADDRESS and EMAIL_API_KEY"
            )

        storage = _load_storage_config()
        if storage.provider not in SUPPORTED_STORAGE_PROVIDERS:
            raise ValueError(
                f"STORAGE_PROVIDER={storage.provider!r} is not supported; "
                f"choose one of {SUPPORTED_STORAGE_PROVIDERS}"
            )
        if storage.provider != "local" and not storage.is_configured():
            raise ValueError(
                f"STORAGE_PROVIDER={storage.provider!r} requires "
                "STORAGE_BUCKET_NAME, STORAGE_ENDPOINT_URL, "
                "STORAGE_ACCESS_KEY_ID and STORAGE_SECRET_ACCESS_KEY"
            )

        ocr = _load_ocr_config()
        if ocr.provider not in SUPPORTED_OCR_PROVIDERS:
            raise ValueError(
                f"OCR_PROVIDER={ocr.provider!r} is not supported; "
                f"choose one of {SUPPORTED_OCR_PROVIDERS}"
            )
        if not ocr.is_configured():
            raise ValueError(
                f"OCR_PROVIDER={ocr.provider!r} requires GOOGLE_VISION_API_KEY"
            )

        llm = _load_llm_config()
        if llm.provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"LLM_PROVIDER={llm.provider!r} is not supported; "
                f"choose one of {SUPPORTED_LLM_PROVIDERS}"
            )
        if not llm.is_configured():
            raise ValueError(
                f"LLM_PROVIDER={llm.provider!r} requires LLM_API_KEY or GEMINI_API_KEY"
            )

        # Same fail-fast for chat. Without it, a production deploy with a chat
        # provider but no chat key degrades at request time to RuleBasedChat — the
        # diner gets a canned "the assistant is not enabled here" string, and
        # nothing is logged or alerted. Better to refuse to boot.
        chat_llm = _load_chat_llm_config(llm)
        if chat_llm.provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"CHAT_LLM_PROVIDER={chat_llm.provider!r} is not supported; "
                f"choose one of {SUPPORTED_LLM_PROVIDERS}"
            )
        if not chat_llm.is_configured():
            raise ValueError(
                f"CHAT_LLM_PROVIDER={chat_llm.provider!r} requires a key "
                "(CHAT_GEMINI_API_KEYS / CHAT_LLM_API_KEY, or the base LLM key)"
            )

        enrich_llm = _load_enrich_llm_config(llm)
        if enrich_llm.provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"ENRICH_LLM_PROVIDER={enrich_llm.provider!r} is not supported; "
                f"choose one of {SUPPORTED_LLM_PROVIDERS}"
            )
        if not enrich_llm.is_configured():
            raise ValueError(
                f"ENRICH_LLM_PROVIDER={enrich_llm.provider!r} requires a key "
                "(ENRICH_GEMINI_API_KEYS / ENRICH_LLM_API_KEY, or the base LLM key)"
            )

        session_cookie_samesite = os.getenv(
            "SESSION_COOKIE_SAMESITE", DEFAULT_SESSION_COOKIE_SAMESITE
        ).strip().lower()
        if session_cookie_samesite not in SUPPORTED_COOKIE_SAMESITE:
            raise ValueError(
                f"SESSION_COOKIE_SAMESITE={session_cookie_samesite!r} is not "
                f"supported; choose one of {SUPPORTED_COOKIE_SAMESITE}"
            )

        return cls(
            database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
            magic_link_base_url=os.getenv(
                "MAGIC_LINK_BASE_URL", DEFAULT_MAGIC_LINK_BASE_URL
            )
            .strip()
            .rstrip("/"),
            app_env=app_env,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            api_v1_prefix=api_v1_prefix,
            cors_origins=cors_origins,
            email=email,
            storage=storage,
            llm=llm,
            chat_llm=chat_llm,
            enrich_llm=enrich_llm,
            ocr=ocr,
            secret_key=secret_key,
            scan_stale_timeout_minutes=_load_scan_stale_timeout_minutes(),
            exchange_rate_api_base_url=os.getenv(
                "EXCHANGE_RATE_API_BASE_URL", DEFAULT_EXCHANGE_RATE_API_BASE_URL
            ).rstrip("/"),
            exchange_rate_timeout_seconds=float(
                os.getenv(
                    "EXCHANGE_RATE_TIMEOUT_SECONDS",
                    DEFAULT_EXCHANGE_RATE_TIMEOUT_SECONDS,
                )
            ),
            exchange_rate_cache_ttl_seconds=int(
                os.getenv(
                    "EXCHANGE_RATE_CACHE_TTL_SECONDS",
                    DEFAULT_EXCHANGE_RATE_CACHE_TTL_SECONDS,
                )
            ),
            scan_min_gap_seconds=int(
                os.getenv("SCAN_MIN_GAP_SECONDS", DEFAULT_SCAN_MIN_GAP_SECONDS)
            ),
            chat_min_gap_seconds=int(
                os.getenv("CHAT_MIN_GAP_SECONDS", DEFAULT_CHAT_MIN_GAP_SECONDS)
            ),
            session_cookie_samesite=session_cookie_samesite,
        )


def _load_email_config() -> EmailConfig:
    return EmailConfig(
        provider=os.getenv("EMAIL_PROVIDER", DEFAULT_EMAIL_PROVIDER),
        from_address=os.getenv("EMAIL_FROM_ADDRESS", DEFAULT_EMAIL_FROM_ADDRESS),
        api_key=os.getenv("EMAIL_API_KEY"),
        api_base_url=os.getenv("EMAIL_API_BASE_URL", DEFAULT_EMAIL_API_BASE_URL).rstrip(
            "/"
        ),
        timeout_seconds=float(
            os.getenv("EMAIL_TIMEOUT_SECONDS", DEFAULT_EMAIL_TIMEOUT_SECONDS)
        ),
        smtp_username=os.getenv("EMAIL_SMTP_USERNAME"),
        smtp_password=os.getenv("EMAIL_SMTP_PASSWORD"),
    )


def _load_storage_config() -> StorageConfig:
    return StorageConfig(
        provider=os.getenv("STORAGE_PROVIDER", DEFAULT_STORAGE_PROVIDER),
        local_root=os.getenv("STORAGE_LOCAL_ROOT", DEFAULT_STORAGE_LOCAL_ROOT),
        bucket_name=os.getenv("STORAGE_BUCKET_NAME"),
        endpoint_url=os.getenv("STORAGE_ENDPOINT_URL"),
        region=os.getenv("STORAGE_REGION", "us-east-1"),
        access_key_id=os.getenv("STORAGE_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("STORAGE_SECRET_ACCESS_KEY"),
        session_token=os.getenv("STORAGE_SESSION_TOKEN"),
        signed_url_seconds=int(
            os.getenv(
                "STORAGE_SIGNED_URL_SECONDS",
                DEFAULT_STORAGE_SIGNED_URL_SECONDS,
            )
        ),
    )


def _load_ocr_config() -> OcrConfig:
    return OcrConfig(
        provider=os.getenv("OCR_PROVIDER", DEFAULT_OCR_PROVIDER),
        timeout_seconds=float(
            os.getenv("OCR_TIMEOUT_SECONDS", DEFAULT_OCR_TIMEOUT_SECONDS)
        ),
        max_image_dimension=int(
            os.getenv("OCR_MAX_IMAGE_DIMENSION", DEFAULT_OCR_MAX_IMAGE_DIMENSION)
        ),
        contrast_factor=float(
            os.getenv("OCR_CONTRAST_FACTOR", DEFAULT_OCR_CONTRAST_FACTOR)
        ),
        google_vision_api_key=os.getenv("GOOGLE_VISION_API_KEY"),
        google_vision_api_base_url=os.getenv(
            "GOOGLE_VISION_API_BASE_URL",
            DEFAULT_GOOGLE_VISION_API_BASE_URL,
        ).rstrip("/"),
        google_vision_model=os.getenv(
            "GOOGLE_VISION_MODEL",
            "DOCUMENT_TEXT_DETECTION",
        ),
    )


def _load_llm_config() -> LlmConfig:
    model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
    fallback_model = os.getenv("LLM_FALLBACK_MODEL", DEFAULT_LLM_FALLBACK_MODEL) or None

    # Key pool: GEMINI_API_KEYS (comma-separated) wins; otherwise the single key.
    single_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    pool = _split_csv(os.getenv("GEMINI_API_KEYS"))
    api_keys = tuple(pool) if pool else (tuple([single_key]) if single_key else ())

    # Model failover chain: LLM_MODELS (comma-separated) wins; otherwise the
    # primary model followed by the distinct fallback model.
    models_env = _split_csv(os.getenv("LLM_MODELS"))
    if models_env:
        models = tuple(models_env)
    else:
        models = (model,) + (
            (fallback_model,) if fallback_model and fallback_model != model else ()
        )

    return LlmConfig(
        provider=os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER),
        model=models[0] if models else model,
        api_key=api_keys[0] if api_keys else None,
        api_base_url=os.getenv(
            "LLM_API_BASE_URL",
            DEFAULT_LLM_API_BASE_URL,
        ).rstrip("/"),
        timeout_seconds=float(
            os.getenv("LLM_TIMEOUT_SECONDS", DEFAULT_LLM_TIMEOUT_SECONDS)
        ),
        fallback_model=fallback_model,
        multimodal=_env_bool("LLM_MULTIMODAL", DEFAULT_LLM_MULTIMODAL),
        prealign_csv=_env_bool("LLM_PREALIGN_CSV", DEFAULT_LLM_PREALIGN_CSV),
        image_max_dimension=int(
            os.getenv("LLM_IMAGE_MAX_DIMENSION", DEFAULT_LLM_IMAGE_MAX_DIMENSION)
        ),
        api_keys=api_keys,
        models=models,
    )


def _load_enrich_llm_config(base: LlmConfig) -> LlmConfig:
    """The food-enrichment pass's own LLM config, independent from the scan.

    Reads ``ENRICH_*`` env vars, falling back to the scan config so enrichment
    still works without extra setup.

    It needs its own key. Sharing the scan's key means the two compete for the same
    per-minute quota, and since enrichment fires several batches at once right after
    a scan finishes, they collide by construction — a 429, every dish untagged, and
    no verdicts on the menu.
    """
    single_key = os.getenv("ENRICH_LLM_API_KEY") or os.getenv("ENRICH_GEMINI_API_KEY")
    pool = _split_csv(os.getenv("ENRICH_GEMINI_API_KEYS"))
    if pool:
        api_keys: tuple[str, ...] = tuple(pool)
    elif single_key:
        api_keys = (single_key,)
    else:
        api_keys = base.api_keys

    models_env = _split_csv(os.getenv("ENRICH_LLM_MODELS"))
    single_model = os.getenv("ENRICH_LLM_MODEL")
    if models_env:
        models: tuple[str, ...] = tuple(models_env)
    elif single_model:
        models = (single_model,)
    else:
        models = base.models

    return replace(
        base,
        provider=os.getenv("ENRICH_LLM_PROVIDER", base.provider),
        api_key=api_keys[0] if api_keys else None,
        api_keys=api_keys,
        model=models[0] if models else base.model,
        models=models,
        # Enrichment is short-text inference, not a multimodal parse of a menu
        # photo. It has no business inheriting the scan's 100s ceiling.
        timeout_seconds=float(
            os.getenv("ENRICH_LLM_TIMEOUT_SECONDS", DEFAULT_ENRICH_LLM_TIMEOUT_SECONDS)
        ),
    )


def _load_chat_llm_config(base: LlmConfig) -> LlmConfig:
    """Chat's own LLM config, independent from the scan pipeline.

    Reads ``CHAT_*`` env vars; anything unset falls back to the main LLM config
    so chat still works without extra setup, while a dedicated key/model can be
    split out (so chat and scan don't share quota or model).
    """
    single_key = os.getenv("CHAT_LLM_API_KEY") or os.getenv("CHAT_GEMINI_API_KEY")
    pool = _split_csv(os.getenv("CHAT_GEMINI_API_KEYS"))
    if pool:
        api_keys: tuple[str, ...] = tuple(pool)
    elif single_key:
        api_keys = (single_key,)
    else:
        api_keys = base.api_keys

    models_env = _split_csv(os.getenv("CHAT_LLM_MODELS"))
    single_model = os.getenv("CHAT_LLM_MODEL")
    if models_env:
        models: tuple[str, ...] = tuple(models_env)
    elif single_model:
        models = (single_model,)
    else:
        models = base.models

    return replace(
        base,
        provider=os.getenv("CHAT_LLM_PROVIDER", base.provider),
        api_key=api_keys[0] if api_keys else None,
        api_keys=api_keys,
        model=models[0] if models else base.model,
        models=models,
        # Chat used to silently inherit the SCAN timeout — 100 seconds, a number
        # tuned for a multimodal parse of a whole menu photo. Nobody sits through
        # 100s of spinner for a chat reply; they reload the page long before that.
        timeout_seconds=float(
            os.getenv("CHAT_LLM_TIMEOUT_SECONDS", DEFAULT_CHAT_LLM_TIMEOUT_SECONDS)
        ),
    )


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_scan_stale_timeout_minutes() -> int:
    value = int(
        os.getenv("SCAN_STALE_TIMEOUT_MINUTES", DEFAULT_SCAN_STALE_TIMEOUT_MINUTES)
    )
    if value < 1:
        raise ValueError("SCAN_STALE_TIMEOUT_MINUTES must be >= 1")
    return value


def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value


def _env_bool(name: str, default: str) -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}


_load_local_env_file()
settings = Settings.from_environment()
