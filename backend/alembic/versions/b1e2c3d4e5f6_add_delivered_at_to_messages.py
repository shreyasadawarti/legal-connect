"""add delivered_at to messages

Chat receipts distinguish three states: sent (the row exists), delivered (the
recipient's client received it), and read (``is_read``). Only the last one was
modelled, so a WhatsApp-style double grey tick had nothing to read from.

``delivered_at`` is nullable with no default, so every existing message stays
valid and simply reads as "sent" until its recipient next comes online -- which
is exactly the truthful state for messages sent into the old system.

Revision ID: b1e2c3d4e5f6
Revises: a7c31e9b4d20
Create Date: 2026-10-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.types

# revision identifiers, used by Alembic.
revision: str = 'b1e2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'a7c31e9b4d20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'messages',
        sa.Column('delivered_at', app.db.types.UTCDateTime(), nullable=True),
    )
    op.create_index(
        'ix_messages_undelivered',
        'messages',
        ['conversation_id', 'recipient_id', 'delivered_at'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_messages_undelivered', table_name='messages')
    op.drop_column('messages', 'delivered_at')
