"""add auth security columns to users

Revision ID: a5b2c3d4e5f6
Revises: 3f774b2b69db
Create Date: 2026-10-10 09:10:00.000000

Additive auth hardening on `users`:

- `auth_version` — bumped on every password change/reset. Access and refresh
  tokens embed the version they were issued under, and the auth dependency
  rejects tokens whose version no longer matches, so existing sessions are
  invalidated after a password change without a server-side blocklist.
- `reset_token_hash` / `reset_token_expires_at` — the password-reset flow now
  mails a cryptographically random, single-use token whose SHA-256 hash and
  expiry are stored here; the row is cleared once used, so a token cannot be
  replayed.

All three are nullable or defaulted and no existing rows are modified.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

import app.db.types

# revision identifiers, used by Alembic.
revision: str = 'a5b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3f774b2b69db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the three users columns idempotently."""
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("users")}

    if "auth_version" not in columns:
        op.add_column(
            "users",
            sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"),
        )
    if "reset_token_hash" not in columns:
        op.add_column(
            "users",
            sa.Column("reset_token_hash", mysql.CHAR(length=64), nullable=True),
        )
    if "reset_token_expires_at" not in columns:
        op.add_column(
            "users",
            sa.Column("reset_token_expires_at", app.db.types.UTCDateTime(), nullable=True),
        )


def downgrade() -> None:
    """Drop the three auth columns."""
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("users")}

    for name in ("reset_token_expires_at", "reset_token_hash", "auth_version"):
        if name in columns:
            op.drop_column("users", name)