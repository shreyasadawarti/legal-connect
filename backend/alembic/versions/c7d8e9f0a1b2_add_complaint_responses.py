"""add admin complaint responses (reporter and reported)

Revision ID: c7d8e9f0a1b2
Revises: f3b4c5d6e7f8
Create Date: 2026-10-09 16:30:00.000000

Admins reply to a complaint in two directions: one message for the reporter
(`complaints.user_id`) and one for the reported party (`complaints.target_user_id`).
Each response carries its own timestamp so a recipient can see when the admin
answered them. All four columns are nullable -- existing rows and complaints
without a reported party simply leave them empty. Idempotent like `f3b4c5d6e7f8`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'f3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = (
    ("reporter_response", sa.Text()),
    ("reporter_responded_at", sa.DateTime(timezone=True)),
    ("reported_response", sa.Text()),
    ("reported_responded_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    """Add the two-way response columns if they are absent."""
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("complaints")}
    for name, col_type in _COLUMNS:
        if name not in existing:
            op.add_column("complaints", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    """Drop the response columns only if present."""
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("complaints")}
    for name, _ in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("complaints", name)
