"""add help service request category

Revision ID: 14dcc1cd477e
Revises: 20260919_0001
Create Date: 2026-09-20 00:13:11.049167

"""
from collections.abc import Sequence

from alembic import op



revision: str = "14dcc1cd477e"
down_revision: str | Sequence[str] | None = "20260919_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_service_requests_valid_category"),
        "service_requests",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_service_requests_valid_category"),
        "service_requests",
        "category IN ('CLEANING', 'MAINTENANCE', 'HELP', 'COMPLAINT')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_service_requests_valid_category"),
        "service_requests",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_service_requests_valid_category"),
        "service_requests",
        "category IN ('CLEANING', 'MAINTENANCE', 'COMPLAINT')",
    )
