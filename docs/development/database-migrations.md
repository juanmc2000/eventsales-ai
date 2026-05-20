# Database Migrations

EventSales AI uses [Alembic](https://alembic.sqlalchemy.org/) for database schema versioning.

All migration commands are run from `services/api/`.

---

## Prerequisites

- PostgreSQL running locally (via `docker-compose up -d`)
- Python virtual environment activated: `source .venv-eventsales-ai/bin/activate`
- Dependencies installed: `pip install -r requirements.txt`

---

## Common Commands

### Apply all pending migrations

```bash
cd services/api
alembic upgrade head
```

### Roll back one migration

```bash
cd services/api
alembic downgrade -1
```

### Roll back to a specific revision

```bash
cd services/api
alembic downgrade <revision-id>
```

### Check current revision

```bash
cd services/api
alembic current
```

### Show migration history

```bash
cd services/api
alembic history --verbose
```

### Generate a new migration (autogenerate from model changes)

```bash
cd services/api
alembic revision --autogenerate -m "short description of change"
```

Review the generated file in `alembic/versions/` before applying it.
Autogenerate does not detect every change — always review the diff.

### Generate an empty migration (manual)

```bash
cd services/api
alembic revision -m "short description of change"
```

---

## Adding a New Model

1. Create the SQLAlchemy model in `services/api/app/modules/<module>/models.py`.
2. Import the model in `services/api/alembic/env.py` under the `# Model imports` section.
3. Generate a migration: `alembic revision --autogenerate -m "<description>"`.
4. Review the generated migration file.
5. Apply: `alembic upgrade head`.

---

## Configuration

- `alembic.ini` — Alembic configuration (located at `services/api/alembic.ini`)
- `alembic/env.py` — migration environment; reads `DATABASE_URL` from application settings
- `alembic/versions/` — migration scripts (one file per migration)

The database URL is read from application settings (`app.core.config.settings.database_url`),
which defaults to the `DATABASE_URL` environment variable or the `.env` file.
Credentials are never stored in `alembic.ini`.

---

## Docker Compose

The local PostgreSQL instance is defined in `docker-compose.yml`.

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Stop services
docker-compose down
```

---

## POC Constraints

- Migrations are for local development only during the POC phase.
- No cloud database migrations are configured.
- No multi-tenant schema isolation is implemented at the database level (deferred to MVP).
