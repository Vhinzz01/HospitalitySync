from sqlalchemy import BigInteger, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateIndex

import app.models  # noqa: F401  # registers every model in Base.metadata
from app.database.base import Base
from app.models import Guest, Reservation, Room, RoomDevice, User


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

EXPECTED_COLUMNS = {
    "users": {
        "id",
        "name",
        "email",
        "password_hash",
        "role",
        "active",
        "created_at",
        "updated_at",
    },
    "guests": {
        "id",
        "user_id",
        "full_name",
        "document",
        "email",
        "phone",
        "active",
        "created_at",
        "updated_at",
    },
    "rooms": {
        "id",
        "number",
        "category",
        "capacity",
        "status",
        "active",
        "created_at",
        "updated_at",
    },
    "room_devices": {
        "id",
        "room_id",
        "code",
        "credential_hash",
        "active",
        "provisioned_at",
        "last_seen_at",
        "pairing_code_hash",
        "pairing_expires_at",
        "created_at",
        "updated_at",
    },
    "reservations": {
        "id",
        "guest_id",
        "room_id",
        "check_in_date",
        "check_out_date",
        "guest_count",
        "status",
        "actual_check_in_at",
        "actual_check_out_at",
        "notes",
        "created_at",
        "updated_at",
    },
    "service_requests": {
        "id",
        "room_id",
        "reservation_id",
        "room_device_id",
        "created_by_user_id",
        "category",
        "status",
        "description",
        "completed_at",
        "created_at",
        "updated_at",
    },
    "menu_items": {
        "id",
        "name",
        "description",
        "price",
        "available",
        "created_at",
        "updated_at",
    },
    "food_orders": {
        "id",
        "reservation_id",
        "room_device_id",
        "status",
        "notes",
        "delivered_at",
        "created_at",
        "updated_at",
    },
    "food_order_items": {
        "id",
        "food_order_id",
        "menu_item_id",
        "quantity",
        "unit_price",
    },
}

EXPECTED_FOREIGN_KEYS = {
    ("guests", "user_id", "users.id"),
    ("room_devices", "room_id", "rooms.id"),
    ("reservations", "guest_id", "guests.id"),
    ("reservations", "room_id", "rooms.id"),
    ("service_requests", "room_id", "rooms.id"),
    ("service_requests", "reservation_id", "reservations.id"),
    ("service_requests", "room_device_id", "room_devices.id"),
    ("service_requests", "created_by_user_id", "users.id"),
    ("food_orders", "reservation_id", "reservations.id"),
    ("food_orders", "room_device_id", "room_devices.id"),
    ("food_order_items", "food_order_id", "food_orders.id"),
    ("food_order_items", "menu_item_id", "menu_items.id"),
}


def test_all_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_table_has_a_primary_key() -> None:
    for table in Base.metadata.tables.values():
        primary_key_columns = list(table.primary_key.columns)

        assert [column.name for column in primary_key_columns] == ["id"]
        assert isinstance(primary_key_columns[0].type, BigInteger)
        assert primary_key_columns[0].nullable is False


def test_tables_have_only_the_approved_columns() -> None:
    actual_columns = {
        table.name: set(table.columns.keys()) for table in Base.metadata.tables.values()
    }

    assert actual_columns == EXPECTED_COLUMNS


def test_foreign_keys_match_the_approved_model() -> None:
    actual_foreign_keys = {
        (table.name, foreign_key.parent.name, foreign_key.target_fullname)
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    }

    assert actual_foreign_keys == EXPECTED_FOREIGN_KEYS
    assert all(
        foreign_key.ondelete == "RESTRICT"
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    )


def test_relationship_cardinalities() -> None:
    configure_mappers()

    assert User.guest.property.uselist is False
    assert Guest.user.property.uselist is False
    assert Guest.reservations.property.uselist is True
    assert Reservation.guest.property.uselist is False
    assert Reservation.room.property.uselist is False
    assert Room.reservations.property.uselist is True
    assert Room.devices.property.uselist is True
    assert RoomDevice.room.property.uselist is False


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
