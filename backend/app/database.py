import logging

from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger("legalconnect.database")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    from app.repositories.appointment_repository import AppointmentRepository
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.repositories.complaint_repository import ComplaintRepository
    from app.repositories.conversation_repository import ConversationRepository
    from app.repositories.document_repository import DocumentRepository
    from app.repositories.lawyer_repository import LawyerRepository
    from app.repositories.message_repository import MessageRepository
    from app.repositories.notification_repository import NotificationRepository
    from app.repositories.payment_repository import PaymentRepository
    from app.repositories.review_repository import ReviewRepository
    from app.repositories.user_repository import UserRepository

    repos = [
        UserRepository,
        LawyerRepository,
        AppointmentRepository,
        NotificationRepository,
        ComplaintRepository,
        ReviewRepository,
        PaymentRepository,
        DocumentRepository,
        AuditLogRepository,
        ConversationRepository,
        MessageRepository,
    ]
    for repo in repos:
        try:
            await repo(db).ensure_indexes()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to ensure indexes for %s: %s", repo.__name__, exc)

    try:
        from app.services.chat_service import ChatService

        chat = ChatService(ConversationRepository(db), MessageRepository(db))
        merged = await chat.merge_duplicate_conversations()
        if merged:
            logger.info("Merged %d duplicate conversations", merged)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to merge duplicate conversations: %s", exc)


def get_database() -> AsyncIOMotorDatabase | None:
    """
    Return the active MongoDB database, or None if MongoDB is not configured.
    The application must NOT crash when MongoDB is unavailable; routes should
    surface a clear configuration error instead.
    """
    return _db


async def connect_to_mongo() -> None:
    global _client, _db
    if not settings.is_mongodb_configured:
        logger.warning(
            "MONGODB_URI is not configured. Database features are disabled. "
            "Add MONGODB_URI to your .env file."
        )
        return
    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
        # Force a connection to verify reachability.
        await _client.admin.command("ping")
        _db = _client[settings.mongodb_database]
        try:
            await _ensure_indexes(_db)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to ensure indexes: %s", exc)
        logger.info("Connected to MongoDB Atlas: %s", settings.mongodb_database)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to connect to MongoDB: %s", exc)
        _client = None
        _db = None


async def close_mongo_connection() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
