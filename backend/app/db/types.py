"""Custom column types.

`UTCDateTime` is the important one. The previous MongoDB implementation stored
timezone-aware UTC datetimes, so every datetime the API returned was serialised
with an explicit offset (e.g. `2026-01-05T10:00:00+00:00`) and the React frontend
parsed them correctly.

MySQL `DATETIME` has no timezone, so a naive value would be serialised without an
offset and `new Date(...)` in the browser would silently reinterpret it as local
time -- shifting every appointment time in the UI. `UTCDateTime` therefore stores
naive UTC in the database and always hands SQLAlchemy a timezone-aware UTC value
back, which keeps the API output byte-identical to the MongoDB version.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.dialects.mysql import DATETIME, JSON


class UTCDateTime(TypeDecorator):
    """DATETIME(6) that is always timezone-aware UTC on the Python side."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        # MySQL DATETIME(fsp=6) keeps microseconds, matching the millisecond
        # precision the API has always exposed. The generic DateTime class has no
        # `fsp` argument, so the dialect-specific type is required here.
        if dialect.name == "mysql":
            return dialect.type_descriptor(DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


# Free-form payloads (notification `data`, audit `details`) map cleanly onto
# MySQL JSON columns.
JSONDict = JSON