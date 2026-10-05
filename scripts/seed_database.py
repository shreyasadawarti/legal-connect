"""Seed the Legal Connect database with realistic demo data.

Usage (from repo root):
    python scripts/seed_database.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import settings  # noqa: E402
from app.database import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.models.platform import (  # noqa: E402
    AppointmentStatus,
    LegalCategory,
    PaymentStatus,
)
from app.models.user import LawyerStatus, UserRole  # noqa: E402
from app.repositories.appointment_repository import AppointmentRepository  # noqa: E402
from app.repositories.complaint_repository import ComplaintRepository  # noqa: E402
from app.repositories.lawyer_repository import LawyerRepository  # noqa: E402
from app.repositories.payment_repository import PaymentRepository  # noqa: E402
from app.repositories.review_repository import ReviewRepository  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402
from app.services.auth_service import hash_password  # noqa: E402

LAWYERS = [
    {
        "name": "Anita Sharma",
        "email": "anita.sharma@example.com",
        "city": "New Delhi",
        "categories": [LegalCategory.FAMILY, LegalCategory.CIVIL],
        "specializations": ["Divorce", "Child custody"],
        "languages": ["Hindi", "English"],
        "years_of_experience": 12,
        "hourly_rate": 2500.0,
        "bio": "Family law specialist with over a decade of practice in matrimonial and custody matters.",
        "latitude": 28.6139,
        "longitude": 77.2090,
    },
    {
        "name": "Rahul Verma",
        "email": "rahul.verma@example.com",
        "city": "Mumbai",
        "categories": [LegalCategory.CORPORATE, LegalCategory.CONTRACT],
        "specializations": ["Mergers", "Contracts"],
        "languages": ["Hindi", "English", "Marathi"],
        "years_of_experience": 9,
        "hourly_rate": 4000.0,
        "bio": "Corporate counsel helping startups and SMEs with contracts, compliance and M&A.",
        "latitude": 19.0760,
        "longitude": 72.8777,
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@example.com",
        "city": "Bengaluru",
        "categories": [LegalCategory.INTELLECTUAL_PROPERTY, LegalCategory.TAX],
        "specializations": ["Trademarks", "Patents"],
        "languages": ["English", "Malayalam", "Kannada"],
        "years_of_experience": 7,
        "hourly_rate": 3500.0,
        "bio": "IP attorney focusing on trademarks, patents and technology law.",
        "latitude": 12.9716,
        "longitude": 77.5946,
    },
    {
        "name": "Vikram Singh",
        "email": "vikram.singh@example.com",
        "city": "Jaipur",
        "categories": [LegalCategory.PROPERTY, LegalCategory.CIVIL],
        "specializations": ["Real estate", "Land disputes"],
        "languages": ["Hindi", "English"],
        "years_of_experience": 15,
        "hourly_rate": 2200.0,
        "bio": "Property and civil litigation attorney with extensive land-dispute experience.",
        "latitude": 26.9124,
        "longitude": 75.7873,
    },
    {
        "name": "Meera Iyer",
        "email": "meera.iyer@example.com",
        "city": "Chennai",
        "categories": [LegalCategory.LABOR, LegalCategory.PERSONAL_INJURY],
        "specializations": ["Employment", "Workplace injury"],
        "languages": ["English", "Tamil"],
        "years_of_experience": 6,
        "hourly_rate": 2000.0,
        "bio": "Employment and labor law advocate for workers and small employers.",
        "latitude": 13.0827,
        "longitude": 80.2707,
    },
]

USERS = [
    {"name": "Rohan Gupta", "email": "rohan.gupta@example.com", "city": "New Delhi"},
    {"name": "Sneha Patel", "email": "sneha.patel@example.com", "city": "Mumbai"},
    {"name": "Arjun Mehta", "email": "arjun.mehta@example.com", "city": "Bengaluru"},
]

DEFAULT_PASSWORD = "DemoPass123"


async def _get_or_create_user(users: UserRepository, name: str, email: str, role: UserRole, city: str):
    existing = await users.find_by_email(email)
    if existing:
        return existing["id"]
    created = await users.create(
        name=name,
        email=email,
        password_hash=hash_password(DEFAULT_PASSWORD),
        role=role,
    )
    await users.mark_email_verified(str(created["_id"]))
    if city:
        await users.update(str(created["_id"]), {"city": city})
    return str(created["_id"])


async def run() -> None:
    if not settings.is_mongodb_configured:
        print("ERROR: MONGODB_URI is not configured. Add it to .env and retry.")
        sys.exit(1)

    await connect_to_mongo()
    db = get_database()
    if db is None:
        print("ERROR: could not connect to MongoDB Atlas.")
        sys.exit(1)

    users = UserRepository(db)
    lawyers_repo = LawyerRepository(db)
    appointments = AppointmentRepository(db)
    payments = PaymentRepository(db)
    complaints = ComplaintRepository(db)
    reviews = ReviewRepository(db)

    lawyer_ids = []
    for idx, spec in enumerate(LAWYERS):
        uid = await _get_or_create_user(
            users, spec["name"], spec["email"], UserRole.LAWYER, spec["city"]
        )
        profile = await lawyers_repo.upsert(
            uid,
            {
                "bio": spec["bio"],
                "years_of_experience": spec["years_of_experience"],
                "categories": [c.value for c in spec["categories"]],
                "specializations": spec["specializations"],
                "languages": spec["languages"],
                "hourly_rate": spec["hourly_rate"],
                "city": spec["city"],
                "latitude": spec["latitude"],
                "longitude": spec["longitude"],
            },
        )
        await lawyers_repo.set_verification_status(uid, LawyerStatus.ACTIVE)
        lawyer_ids.append(uid)
        print(f"Seeded lawyer #{idx + 1}: {spec['name']} ({uid})")

    user_ids = []
    for idx, spec in enumerate(USERS):
        uid = await _get_or_create_user(
            users, spec["name"], spec["email"], UserRole.USER, spec["city"]
        )
        user_ids.append(uid)
        print(f"Seeded user #{idx + 1}: {spec['name']} ({uid})")

    base = datetime.now(timezone.utc)
    appointment_data = [
        (user_ids[0], lawyer_ids[0], LegalCategory.FAMILY, AppointmentStatus.COMPLETED),
        (user_ids[1], lawyer_ids[1], LegalCategory.CONTRACT, AppointmentStatus.CONFIRMED),
        (user_ids[2], lawyer_ids[2], LegalCategory.INTELLECTUAL_PROPERTY, AppointmentStatus.PENDING),
        (user_ids[0], lawyer_ids[3], LegalCategory.PROPERTY, AppointmentStatus.COMPLETED),
        (user_ids[1], lawyer_ids[4], LegalCategory.LABOR, AppointmentStatus.COMPLETED),
    ]

    created_appointments = []
    for n, (client_id, lawyer_id, category, status) in enumerate(appointment_data):
        start = (base + timedelta(days=n, hours=2)).replace(
            minute=0, second=0, microsecond=0
        )
        end = start + timedelta(hours=1)
        appt = await appointments.create(
            lawyer_id=lawyer_id,
            client_id=client_id,
            category=category.value,
            start_time=start,
            end_time=end,
            description=f"Demo consultation #{n + 1}",
        )
        appt_id = str(appt["_id"])
        created_appointments.append((appt_id, client_id, lawyer_id, status))
        await appointments.update_status(appt_id, status)
        print(f"Seeded appointment #{n + 1} ({appt_id}) status={status.value}")

    for n, (appt_id, client_id, lawyer_id, status) in enumerate(created_appointments):
        if status == AppointmentStatus.COMPLETED:
            payment = await payments.create(
                appointment_id=appt_id,
                payee_id=client_id,
                amount=float(1500 + n * 250),
                status=PaymentStatus.PAID,
            )
            print(f"Seeded payment for appointment #{n + 1} (ref {payment['reference']})")

    complaint = await complaints.create(
        user_id=user_ids[0],
        subject="Delayed response",
        description="My lawyer took several days to respond to my query.",
        related_appointment_id=None,
    )
    print(f"Seeded complaint ({complaint['_id']})")

    for n, (appt_id, client_id, lawyer_id, status) in enumerate(created_appointments):
        if status == AppointmentStatus.COMPLETED:
            review = await reviews.create(
                lawyer_id=lawyer_id,
                reviewer_id=client_id,
                rating=4 + (n % 2),
                comment="Good consultation, clear guidance.",
            )
            print(f"Seeded review for appointment #{n + 1} (rating {review['rating']})")

    print("\nSeed complete.")
    print(f"Use default password '{DEFAULT_PASSWORD}' for all seeded accounts.")

    await close_mongo_connection()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
