"""Create or update an administrator account.

Usage (from repo root):
    python scripts/create_admin.py --name "Admin" --email admin@example.com --password "ChangeMe123"

Alternatively set ADMIN_NAME / ADMIN_EMAIL / ADMIN_PASSWORD in the environment.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import settings  # noqa: E402
from app.database import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.models.user import UserRole  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402
from app.services.auth_service import hash_password  # noqa: E402


async def run(name: str, email: str, password: str) -> None:
    email = email.strip().lower()

    if not settings.is_mongodb_configured:
        print("ERROR: MONGODB_URI is not configured. Add it to .env and retry.")
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: password must be at least 8 characters.")
        sys.exit(1)

    await connect_to_mongo()
    db = get_database()
    if db is None:
        print("ERROR: could not connect to MongoDB Atlas.")
        sys.exit(1)

    users = UserRepository(db)
    existing = await users.find_by_email(email)

    if existing:
        await users.update(
            str(existing["_id"]),
            {"role": UserRole.ADMIN.value, "is_email_verified": True},
        )
        print(f"Updated existing user '{existing['_id']}' to admin role.")
    else:
        created = await users.create(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
        )
        await users.mark_email_verified(str(created["_id"]))
        print(f"Created admin user with id '{created['_id']}'.")

    print(f"Admin email: {email}")
    print("Done.")

    await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an admin account.")
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "Administrator"))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", ""))
    args = parser.parse_args()

    if not args.email or not args.password:
        print("ERROR: --email and --password are required.")
        parser.print_help()
        sys.exit(1)

    asyncio.run(run(args.name, args.email, args.password))


if __name__ == "__main__":
    main()
