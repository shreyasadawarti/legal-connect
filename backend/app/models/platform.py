"""MongoDB data models and enums for the Legal Connect platform domain."""

from enum import Enum


class LegalCategory(str, Enum):
    FAMILY = "family"
    CRIMINAL = "criminal"
    CIVIL = "civil"
    CORPORATE = "corporate"
    PROPERTY = "property"
    TAX = "tax"
    LABOR = "labor"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    CONTRACT = "contract"
    PERSONAL_INJURY = "personal_injury"
    IMMIGRATION = "immigration"
    OTHER = "other"


class AppointmentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    NO_SHOW = "NO_SHOW"


class NotificationType(str, Enum):
    APPOINTMENT = "APPOINTMENT"
    REVIEW = "REVIEW"
    COMPLAINT = "COMPLAINT"
    SYSTEM = "SYSTEM"
    PAYMENT = "PAYMENT"


class ComplaintStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
