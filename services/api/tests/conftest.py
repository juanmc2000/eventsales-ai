"""pytest configuration for the EventSales AI backend test suite.

Test categories:
  smoke (no DB)       — schema validation, import checks, business logic
  unit (no DB)        — isolated service/repository logic with mocks
  integration (DB)    — tests that require a live PostgreSQL instance

Run smoke and unit tests (default, no DB needed):
    cd services/api
    pytest -m "not integration"

Run all tests including integration (requires docker-compose up -d + alembic upgrade head):
    cd services/api
    pytest
"""

import sys
import os

# Ensure app/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
