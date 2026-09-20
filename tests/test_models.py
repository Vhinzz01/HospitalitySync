from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from app.database.base import Base
import app.models  # noqa: F401  # registers every model in Base.metadata


EXPECTED_TABLES = {
    "users",
    "guests",
    "rooms",
    "room_devices",
    "reservations",
    "service_requests",
    "menu_items",
    "food_orders",
    "food_order_items",
}


def test_all_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_table_has_a_primary_key() -> None:
    for table in Base.metadata.tables.values():
        assert list(table.primary_key.columns), f"{table.name} has no primary key"


def test_domain_tables_define_database_constraints() -> None:
    assert any(
        isinstance(item, CheckConstraint)
        for item in Base.metadata.tables["reservations"].constraints
    )
    assert any(
        isinstance(item, UniqueConstraint)
        for item in Base.metadata.tables["food_order_items"].constraints
    )


def test_user_email_index_is_case_insensitive() -> None:
    index = next(
        item
        for item in Base.metadata.tables["users"].indexes
        if item.name == "uq_users_email_lower"
    )
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))

    assert ddl == "CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))"
