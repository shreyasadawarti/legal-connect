"""backfill review appointment links

Revision ID: e1f2a3b4c5d6
Revises: a7d2e5f9c1b3
Create Date: 2026-10-09 13:00:00.000000

Reviews created before `reviews.appointment_id` existed are orphaned (NULL),
so the per-appointment "reviewed" flag can never recognise them. This one-time
data migration links each such review to the completed appointment it most
likely belongs to: the citizen's appointment with the same lawyer that was
completed closest to (and not after) the review's creation time, falling back
to the earliest completed appointment. Existing reviews, ratings and
appointments are preserved; only NULL appointment_id values are filled in.
"""
from collections import defaultdict
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'a7d2e5f9c1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pick_appointment(
    review_created: datetime,
    candidates: list[tuple[str, datetime]],
    used: set[str],
) -> str | None:
    """The completed appointment closest before the review, else the earliest."""
    unused = [(aid, upd) for aid, upd in candidates if aid not in used]
    if not unused:
        return None
    before = [
        (aid, upd)
        for aid, upd in unused
        if upd is not None and review_created is not None and upd <= review_created
    ]
    if before:
        return max(before, key=lambda item: item[1])[0]
    return min(unused, key=lambda item: (item[1] is None, item[1] or datetime.min))[0]


def upgrade() -> None:
    """Link legacy (appointment_id IS NULL) reviews to their appointment."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, reviewer_id, lawyer_id, created_at FROM reviews "
            "WHERE appointment_id IS NULL ORDER BY created_at, id"
        )
    ).fetchall()
    if not rows:
        return

    groups: dict[tuple[str, str], list[tuple[str, datetime]]] = defaultdict(list)
    for review_id, reviewer_id, lawyer_id, created_at in rows:
        groups[(reviewer_id, lawyer_id)].append((review_id, created_at))

    for (reviewer_id, lawyer_id), group in groups.items():
        candidates = [
            (row[0], row[1])
            for row in bind.execute(
                sa.text(
                    "SELECT id, updated_at FROM appointments "
                    "WHERE client_id = :reviewer AND lawyer_id = :lawyer "
                    "AND status = 'COMPLETED'"
                ),
                {"reviewer": reviewer_id, "lawyer": lawyer_id},
            ).fetchall()
        ]
        used: set[str] = set()
        for review_id, created_at in sorted(
            group, key=lambda item: (item[1] or datetime.min, item[0])
        ):
            appointment_id = _pick_appointment(created_at, candidates, used)
            if appointment_id is None:
                continue
            bind.execute(
                sa.text("UPDATE reviews SET appointment_id = :aid WHERE id = :rid"),
                {"aid": appointment_id, "rid": review_id},
            )
            used.add(appointment_id)


def downgrade() -> None:
    """No-op: the appointment_id column is owned by the parent migration."""
    return None
