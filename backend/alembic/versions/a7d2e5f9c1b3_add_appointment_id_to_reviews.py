"""add appointment_id to reviews

Revision ID: a7d2e5f9c1b3
Revises: c4a1b7e9d2f0
Create Date: 2026-10-09 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d2e5f9c1b3'
down_revision: Union[str, Sequence[str], None] = 'c4a1b7e9d2f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tie each review to the appointment it reviews.

    Existing rows keep a NULL appointment_id (and MySQL permits repeated NULLs
    in a unique index), so no review data is lost. One review per appointment is
    now the rule; the previous one-review-per-lawyer constraint is removed so a
    citizen can review each completed appointment.
    """
    op.add_column(
        "reviews", sa.Column("appointment_id", sa.String(length=24), nullable=True)
    )
    op.create_foreign_key(
        "fk_reviews_appointment_id_appointments",
        "reviews",
        "appointments",
        ["appointment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_reviews_appointment_id", "reviews", ["appointment_id"]
    )
    op.create_index("ix_reviews_appointment_id", "reviews", ["appointment_id"])
    op.drop_constraint("uq_reviews_lawyer_reviewer", "reviews", type_="unique")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_unique_constraint(
        "uq_reviews_lawyer_reviewer", "reviews", ["lawyer_id", "reviewer_id"]
    )
    op.drop_index("ix_reviews_appointment_id", table_name="reviews")
    op.drop_constraint("uq_reviews_appointment_id", "reviews", type_="unique")
    op.drop_constraint(
        "fk_reviews_appointment_id_appointments", "reviews", type_="foreignkey"
    )
    op.drop_column("reviews", "appointment_id")
