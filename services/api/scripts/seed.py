"""POC seed data script.

Run from services/api/:
    python scripts/seed.py

Or from the project root:
    PYTHONPATH=services/api python services/api/scripts/seed.py

Requires:
- PostgreSQL running (docker-compose up -d)
- Alembic migrations applied (alembic upgrade head)
- Python venv active with requirements installed
"""

import sys
import os

# Ensure app/ is importable when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.modules.shared.seed_data import run_seed


def main() -> None:
    print("EventSales AI — POC seed data")
    print("=" * 40)

    db = SessionLocal()
    try:
        counts = run_seed(db)
        print("Seed complete. Record counts:")
        for table, count in counts.items():
            print(f"  {table}: {count}")
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
