import os


DEFAULT_DATABASE_URL = (
    "postgresql://menuscan:localdev@localhost:54320/menuscan"
)


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


settings = Settings()
