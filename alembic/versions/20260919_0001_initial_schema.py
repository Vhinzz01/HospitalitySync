"""Create the initial HospitalitySync schema.

Revision ID: 20260919_0001
Revises:
Create Date: 2026-09-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260919_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Required by the GiST exclusion constraint combining BIGINT and daterange.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('RECEPTION', 'KITCHEN', 'GUEST')",
            name=op.f("ck_users_valid_role"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'AVAILABLE'"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("capacity > 0", name=op.f("ck_rooms_positive_capacity")),
        sa.CheckConstraint(
            "status IN ('AVAILABLE', 'OCCUPIED', 'CLEANING', 'MAINTENANCE')",
            name=op.f("ck_rooms_valid_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rooms")),
        sa.UniqueConstraint("number", name=op.f("uq_rooms_number")),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "available", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "price >= 0", name=op.f("ck_menu_items_non_negative_price")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_menu_items")),
    )

    op.create_table(
        "guests",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("document", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_guests_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guests")),
        sa.UniqueConstraint("document", name=op.f("uq_guests_document")),
        sa.UniqueConstraint("user_id", name=op.f("uq_guests_user_id")),
    )

    op.create_table(
        "room_devices",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("room_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("credential_hash", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pairing_code_hash", sa.String(length=255), nullable=True),
        sa.Column("pairing_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "active = false OR "
            "(credential_hash IS NOT NULL AND provisioned_at IS NOT NULL)",
            name=op.f("ck_room_devices_active_device_is_provisioned"),
        ),
        sa.CheckConstraint(
            "(pairing_code_hash IS NULL AND pairing_expires_at IS NULL) OR "
            "(pairing_code_hash IS NOT NULL AND pairing_expires_at IS NOT NULL)",
            name=op.f("ck_room_devices_pairing_fields_together"),
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_room_devices_room_id_rooms"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_room_devices")),
        sa.UniqueConstraint("code", name=op.f("uq_room_devices_code")),
        sa.UniqueConstraint(
            "credential_hash", name=op.f("uq_room_devices_credential_hash")
        ),
        sa.UniqueConstraint(
            "pairing_code_hash", name=op.f("uq_room_devices_pairing_code_hash")
        ),
    )
    op.create_index(
        op.f("ix_room_devices_room_id"),
        "room_devices",
        ["room_id"],
        unique=False,
    )
    op.create_index(
        "uq_room_devices_active_room",
        "room_devices",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("active = true"),
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("guest_id", sa.BigInteger(), nullable=False),
        sa.Column("room_id", sa.BigInteger(), nullable=False),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("check_out_date", sa.Date(), nullable=False),
        sa.Column("guest_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'CONFIRMED'"),
            nullable=False,
        ),
        sa.Column("actual_check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "guest_count > 0", name=op.f("ck_reservations_positive_guest_count")
        ),
        sa.CheckConstraint(
            "(status IN ('CONFIRMED', 'CANCELLED') "
            "AND actual_check_in_at IS NULL AND actual_check_out_at IS NULL) OR "
            "(status = 'CHECKED_IN' "
            "AND actual_check_in_at IS NOT NULL AND actual_check_out_at IS NULL) OR "
            "(status = 'CHECKED_OUT' "
            "AND actual_check_in_at IS NOT NULL AND actual_check_out_at IS NOT NULL)",
            name=op.f("ck_reservations_status_matches_actual_times"),
        ),
        sa.CheckConstraint(
            "actual_check_out_at IS NULL OR "
            "(actual_check_in_at IS NOT NULL "
            "AND actual_check_out_at > actual_check_in_at)",
            name=op.f("ck_reservations_valid_actual_times"),
        ),
        sa.CheckConstraint(
            "check_out_date > check_in_date",
            name=op.f("ck_reservations_valid_date_range"),
        ),
        sa.CheckConstraint(
            "status IN ('CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT', 'CANCELLED')",
            name=op.f("ck_reservations_valid_status"),
        ),
        postgresql.ExcludeConstraint(
            ("room_id", "="),
            (
                sa.func.daterange(
                    sa.text("check_in_date"), sa.text("check_out_date"), "[)"
                ),
                "&&",
            ),
            where=sa.text("status IN ('CONFIRMED', 'CHECKED_IN')"),
            using="gist",
            name="exclude_overlapping_active_reservations",
        ),
        sa.ForeignKeyConstraint(
            ["guest_id"],
            ["guests.id"],
            name=op.f("fk_reservations_guest_id_guests"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_reservations_room_id_rooms"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reservations")),
    )
    op.create_index(
        op.f("ix_reservations_guest_id"),
        "reservations",
        ["guest_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reservations_room_id"),
        "reservations",
        ["room_id"],
        unique=False,
    )

    op.create_table(
        "food_orders",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("reservation_id", sa.BigInteger(), nullable=False),
        sa.Column("room_device_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'RECEIVED'"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'DELIVERED' AND delivered_at IS NOT NULL) OR "
            "(status <> 'DELIVERED' AND delivered_at IS NULL)",
            name=op.f("ck_food_orders_status_matches_delivered_at"),
        ),
        sa.CheckConstraint(
            "status IN ('RECEIVED', 'PREPARING', 'READY', 'DELIVERED')",
            name=op.f("ck_food_orders_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
            name=op.f("fk_food_orders_reservation_id_reservations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_device_id"],
            ["room_devices.id"],
            name=op.f("fk_food_orders_room_device_id_room_devices"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_food_orders")),
    )
    op.create_index(
        op.f("ix_food_orders_reservation_id"),
        "food_orders",
        ["reservation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_food_orders_room_device_id"),
        "food_orders",
        ["room_device_id"],
        unique=False,
    )

    op.create_table(
        "service_requests",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("room_id", sa.BigInteger(), nullable=False),
        sa.Column("reservation_id", sa.BigInteger(), nullable=True),
        sa.Column("room_device_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "NOT (room_device_id IS NOT NULL AND created_by_user_id IS NOT NULL)",
            name=op.f("ck_service_requests_single_creator"),
        ),
        sa.CheckConstraint(
            "(status = 'COMPLETED' AND completed_at IS NOT NULL) OR "
            "(status <> 'COMPLETED' AND completed_at IS NULL)",
            name=op.f("ck_service_requests_status_matches_completed_at"),
        ),
        sa.CheckConstraint(
            "category IN ('CLEANING', 'MAINTENANCE', 'COMPLAINT')",
            name=op.f("ck_service_requests_valid_category"),
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name=op.f("ck_service_requests_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_service_requests_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
            name=op.f("fk_service_requests_reservation_id_reservations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_device_id"],
            ["room_devices.id"],
            name=op.f("fk_service_requests_room_device_id_room_devices"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_service_requests_room_id_rooms"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_requests")),
    )
    for column_name in (
        "created_by_user_id",
        "reservation_id",
        "room_device_id",
        "room_id",
    ):
        op.create_index(
            op.f(f"ix_service_requests_{column_name}"),
            "service_requests",
            [column_name],
            unique=False,
        )

    op.create_table(
        "food_order_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("food_order_id", sa.BigInteger(), nullable=False),
        sa.Column("menu_item_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.CheckConstraint(
            "unit_price >= 0",
            name=op.f("ck_food_order_items_non_negative_unit_price"),
        ),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_food_order_items_positive_quantity")
        ),
        sa.ForeignKeyConstraint(
            ["food_order_id"],
            ["food_orders.id"],
            name=op.f("fk_food_order_items_food_order_id_food_orders"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["menu_item_id"],
            ["menu_items.id"],
            name=op.f("fk_food_order_items_menu_item_id_menu_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_food_order_items")),
        sa.UniqueConstraint(
            "food_order_id",
            "menu_item_id",
            name="uq_food_order_items_order_menu_item",
        ),
    )
    op.create_index(
        op.f("ix_food_order_items_food_order_id"),
        "food_order_items",
        ["food_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_food_order_items_menu_item_id"),
        "food_order_items",
        ["menu_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_food_order_items_menu_item_id"), table_name="food_order_items"
    )
    op.drop_index(
        op.f("ix_food_order_items_food_order_id"), table_name="food_order_items"
    )
    op.drop_table("food_order_items")

    for column_name in (
        "room_id",
        "room_device_id",
        "reservation_id",
        "created_by_user_id",
    ):
        op.drop_index(
            op.f(f"ix_service_requests_{column_name}"),
            table_name="service_requests",
        )
    op.drop_table("service_requests")

    op.drop_index(
        op.f("ix_food_orders_room_device_id"), table_name="food_orders"
    )
    op.drop_index(
        op.f("ix_food_orders_reservation_id"), table_name="food_orders"
    )
    op.drop_table("food_orders")

    op.drop_index(op.f("ix_reservations_room_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_guest_id"), table_name="reservations")
    op.drop_table("reservations")

    op.drop_index("uq_room_devices_active_room", table_name="room_devices")
    op.drop_index(op.f("ix_room_devices_room_id"), table_name="room_devices")
    op.drop_table("room_devices")

    op.drop_table("guests")
    op.drop_table("menu_items")
    op.drop_table("rooms")

    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")

    # The extension is intentionally kept: it may be shared by other schemas.
