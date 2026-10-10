"""Rotate the passwords of the seeded demo accounts.

The demo accounts created by scripts/seed_database.py all share the well-known
password ``DemoPass123``. That is fine for local testing but must not survive on
a public deployment, so this script replaces it with a fresh random password per
account and prints the new credentials exactly once.

Usage (from repo root):
    python scripts/rotate_demo_credentials.py                 # demo lawyers only
    python scripts/rotate_demo_credentials.py --include-citizens
    python scripts/rotate_demo_credentials.py --dry-run       # show targets only

Nothing is written to disk; copy the output somewhere safe before closing the
terminal. Re-running rotates the passwords again. Accounts that do not exist are
skipped, and no account is ever deleted.
"""

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import settings  # noqa: E402
from app.db.session import dispose_engine, session_scope  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402
from app.services.auth_service import hash_password  # noqa: E402

# Keep these in sync with scripts/seed_database.py.
DEMO_LAWYER_EMAILS = (
    "anita.sharma@example.com",
    "rahul.verma@example.com",
    "priya.nair@example.com",
    "vikram.singh@example.com",
    "meera.iyer@example.com",
)
DEMO_CITIZEN_EMAILS = (
    "rohan.gupta@example.com",
    "sneha.patel@example.com",
    "arjun.mehta@example.com",
)


def _generate_password() -> str:
    return secrets.token_urlsafe(12)


async def run(include_citizens: bool, dry_run: bool) -> None:
    if not settings.is_mysql_configured:
        print("ERROR: MySQL is not configured. Set MYSQL_HOST/USER/PASSWORD/DATABASE in .env.")
        sys.exit(1)

    emails = list(DEMO_LAWYER_EMAILS)
    if include_citizens:
        emails.extend(DEMO_CITIZEN_EMAILS)

    results: list[tuple[str, str]] = []
    skipped: list[str] = []

    async with session_scope() as db:
        users = UserRepository(db)
        for email in emails:
            account = await users.find_by_email(email)
            if account is None:
                skipped.append(email)
                continue
            if dry_run:
                results.append((email, "<dry-run>"))
                continue
            new_password = _generate_password()
            await users.update(
                str(account["_id"]), {"password_hash": hash_password(new_password)}
            )
            results.append((email, new_password))

    if dry_run:
        print("Dry run — the following accounts would be rotated:")
        for email, _ in results:
            print(f"  {email}")
    else:
        print("Rotated credentials (store these now; they are not saved anywhere):")
        print("")
        for email, password in results:
            print(f"  {email}  ->  {password}")
        print("")

    if skipped:
        print("Skipped (account not found):")
        for email in skipped:
            print(f"  {email}")

    print(f"Done. Rotated {len(results)} account(s), skipped {len(skipped)}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rotate the passwords of the seeded demo accounts."
    )
    parser.add_argument(
        "--include-citizens",
        action="store_true",
        help="Also rotate the demo citizen accounts (rohan/sneha/arjun).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the accounts that would be rotated without changing anything.",
    )
    args = parser.parse_args()

    async def _main() -> None:
        await run(args.include_citizens, args.dry_run)
        await dispose_engine()

    asyncio.run(_main())


if __name__ == "__main__":
    main()
