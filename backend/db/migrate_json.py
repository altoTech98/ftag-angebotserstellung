"""
One-time migration script: JSON files → SQLite/PostgreSQL.
Reads existing JSON data and inserts it into the database.
Run with: python -m db.migrate_json
"""

import json
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from db.engine import sync_engine, Base
from db.models import User, Feedback

logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def migrate_users(session: Session) -> int:
    """Migrate users.json → users table."""
    users_file = DATA_DIR / "users.json"
    if not users_file.exists():
        return 0

    users_data = json.loads(users_file.read_text(encoding="utf-8"))
    count = 0
    for u in users_data:
        existing = session.query(User).filter_by(email=u["email"]).first()
        if existing:
            continue
        user = User(
            email=u["email"],
            password_hash=u["password_hash"],
            role=u.get("role", "user"),
        )
        session.add(user)
        count += 1

    return count


def migrate_feedback(session: Session) -> int:
    """Migrate matching_feedback.json → feedback table."""
    feedback_file = DATA_DIR / "matching_feedback.json"
    if not feedback_file.exists():
        return 0

    try:
        feedback_data = json.loads(feedback_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    entries = feedback_data if isinstance(feedback_data, list) else feedback_data.get("entries", [])
    count = 0
    for entry in entries:
        fb = Feedback(
            feedback_type=entry.get("type", "correction"),
            requirement_text=entry.get("requirement_text", ""),
            requirement_fields=entry.get("requirement_fields"),
            original_product=entry.get("original_product"),
            corrected_product=entry.get("confirmed_product") or entry.get("corrected_product"),
            match_status_was=entry.get("match_status_was"),
        )
        session.add(fb)
        count += 1

    return count


def run_migration():
    """Execute full JSON → DB migration."""
    print("Creating tables...")
    Base.metadata.create_all(sync_engine)

    with Session(sync_engine) as session:
        users_count = migrate_users(session)
        print(f"  Users migrated: {users_count}")

        feedback_count = migrate_feedback(session)
        print(f"  Feedback entries migrated: {feedback_count}")

        session.commit()
        print("Migration complete.")


if __name__ == "__main__":
    run_migration()
