"""Alembic migration environment for EventSales AI.

This env.py connects to the database using the application settings
(DATABASE_URL from environment / .env file) and runs migrations
against the SQLAlchemy Base metadata.

Import all model modules below the "Model imports" section so that
Alembic's autogenerate can detect schema changes.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make app/ importable when running alembic from services/api/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base  # noqa: F401 — Base must be imported for metadata

# ─── Model imports ────────────────────────────────────────────────────────────
# Import every model module here so that Base.metadata is fully populated
# before autogenerate runs.  Add a new import for each DATA-xxx issue.
#
# from app.modules.restaurants.models import Restaurant  # DATA-003
# from app.modules.personas.models import Persona        # DATA-003
# (add more as modules are implemented)

# ─── Alembic config ───────────────────────────────────────────────────────────

config = context.config

# Override sqlalchemy.url with the value from application settings so that
# credentials are never stored in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configure Python logging from alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object that autogenerate inspects.
target_metadata = Base.metadata


# ─── Offline migrations ───────────────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Run migrations without a live database connection.

    Emits SQL to stdout.  Useful for reviewing what would be applied.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ─── Online migrations ────────────────────────────────────────────────────────


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
