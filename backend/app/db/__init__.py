"""Database package for Legal Connect.

Deliberately minimal: only the declarative base is re-exported here so that
importing `app.db` can never create an import cycle with `app.db.session`.
Import the engine helpers from `app.db.session` and the ORM classes from
`app.db.models`.
"""

from app.db.base import NAMING_CONVENTION, Base

__all__ = ["Base", "NAMING_CONVENTION"]