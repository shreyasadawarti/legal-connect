"""add missing complaint columns (schema drift repair)

Revision ID: f3b4c5d6e7f8
Revises: e1f2a3b4c5d6
Create Date: 2026-10-09 15:00:00.000000

Some environments applied `5ff3dbb02184` before its complaints block was
finalised, so `complaints.target_user_id`, `complaints.conversation_id` and
`complaints.category` (plus their foreign keys and indexes) are missing even
though `alembic_version` is past that revision. Every complaint insert/select
then fails with `Unknown column`, which breaks report submission and the admin
complaints list.

This migration adds only what is absent, using the exact names from
`5ff3dbb02184`, so a drifted database converges with a clean one. On a database
where that revision already applied, all checks pass and the upgrade is a no-op.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TARGET_FK = "fk_complaints_target_user_id_users"
_CONVERSATION_FK = "fk_complaints_conversation_id_conversations"
_TARGET_IX = "ix_complaints_target_user_id"
_CONVERSATION_IX = "ix_complaints_conversation_id"


def upgrade() -> None:
    """Add the complaint columns/FKs/indexes that are absent."""
    insp = sa.inspect(op.get_bind())

    columns = {c["name"] for c in insp.get_columns("complaints")}
    if "target_user_id" not in columns:
        op.add_column(
            "complaints",
            sa.Column("target_user_id", sa.String(length=24), nullable=True),
        )
    if "conversation_id" not in columns:
        op.add_column(
            "complaints",
            sa.Column("conversation_id", sa.String(length=24), nullable=True),
        )
    if "category" not in columns:
        op.add_column(
            "complaints",
            sa.Column("category", sa.String(length=50), nullable=True),
        )

    insp = sa.inspect(op.get_bind())
    foreign_keys = {fk["name"] for fk in insp.get_foreign_keys("complaints")}
    if _TARGET_FK not in foreign_keys:
        op.create_foreign_key(
            _TARGET_FK,
            "complaints",
            "users",
            ["target_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if _CONVERSATION_FK not in foreign_keys:
        op.create_foreign_key(
            _CONVERSATION_FK,
            "complaints",
            "conversations",
            ["conversation_id"],
            ["id"],
            ondelete="SET NULL",
        )

    insp = sa.inspect(op.get_bind())
    indexes = {ix["name"] for ix in insp.get_indexes("complaints")}
    if _TARGET_IX not in indexes:
        op.create_index(_TARGET_IX, "complaints", ["target_user_id"], unique=False)
    if _CONVERSATION_IX not in indexes:
        op.create_index(
            _CONVERSATION_IX, "complaints", ["conversation_id"], unique=False
        )


def downgrade() -> None:
    """Drop the complaint columns/FKs/indexes only if present."""
    insp = sa.inspect(op.get_bind())

    foreign_keys = {fk["name"] for fk in insp.get_foreign_keys("complaints")}
    if _CONVERSATION_FK in foreign_keys:
        op.drop_constraint(_CONVERSATION_FK, "complaints", type_="foreignkey")
    if _TARGET_FK in foreign_keys:
        op.drop_constraint(_TARGET_FK, "complaints", type_="foreignkey")

    insp = sa.inspect(op.get_bind())
    indexes = {ix["name"] for ix in insp.get_indexes("complaints")}
    if _CONVERSATION_IX in indexes:
        op.drop_index(_CONVERSATION_IX, table_name="complaints")
    if _TARGET_IX in indexes:
        op.drop_index(_TARGET_IX, table_name="complaints")

    insp = sa.inspect(op.get_bind())
    columns = {c["name"] for c in insp.get_columns("complaints")}
    if "category" in columns:
        op.drop_column("complaints", "category")
    if "conversation_id" in columns:
        op.drop_column("complaints", "conversation_id")
    if "target_user_id" in columns:
        op.drop_column("complaints", "target_user_id")
