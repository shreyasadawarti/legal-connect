"""add chat blocks, per-user visibility, and extend complaints

Revision ID: 5ff3dbb02184
Revises: b1e2c3d4e5f6
Create Date: 2026-10-09 10:28:40.029516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ff3dbb02184'
down_revision: Union[str, Sequence[str], None] = 'b1e2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "conversation_participants",
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversation_participants",
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "user_blocks",
        sa.Column("blocker_id", sa.String(length=24), nullable=False),
        sa.Column("blocked_id", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("blocker_id", "blocked_id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
    )
    op.create_index(
        "ix_user_blocks_blocker_id", "user_blocks", ["blocker_id"], unique=False
    )
    op.create_index(
        "ix_user_blocks_blocked_id", "user_blocks", ["blocked_id"], unique=False
    )

    op.add_column(
        "complaints",
        sa.Column("target_user_id", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("conversation_id", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("category", sa.String(length=50), nullable=True),
    )
    op.create_foreign_key(
        "fk_complaints_target_user_id_users",
        "complaints",
        "users",
        ["target_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_complaints_conversation_id_conversations",
        "complaints",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_complaints_target_user_id", "complaints", ["target_user_id"], unique=False
    )
    op.create_index(
        "ix_complaints_conversation_id",
        "complaints",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_complaints_conversation_id", table_name="complaints")
    op.drop_index("ix_complaints_target_user_id", table_name="complaints")
    op.drop_constraint(
        "fk_complaints_conversation_id_conversations", "complaints", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_complaints_target_user_id_users", "complaints", type_="foreignkey"
    )
    op.drop_column("complaints", "category")
    op.drop_column("complaints", "conversation_id")
    op.drop_column("complaints", "target_user_id")

    op.drop_index("ix_user_blocks_blocked_id", table_name="user_blocks")
    op.drop_index("ix_user_blocks_blocker_id", table_name="user_blocks")
    op.drop_table("user_blocks")

    op.drop_column("conversation_participants", "cleared_at")
    op.drop_column("conversation_participants", "hidden_at")
