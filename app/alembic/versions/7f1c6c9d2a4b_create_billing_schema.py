"""create_billing_schema

Revision ID: 7f1c6c9d2a4b
Revises: ea82caf848bf
Create Date: 2026-06-30 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7f1c6c9d2a4b"
down_revision: str | None = "ea82caf848bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bill_status = postgresql.ENUM(
        "DRAFT",
        "FINALIZED",
        name="bill_status",
    )
    bill_status.create(op.get_bind(), checkfirst=True)

    bill_adjustment_type = postgresql.ENUM(
        "DISCOUNT",
        "SURCHARGE",
        "TAX",
        "SERVICE_CHARGE",
        "ROUNDING",
        name="bill_adjustment_type",
    )
    bill_adjustment_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("menu_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DRAFT",
                "FINALIZED",
                name="bill_status",
                create_type=False,
            ),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column(
            "subtotal_amount",
            sa.Numeric(14, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "adjustment_total",
            sa.Numeric(14, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(14, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FINALIZED')",
            name="ck_bills_status",
        ),
        sa.CheckConstraint(
            "status != 'FINALIZED' OR finalized_at IS NOT NULL",
            name="ck_bills_finalized_at",
        ),
        sa.CheckConstraint(
            "subtotal_amount >= 0",
            name="ck_bills_subtotal_amount_non_negative",
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name="ck_bills_total_amount_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_bills_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["menu_id"],
            ["menus.id"],
            name="fk_bills_menu_id_menus",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bills"),
    )
    op.create_index("ix_bills_user_id", "bills", ["user_id"])
    op.create_index("ix_bills_menu_id", "bills", ["menu_id"])

    op.create_table(
        "bill_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name_snapshot", sa.String(255), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column(
            "quantity",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="ck_bill_items_quantity_positive"),
        sa.CheckConstraint(
            "unit_price_snapshot >= 0",
            name="ck_bill_items_unit_price_snapshot_non_negative",
        ),
        sa.CheckConstraint(
            "line_total >= 0",
            name="ck_bill_items_line_total_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["bills.id"],
            name="fk_bill_items_bill_id_bills",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_id"],
            ["food_items.id"],
            name="fk_bill_items_food_item_id_food_items",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bill_items"),
    )
    op.create_index("ix_bill_items_bill_id", "bill_items", ["bill_id"])

    op.create_table(
        "bill_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "DISCOUNT",
                "SURCHARGE",
                "TAX",
                "SERVICE_CHARGE",
                "ROUNDING",
                name="bill_adjustment_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bill_id"],
            ["bills.id"],
            name="fk_bill_adjustments_bill_id_bills",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bill_adjustments"),
    )
    op.create_index(
        "ix_bill_adjustments_bill_id",
        "bill_adjustments",
        ["bill_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bill_adjustments_bill_id", table_name="bill_adjustments")
    op.drop_table("bill_adjustments")

    op.drop_index("ix_bill_items_bill_id", table_name="bill_items")
    op.drop_table("bill_items")

    op.drop_index("ix_bills_menu_id", table_name="bills")
    op.drop_index("ix_bills_user_id", table_name="bills")
    op.drop_table("bills")

    postgresql.ENUM(name="bill_adjustment_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="bill_status").drop(op.get_bind(), checkfirst=True)