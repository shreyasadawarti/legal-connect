"""ORM row -> legacy document conversion.

Every repository returns plain dicts shaped exactly like the MongoDB documents
the old implementation produced. Centralising the conversion here guarantees
that a field is never accidentally renamed in one repository but not another,
and keeps the existing `app/schemas/` serializers working untouched.

Two conversions matter beyond plain attribute copying:

* Enums are emitted as their `.value` string (`UserRole.USER` -> `"user"`), which
  is what the HTTP responses have always contained.
* `availability` times come back from MySQL as `datetime.time` objects but were
  stored in MongoDB as `"HH:MM"` strings, so they are re-formatted.
"""

from datetime import time
from typing import Any, Optional

from app.db.compat import as_float
from app.db.models import (
    Appointment,
    AuditLog,
    Complaint,
    Conversation,
    Document,
    LawyerProfile,
    Message,
    Notification,
    Payment,
    Review,
    User,
)


def enum_value(value: Any) -> Any:
    """Return the stored string for an enum column, passing strings through."""
    if value is None:
        return None
    return getattr(value, "value", value)


def _time_str(value: Optional[time]) -> Optional[str]:
    return value.strftime("%H:%M") if value is not None else None


# Monetary and rating columns are DECIMAL in MySQL, so they arrive as
# `decimal.Decimal`. MongoDB stored them as JSON numbers, and Pydantic plus
# FastAPI's JSON encoder both expect numbers here -- `Decimal` would either fail
# validation or serialise as a string. Every such field goes through `as_float`
# so the response body is byte-identical to the MongoDB version.
def _money(value: Any) -> Optional[float]:
    return as_float(value)


def user_to_doc(row: User) -> dict[str, Any]:
    """Full internal user document, including `password_hash`.

    `serialize_user` in the user repository strips the hash before the document
    leaves the process; authentication needs it, the API must never see it.
    """
    return {
        "_id": row.id,
        "name": row.name,
        "email": row.email,
        "phone": row.phone,
        "password_hash": row.password_hash,
        "role": enum_value(row.role),
        "preferred_language": row.preferred_language,
        "city": row.city,
        "address": row.address,
        "bio": row.bio,
        "is_email_verified": bool(row.is_email_verified),
        "status": enum_value(row.status),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "last_login_at": row.last_login_at,
    }


def lawyer_profile_to_doc(row: LawyerProfile) -> dict[str, Any]:
    """Lawyer profile document with its four list fields rebuilt as plain lists.

    `position` keeps the original insertion order, so the React lawyer cards
    render the same sequence they always have.
    """
    return {
        "_id": row.id,
        "user_id": row.user_id,
        "bio": row.bio,
        "years_of_experience": row.years_of_experience,
        "hourly_rate": _money(row.hourly_rate),
        "city": row.city,
        "latitude": _money(row.latitude),
        "longitude": _money(row.longitude),
        "avg_rating": _money(row.avg_rating),
        "rating_count": row.rating_count,
        "verification_status": enum_value(row.verification_status),
        "is_verified": bool(row.is_verified),
        "rejection_reason": row.rejection_reason,
        "verification_document_id": row.verification_document_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "categories": [enum_value(c.category) for c in row.categories],
        "specializations": [s.value for s in row.specializations],
        "languages": [lang.value for lang in row.languages],
        "availability": [
            {
                "day_of_week": slot.day_of_week,
                "start_time": _time_str(slot.start_time),
                "end_time": _time_str(slot.end_time),
            }
            for slot in row.availability
        ],
    }


def appointment_to_doc(row: Appointment) -> dict[str, Any]:
    return {
        "_id": row.id,
        "lawyer_id": row.lawyer_id,
        "client_id": row.client_id,
        "category": enum_value(row.category),
        "start_time": row.start_time,
        "end_time": row.end_time,
        "description": row.description,
        "status": enum_value(row.status),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def conversation_to_doc(row: Conversation) -> dict[str, Any]:
    return {
        "_id": row.id,
        "type": row.type,
        "last_message": row.last_message,
        "last_message_at": row.last_message_at,
        "created_at": row.created_at,
        "participants": [p.user_id for p in row.participants],
    }


def message_to_doc(row: Message) -> dict[str, Any]:
    return {
        "_id": row.id,
        "conversation_id": row.conversation_id,
        "sender_id": row.sender_id,
        "recipient_id": row.recipient_id,
        "content": row.content,
        "message_type": row.message_type,
        "is_read": bool(row.is_read),
        "created_at": row.created_at,
    }


def document_to_doc(row: Document) -> dict[str, Any]:
    return {
        "_id": row.id,
        "owner_id": row.owner_id,
        "title": row.title,
        "original_name": row.original_name,
        "mime_type": row.mime_type,
        "size_bytes": row.size_bytes,
        "public_id": row.public_id,
        "resource_type": row.resource_type,
        "related_appointment_id": row.related_appointment_id,
        "doc_type": row.doc_type,
        "created_at": row.created_at,
        "shared_with": [s.user_id for s in row.shares],
    }


def notification_to_doc(row: Notification) -> dict[str, Any]:
    return {
        "_id": row.id,
        "user_id": row.user_id,
        "type": row.type,
        "title": row.title,
        "message": row.message,
        "data": row.data,
        "is_read": bool(row.is_read),
        "created_at": row.created_at,
    }


def review_to_doc(row: Review) -> dict[str, Any]:
    return {
        "_id": row.id,
        "lawyer_id": row.lawyer_id,
        "reviewer_id": row.reviewer_id,
        "rating": row.rating,
        "comment": row.comment,
        "created_at": row.created_at,
    }


def payment_to_doc(row: Payment) -> dict[str, Any]:
    return {
        "_id": row.id,
        "appointment_id": row.appointment_id,
        "payee_id": row.payee_id,
        "amount": _money(row.amount),
        "status": enum_value(row.status),
        "reference": row.reference,
        "created_at": row.created_at,
    }


def complaint_to_doc(row: Complaint) -> dict[str, Any]:
    return {
        "_id": row.id,
        "user_id": row.user_id,
        "subject": row.subject,
        "description": row.description,
        "related_appointment_id": row.related_appointment_id,
        "status": enum_value(row.status),
        "admin_note": row.admin_note,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def audit_log_to_doc(row: AuditLog) -> dict[str, Any]:
    return {
        "_id": row.id,
        "actor_id": row.actor_id,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "details": row.details,
        "created_at": row.created_at,
    }