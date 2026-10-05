"""MongoDB data models and enums for Legal Connect."""

from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    LAWYER = "lawyer"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"


class LawyerStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
