"""SQLAlchemy ORM models for Legal Connect.

These replace the eleven MongoDB collections. Design notes:

* Public identifiers are 24-character strings (`CHAR(24)`), matching the
  ObjectId values the API has always exposed.
* Fields that MongoDB stored as embedded arrays (`categories`, `languages`,
  `specializations`, `availability`, `participants`, `shared_with`) become real
  child or join tables rather than JSON blobs, so they are queryable and
  referenceable. `position` columns preserve the original list order, because
  the API returns these lists verbatim and the frontend renders them in order.
* Free-form payloads (`notifications.data`, `audit_logs.details`) stay JSON,
  because their shape is genuinely open-ended.
* Foreign keys are declared only where the application guarantees the target row
  exists. Where an identifier arrives straight from user input without
  validation -- `documents.related_appointment_id`,
  `complaints.related_appointment_id`, `audit_logs.entity_id` -- the column is a
  plain indexed string, exactly as MongoDB treated it. Adding a foreign key
  there would introduce new 500 errors that the working app does not produce.
"""

from datetime import datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import CHAR, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.compat import new_id, utcnow
from app.db.types import JSONDict, UTCDateTime
from app.models.platform import (
    AppointmentStatus,
    ComplaintStatus,
    LegalCategory,
    PaymentStatus,
    RevenueEventType,
)
from app.models.user import LawyerStatus, UserRole, UserStatus


def enum_type(python_enum: type, name: str) -> SAEnum:
    """Native MySQL ENUM that stores the enum *value*, not its member name.

    SQLAlchemy defaults to persisting `.name`, which would write `"USER"` instead
    of `"user"` and break every existing status comparison in the codebase.
    """
    return SAEnum(
        python_enum,
        values_callable=lambda e: [m.value for m in e],
        name=name,
        validate_strings=True,
    )


ID = CHAR(24)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_role", "role"), Index("ix_users_status", "status"))

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_type(UserRole, "user_role"), nullable=False
    )
    preferred_language: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_picture_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    profile_picture_public_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reset_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        enum_type(UserStatus, "user_status"), nullable=False, default=UserStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)


