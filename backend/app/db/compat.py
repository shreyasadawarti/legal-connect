"""Compatibility helpers that keep the API response shape unchanged.

The repositories historically returned raw MongoDB documents and every
serializer in `app/schemas/` was written against that shape -- most importantly
`serialize_user`, `serialize_appointment`, `serialize_message`,
`serialize_conversation` and `serialize_document`, which each do
`doc["id"] = str(doc.pop("_id"))` and then read sibling fields such as
`lawyer_id` / `owner_id` / `participants` directly.

To keep the HTTP contract byte-identical, the SQLAlchemy repositories convert
each ORM row back into the equivalent document dict before returning it. Routers,
schemas, services and the WebSocket layer therefore need no changes.

Two rules hold throughout:
  * `_id` is the 24-character public ID string, never an integer.
  * Every foreign key is a string, never an integer.
"""

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional, Sequence, TypeVar

# --- ObjectId-compatible identifier generation -----------------------------
#
# Identifiers stay 24 hexadecimal characters, exactly the shape the MongoDB
# implementation exposed. That keeps API responses, JWT `sub` claims, stored
# document references and any previously exported data compatible, while still
# allowing a MongoDB export to be imported later with its original IDs intact.
#
# Layout mirrors bson.ObjectId: 4-byte timestamp, 5-byte per-process random
# value, 3-byte counter. The counter keeps IDs monotonic within a process, which
# is what let the previous code order and paginate by identifier.

_PROCESS_RANDOM = os.urandom(5)
_counter_lock = threading.Lock()
_counter = int.from_bytes(os.urandom(3), "big")


def new_id() -> str:
    """Return a new 24-character hex identifier, monotonic within this process."""
    global _counter
    with _counter_lock:
        _counter = (_counter + 1) & 0xFFFFFF
        counter = _counter
    timestamp = int(time.time())
    raw = (
        timestamp.to_bytes(4, "big")
        + _PROCESS_RANDOM
        + counter.to_bytes(3, "big")
    )
    return raw.hex()


def utcnow() -> datetime:
    """Timezone-aware UTC now, matching the datetimes the API used to return."""
    return datetime.now(timezone.utc)


def id_to_datetime(value: Any) -> Optional[datetime]:
    """Recover the creation time embedded in an ObjectId-style identifier.

    `list_for_conversation` paginates with a `before=<message id>` cursor by
    reading the timestamp out of the previous identifier, which is exactly what
    `bson.ObjectId.generation_time` did. Because `new_id()` writes the current
    time into the first four bytes in the same layout, the same trick keeps
    working. Returns None for anything that is not a 24-character hex string,
    which the callers treat as "no cursor".
    """
    if not isinstance(value, str) or len(value) != 24:
        return None
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return None
    return datetime.fromtimestamp(int.from_bytes(raw[:4], "big"), tz=timezone.utc)


# --- shared query helpers ---------------------------------------------------

T = TypeVar("T")


def offset(page: int, page_size: int) -> int:
    return max(page - 1, 0) * page_size


def page_result(
    items: Sequence[Any], total: int, page: int, page_size: int
) -> dict[str, Any]:
    """Build the pagination envelope every list endpoint already returns."""
    return {"items": list(items), "total": total, "page": page, "page_size": page_size}


def as_float(value: Any) -> Optional[float]:
    """Convert DECIMAL columns to float.

    Required, not cosmetic: DECIMAL comes back as `decimal.Decimal`, which
    `json.dumps` cannot encode. The WebSocket manager serialises every outgoing
    frame with `json.dumps(..., default=str)`, so an unconverted Decimal would
    reach the browser as a *string* and break the chat UI.
    """
    if value is None:
        return None
    return float(value)


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    """Normalise a JSON column to a plain dict (never None for absent values)."""
    if value is None:
        return None
    return dict(value)