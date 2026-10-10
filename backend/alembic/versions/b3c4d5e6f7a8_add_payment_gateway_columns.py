"""add payment gateway columns

Revision ID: b3c4d5e6f7a8
Revises: a5b2c3d4e5f6
Create Date: 2026-10-10 09:30:00.000000

Razorpay order and capture identifiers are stored on the existing `payments`
row so a payment can be reconciled against the gateway. All three columns are
nullable, so legacy (mock) payments keep working untouched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a5b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _payment_columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("payments")}


def upgrade() -> None:
    """Add the gateway reconciliation columns."""
    columns = _payment_columns()
    if "payments" not in sa.inspect(op.get_bind()).get_table_names():
        return
    if "gateway_order_id" not in columns:
        op.add_column(
            "payments",
            sa.Column("gateway_order_id", sa.String(length=64), nullable=True),
        )
    if "gateway_payment_id" not in columns:
        op.add_column(
            "payments",
            sa.Column("gateway_payment_id", sa.String(length=64), nullable=True),
        )
    if "gateway_signature" not in columns:
        op.add_column(
            "payments",
            sa.Column("gateway_signature", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    """Drop the gateway reconciliation columns."""
    if "payments" not in sa.inspect(op.get_bind()).get_table_names():
        return
    columns = _payment_columns()
    if "gateway_signature" in columns:
        op.drop_column("payments", "gateway_signature")
    if "gateway_payment_id" in columns:
        op.drop_column("payments", "gateway_payment_id")
    if "gateway_order_id" in columns:
        op.drop_column("payments", "gateway_order_id")
