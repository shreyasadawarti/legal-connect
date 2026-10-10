"""add revenue_events ledger

Revision ID: 3f774b2b69db
Revises: c7d8e9f0a1b2
Create Date: 2026-10-10 08:19:22.460584

Admin revenue is recorded as one `revenue_events` row per source (`registration`
or `commission`) with a unique `(event_type, reference_id)` key, so replaying a
hook or re-running this migration can never double-count.

The backfill "replays" the existing records: every user registered as a citizen
or lawyer becomes a 10000.00 registration event (keyed by user id) and every
COMPLETED appointment with a positive hourly rate becomes a 5x earnings
commission event (keyed by appointment id). Both use MySQL `INSERT IGNORE`, so
rows already present are left untouched and the migration is safe to re-run.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

import app.db.types

# revision identifiers, used by Alembic.
revision: str = '3f774b2b69db'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the revenue ledger and backfill historical income."""
    if "revenue_events" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('revenue_events',
        sa.Column('id', mysql.CHAR(length=24), nullable=False),
        sa.Column('event_type', sa.Enum('registration', 'commission', name='revenue_event_type'), nullable=False),
        sa.Column('reference_id', mysql.CHAR(length=24), nullable=False),
        sa.Column('amount', mysql.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('created_at', app.db.types.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_revenue_events')),
        sa.UniqueConstraint('event_type', 'reference_id', name='uq_revenue_events_event_reference')
        )
        op.create_index('ix_revenue_events_created', 'revenue_events', ['created_at'], unique=False)

    op.execute(
        """
        INSERT IGNORE INTO revenue_events (id, event_type, reference_id, amount, created_at)
        SELECT LEFT(MD5(CONCAT('registration', users.id)), 24),
               'registration',
               users.id,
               10000.00,
               users.created_at
        FROM users
        WHERE users.role IN ('user', 'lawyer')
        """
    )
    op.execute(
        """
        INSERT IGNORE INTO revenue_events (id, event_type, reference_id, amount, created_at)
        SELECT LEFT(MD5(CONCAT('commission', a.id)), 24),
               'commission',
               a.id,
               ROUND(5.00 * lp.hourly_rate * (TIMESTAMPDIFF(SECOND, a.start_time, a.end_time) / 3600.00), 2),
               a.updated_at
        FROM appointments a
        JOIN lawyer_profiles lp ON lp.user_id = a.lawyer_id
        WHERE a.status = 'COMPLETED'
          AND lp.hourly_rate > 0
        """
    )


def downgrade() -> None:
    """Drop the revenue ledger."""
    if "revenue_events" in sa.inspect(op.get_bind()).get_table_names():
        indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("revenue_events")}
        if "ix_revenue_events_created" in indexes:
            op.drop_index(op.f('ix_revenue_events_created'), table_name='revenue_events')
        op.drop_table('revenue_events')