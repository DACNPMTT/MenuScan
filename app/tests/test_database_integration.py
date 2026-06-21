import os
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="PostgreSQL integration tests require RUN_DATABASE_TESTS=1",
)

EXPECTED_TABLES = {
    "alembic_version",
    "users",
    "magic_link_tokens",
    "user_sessions",
    "scan_sessions",
    "ocr_results",
    "menus",
    "food_items",
}


@pytest.fixture
def database_engine():
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def test_migration_creates_all_required_tables(database_engine) -> None:
    table_names = set(inspect(database_engine).get_table_names())
    assert EXPECTED_TABLES <= table_names


def test_user_email_is_unique_ignoring_case(database_engine) -> None:
    email = f"case-{uuid.uuid4()}@example.com"

    with database_engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (id, email)
                VALUES (:id, :email)
                """
            ),
            {"id": uuid.uuid4(), "email": email},
        )

    try:
        with pytest.raises(IntegrityError):
            with database_engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO users (id, email)
                        VALUES (:id, :email)
                        """
                    ),
                    {"id": uuid.uuid4(), "email": email.upper()},
                )
    finally:
        with database_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM users WHERE lower(email) = lower(:email)"),
                {"email": email},
            )
