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
from app.db.session import (  # noqa: E402
    dispose_engine,
    ensure_database_exists,
    session_scope,
    upgrade_schema,
)
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
        "profile_picture": "/lawyers/anita-sharma.svg",
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
        "profile_picture": "/lawyers/rahul-verma.svg",
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
        "profile_picture": "/lawyers/priya-nair.svg",
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
        "profile_picture": "/lawyers/vikram-singh.svg",
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
        "profile_picture": "/lawyers/meera-iyer.svg",
        "latitude": 13.0827,
        "longitude": 80.2707,
    },
]

USERS = [
    {"name": "Rohan Gupta", "email": "rohan.gupta@example.com", "city": "New Delhi"},
    {"name": "Sneha Patel", "email": "sneha.patel@example.com", "city": "Mumbai"},
    {"name": "Arjun Mehta", "email": "arjun.mehta@example.com", "city": "Bengaluru"},
]

# Lawyer accounts that predate the LAWYERS list above and so are never created by
# this script. Their demo portrait is applied in place to an account that already
# exists, which keeps this file free of any insert or delete for them.
LEGACY_LAWYER_PORTRAITS = [
    ("pankaj@gmail.com", "/lawyers/pankaj-tripathi.svg"),
]

DEFAULT_PASSWORD = "DemoPass123"


async def _get_or_create_user(
    users: UserRepository,
    name: str,
    email: str,
    role: UserRole,
    city: str,
    profile_picture: str | None = None,
):
    existing = await users.find_by_email(email)
    if existing:
        uid = str(existing["_id"])
        # Fill in the demo portrait only when the account has none, so a
        # database seeded before profile pictures existed picks one up on the
        # next run without ever discarding a picture someone uploaded.
        if profile_picture and not existing.get("profile_picture_url"):
            await users.update(uid, {"profile_picture_url": profile_picture})
        return uid
    created = await users.create(
        name=name,
        email=email,
        password_hash=hash_password(DEFAULT_PASSWORD),
        role=role,
    )
    await users.mark_email_verified(str(created["_id"]))
    fields: dict = {}
    if city:
        fields["city"] = city
    if profile_picture:
        fields["profile_picture_url"] = profile_picture
    if fields:
        await users.update(str(created["_id"]), fields)
    return str(created["_id"])


async def run() -> None:
    if not settings.is_mysql_configured:
        print("ERROR: MySQL is not configured. Set MYSQL_HOST/USER/PASSWORD/DATABASE in .env.")
        sys.exit(1)

    await ensure_database_exists()
    # Bring the schema up to head rather than relying on create_all, so a fresh
    # checkout can be seeded in one step and the migration history stays correct.
    upgrade_schema()

    async with session_scope() as db:
        await _seed(db)
    await dispose_engine()


async def _seed(db) -> None:
    users = UserRepository(db)
    lawyers_repo = LawyerRepository(db)
    appointments = AppointmentRepository(db)
    payments = PaymentRepository(db)
    complaints = ComplaintRepository(db)
    reviews = ReviewRepository(db)

    lawyer_ids = []
    for idx, spec in enumerate(LAWYERS):
        uid = await _get_or_create_user(
            users,
            spec["name"],
            spec["email"],
            UserRole.LAWYER,
            spec["city"],
            spec.get("profile_picture"),
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

    for email, picture in LEGACY_LAWYER_PORTRAITS:
        account = await users.find_by_email(email)
        if account is None:
            print(f"Skipped portrait for absent lawyer account: {email}")
            continue
        if account.get("profile_picture_url"):
            print(f"Kept existing picture for lawyer: {email}")
            continue
        await users.update(str(account["_id"]), {"profile_picture_url": picture})
        print(f"Applied demo portrait: {account['name']} ({email})")

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
            # `reviews` has a unique constraint on (lawyer_id, reviewer_id), and a
            # re-run books fresh appointments for the same lawyer/client pairs, so
            # the insert has to be skipped when that review already exists.
            existing_review = await reviews.find_by_user_and_lawyer(client_id, lawyer_id)
            if existing_review is None:
                review = await reviews.create(
                    lawyer_id=lawyer_id,
                    reviewer_id=client_id,
                    rating=4 + (n % 2),
                    comment="Good consultation, clear guidance.",
                )
                print(f"Seeded review for appointment #{n + 1} (rating {review['rating']})")
            # The router recalculates the cached rating after each review; the seed
            # bypasses that, so `avg_rating` would stay 0.00 and search-by-rating
            # and the leaderboard would show the wrong numbers.
            stats = await reviews.rating_average(lawyer_id)
            await lawyers_repo.update_rating(lawyer_id, stats["avg"], stats["count"])

    print("\nSeed complete.")
    print(f"Use default password '{DEFAULT_PASSWORD}' for all seeded accounts.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