class LawyerProfile(Base):
    __tablename__ = "lawyer_profiles"
    __table_args__ = (
        Index("ix_lawyer_profiles_verification_status", "verification_status"),
        Index("ix_lawyer_profiles_city", "city"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    years_of_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hourly_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False, default=Decimal("0.00")
    )
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 7), nullable=True)
    avg_rating: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=Decimal("0.00")
    )
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_status: Mapped[LawyerStatus] = mapped_column(
        enum_type(LawyerStatus, "lawyer_status"),
        nullable=False,
        default=LawyerStatus.PENDING_VERIFICATION,
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Marks seeded demo profiles so the UI can distinguish them from real,
    # verified lawyers without changing their bookable status.
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Documents own the Cloudinary asset; MySQL stores only this reference.
    verification_document_id: Mapped[Optional[str]] = mapped_column(
        ID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(lazy="selectin")
    categories: Mapped[list["LawyerCategory"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="LawyerCategory.position",
        lazy="selectin",
    )
    specializations: Mapped[list["LawyerSpecialization"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="LawyerSpecialization.position",
        lazy="selectin",
    )
    languages: Mapped[list["LawyerLanguage"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="LawyerLanguage.position",
        lazy="selectin",
    )
    availability: Mapped[list["LawyerAvailability"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="LawyerAvailability.position",
        lazy="selectin",
    )


class LawyerCategory(Base):
    __tablename__ = "lawyer_categories"
    __table_args__ = (Index("ix_lawyer_categories_category", "category"),)

    lawyer_profile_id: Mapped[str] = mapped_column(
        ID,
        ForeignKey("lawyer_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[LegalCategory] = mapped_column(
        enum_type(LegalCategory, "legal_category"), nullable=False
    )

    profile: Mapped[LawyerProfile] = relationship(back_populates="categories")


class LawyerSpecialization(Base):
    __tablename__ = "lawyer_specializations"
    __table_args__ = (Index("ix_lawyer_specializations_value", "value"),)

    lawyer_profile_id: Mapped[str] = mapped_column(
        ID,
        ForeignKey("lawyer_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(120), nullable=False)

    profile: Mapped[LawyerProfile] = relationship(back_populates="specializations")


class LawyerLanguage(Base):
    __tablename__ = "lawyer_languages"
    __table_args__ = (Index("ix_lawyer_languages_value", "value"),)

    lawyer_profile_id: Mapped[str] = mapped_column(
        ID,
        ForeignKey("lawyer_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(60), nullable=False)

    profile: Mapped[LawyerProfile] = relationship(back_populates="languages")


class LawyerAvailability(Base):
    __tablename__ = "lawyer_availability"
    __table_args__ = (
        Index("ix_lawyer_availability_profile_day", "lawyer_profile_id", "day_of_week"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    lawyer_profile_id: Mapped[str] = mapped_column(
        ID, ForeignKey("lawyer_profiles.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    profile: Mapped[LawyerProfile] = relationship(back_populates="availability")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_lawyer_id", "lawyer_id"),
        Index("ix_appointments_client_id", "client_id"),
        Index("ix_appointments_lawyer_status", "lawyer_id", "status"),
        Index("ix_appointments_start_time", "start_time"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    lawyer_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[LegalCategory] = mapped_column(
        enum_type(LegalCategory, "legal_category"), nullable=False
    )
    start_time = mapped_column(UTCDateTime, nullable=False)
    end_time = mapped_column(UTCDateTime, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        enum_type(AppointmentStatus, "appointment_status"),
        nullable=False,
        default=AppointmentStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="direct")
    # Sorted, joined participant IDs. UNIQUE reproduces the "one direct
    # conversation per pair" rule that `find_between` enforced in MongoDB.
    pair_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    last_message: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    last_message_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    participants: Mapped[list["ConversationParticipant"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationParticipant.position",
        lazy="selectin",
    )


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (Index("ix_conversation_participants_user_id", "user_id"),)

    conversation_id: Mapped[str] = mapped_column(
        ID, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    hidden_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    cleared_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="participants")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index(
            "ix_messages_unread",
            "conversation_id",
            "recipient_id",
            "is_read",
        ),
        Index(
            "ix_messages_undelivered",
            "conversation_id",
            "recipient_id",
            "delivered_at",
        ),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        ID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # NULL until the recipient's client has actually received it. Distinct from
    # `is_read`: delivered means "available on the recipient's device", read means
    # "the recipient opened and saw it".
    delivered_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_owner_created", "owner_id", "created_at"),
        Index("ix_documents_public_id", "public_id"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    public_id: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False, default="raw")
    related_appointment_id: Mapped[Optional[str]] = mapped_column(ID, nullable=True)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False, default="general")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    shares: Mapped[list["DocumentShare"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentShare.position",
        lazy="selectin",
    )


class DocumentShare(Base):
    __tablename__ = "document_shares"
    __table_args__ = (Index("ix_document_shares_user_id", "user_id"),)

    document_id: Mapped[str] = mapped_column(
        ID, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Mirrors MongoDB's `shared_with` array, where order was insertion order.
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped[Document] = relationship(back_populates="shares")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[dict]] = mapped_column(JSONDict, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        # One review per appointment. NULL for legacy reviews created before
        # reviews were tied to an appointment; MySQL allows repeated NULLs in a
        # unique index, so those rows are unaffected.
        UniqueConstraint("appointment_id", name="uq_reviews_appointment_id"),
        Index("ix_reviews_lawyer_id", "lawyer_id"),
        Index("ix_reviews_appointment_id", "appointment_id"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    lawyer_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    appointment_id: Mapped[Optional[str]] = mapped_column(
        ID, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_payee_id", "payee_id"),
        Index("ix_payments_appointment_id", "appointment_id"),
        Index("ix_payments_status", "status"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    appointment_id: Mapped[str] = mapped_column(
        ID, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False
    )
    payee_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        enum_type(PaymentStatus, "payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    gateway_order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gateway_payment_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gateway_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class RevenueEvent(Base):
    __tablename__ = "revenue_events"
    __table_args__ = (
        Index("ix_revenue_events_created", "created_at"),
        UniqueConstraint(
            "event_type", "reference_id", name="uq_revenue_events_event_reference"
        ),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    event_type: Mapped[RevenueEventType] = mapped_column(
        enum_type(RevenueEventType, "revenue_event_type"),
        nullable=False,
    )
    reference_id: Mapped[str] = mapped_column(ID, nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        Index("ix_complaints_reporter_created", "user_id", "created_at"),
        Index("ix_complaints_status", "status"),
        Index("ix_complaints_target_user", "target_user_id"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    related_appointment_id: Mapped[Optional[str]] = mapped_column(ID, nullable=True)
    target_user_id: Mapped[Optional[str]] = mapped_column(
        ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        ID, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[ComplaintStatus] = mapped_column(
        enum_type(ComplaintStatus, "complaint_status"),
        nullable=False,
        default=ComplaintStatus.OPEN,
    )
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reporter_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reporter_responded_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True
    )
    reported_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reported_responded_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        Index("ix_audit_logs_entity_type", "entity_type"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True, default=new_id)
    actor_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(ID, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONDict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)




class UserBlock(Base):
    __tablename__ = "user_blocks"
    __table_args__ = (
        Index("ix_user_blocks_blocker_id", "blocker_id"),
        Index("ix_user_blocks_blocked_id", "blocked_id"),
        UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
    )
    blocker_id: Mapped[str] = mapped_column(ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id: Mapped[str] = mapped_column(ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Free-form settings blob: notification toggles, interests, privacy flags.
    data: Mapped[Optional[dict]] = mapped_column(JSONDict, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow
    )












