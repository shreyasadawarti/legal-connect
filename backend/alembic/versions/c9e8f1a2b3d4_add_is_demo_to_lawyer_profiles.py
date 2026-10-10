"""add is_demo to lawyer profiles

Revision ID: c9e8f1a2b3d4
Revises: b3c4d5e6f7a8
Create Date: 2026-10-10 10:00:00.000000

Seeded demo lawyers are bookable (they must stay `ACTIVE`), so a separate flag is
needed to tell them apart from real, admin-verified lawyers in the UI. The column
defaults to 0 so every existing profile stays "real" unless the backfill below
explicitly marks the demo accounts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c9e8f1a2b3d4'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The demo accounts created by scripts/seed_database.py. Backfilling by email is
# safe and idempotent: it only ever sets the flag on rows that are absent.
DEMO_LAWYER_EMAILS = (
    "anita.sharma@example.com",
    "rahul.verma@example.com",
    "priya.nair@example.com",
    "vikram.singh@example.com",
    "meera.iyer@example.com",
)


def _profile_columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("lawyer_profiles")}


def upgrade() -> None:
    """Add the demo flag and mark the seeded demo lawyers."""
    if "lawyer_profiles" not in sa.inspect(op.get_bind()).get_table_names():
        return
    if "is_demo" not in _profile_columns():
        op.add_column(
            "lawyer_profiles",
            sa.Column(
                "is_demo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    emails = ", ".join(f"'{email}'" for email in DEMO_LAWYER_EMAILS)
    op.execute(
        "UPDATE lawyer_profiles AS p "
        "JOIN users AS u ON u.id = p.user_id "
        f"SET p.is_demo = 1 WHERE u.email IN ({emails})"
    )


def downgrade() -> None:
    """Drop the demo flag."""
    if "lawyer_profiles" not in sa.inspect(op.get_bind()).get_table_names():
        return
    if "is_demo" in _profile_columns():
        op.drop_column("lawyer_profiles", "is_demo")
