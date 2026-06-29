from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import CHAR, Numeric, func

from src.core import database
from src.core.database import Base
from src.modules.identity.models import (  # noqa: F401
    MagicLinkToken,
    User,
    UserSession,
)
from src.modules.menu.models import FoodItem, Menu  # noqa: F401
from src.modules.menu_scan.models import OcrResult, ScanSession  # noqa: F401


EXPECTED_TABLES = {
    "users",
    "magic_link_tokens",
    "user_sessions",
    "scan_sessions",
    "ocr_results",
    "menus",
    "food_items",
}

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_metadata_registers_all_mvp_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_models_do_not_define_password_columns() -> None:
    for table in Base.metadata.tables.values():
        column_names = set(table.columns.keys())
        if table.name == "users":
            assert "password" not in column_names  # raw passwords must never be stored
            assert (
                "password_hash" in column_names
            )  # password_hash is now allowed on users
        else:
            assert "password" not in column_names
            assert "password_hash" not in column_names


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/alembic/versions/001_create_mvp_schema.py",
        "DB/schema.sql",
        "doc/diagrams/ERD Diagram.drawio",
    ],
)
def test_mvp_schema_sources_do_not_contain_password_fields(
    relative_path: str,
) -> None:
    content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
    assert "password_hash" not in content
    assert "password:" not in content


def test_price_and_currency_use_exact_database_types() -> None:
    price = FoodItem.__table__.c.price.type
    currency = FoodItem.__table__.c.currency.type

    assert isinstance(price, Numeric)
    assert price.precision == 14
    assert price.scale == 2
    assert isinstance(currency, CHAR)
    assert currency.length == 3


def test_user_email_has_case_insensitive_unique_index() -> None:
    index = next(
        item for item in User.__table__.indexes if item.name == "uq_users_email_lower"
    )

    assert index.unique
    assert str(index.expressions[0]) == str(func.lower(User.email))


def test_required_relationship_constraints_are_present() -> None:
    assert OcrResult.__table__.c.scan_session_id.unique
    assert Menu.__table__.c.scan_session_id.unique
    assert MagicLinkToken.__table__.c.token_hash.unique
    assert UserSession.__table__.c.refresh_token_hash.unique

    food_item_unique_constraints = {
        constraint.name
        for constraint in FoodItem.__table__.constraints
        if constraint.name is not None
    }
    assert "uq_food_items_menu_id_sort_order" in food_item_unique_constraints


def test_get_db_closes_session_without_implicit_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock()
    monkeypatch.setattr(database, "SessionLocal", Mock(return_value=session))

    dependency = database.get_db()
    assert next(dependency) is session
    dependency.close()

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_called_once_with()


def test_get_db_rolls_back_and_closes_session_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock()
    monkeypatch.setattr(database, "SessionLocal", Mock(return_value=session))

    dependency = database.get_db()
    assert next(dependency) is session

    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()
