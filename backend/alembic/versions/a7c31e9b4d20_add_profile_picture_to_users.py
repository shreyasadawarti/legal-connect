"""add profile picture to users

Citizens, lawyers and admins all upload a profile picture, so the columns live on
``users`` rather than on the lawyer-only profile table. One column pair therefore
covers every role without a second avatar field anywhere.

``profile_picture_public_id`` keeps the Cloudinary reference so a replaced image
can be deleted instead of being orphaned on every upload, mirroring how
``documents.public_id`` already tracks its asset.

Nullable with no default, so every existing row is valid without a data migration
and both columns read as absent until a picture is set.

Revision ID: a7c31e9b4d20
Revises: fef6641d722c
Create Date: 2026-10-05 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c31e9b4d20'
down_revision: Union[str, Sequence[str], None] = 'fef6641d722c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('profile_picture_url', sa.String(500), nullable=True))
    op.add_column(
        'users', sa.Column('profile_picture_public_id', sa.String(255), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'profile_picture_public_id')
    op.drop_column('users', 'profile_picture_url')