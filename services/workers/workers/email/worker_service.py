"""EmailWorkerService — orchestrates SMTP send and delivery status updates.

Called by the Celery task. Keeps business logic out of the task function.
Uses a direct SQLAlchemy session; does not depend on the FastAPI API service.
"""
import logging
import os
import uuid
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from workers.email.smtp_provider import is_smtp_configured, send_email

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://eventsales:eventsales@localhost:5432/eventsales"
)

_engine = None
_SessionLocal = None


def _get_session_factory() -> sessionmaker:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = create_engine(_DATABASE_URL, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Delivery status constants (duplicated here to avoid cross-service imports) ─

_STATUS_SENDING = "sending"
_STATUS_SENT = "sent"
_STATUS_FAILED = "failed"
_STATUS_DISABLED = "disabled"

# Statuses that are terminal — do not retry
_TERMINAL_STATUSES = {_STATUS_SENT, _STATUS_DISABLED}


class EmailWorkerService:
    """Orchestrates the send attempt and writes status updates to email_events."""

    def execute(self, *, event_id: str) -> None:
        """
        Execute a single email send attempt for the given event_id.

        Idempotent: if the event is already SENT or DISABLED, this is a no-op.
        """
        with get_db_session() as db:
            # Fetch the event
            row = db.execute(
                text(
                    "SELECT id, status, to_address, subject, body "
                    "FROM email_events WHERE id = :id"
                ),
                {"id": event_id},
            ).fetchone()

            if not row:
                logger.error("EmailEvent %s not found — skipping", event_id)
                return

            event_status = row.status

            # Idempotency guard
            if event_status in _TERMINAL_STATUSES:
                logger.info(
                    "EmailEvent %s is already %s — skipping", event_id, event_status
                )
                return

            # Check SMTP
            if not is_smtp_configured():
                db.execute(
                    text(
                        "UPDATE email_events SET status = :status, error = :error "
                        "WHERE id = :id"
                    ),
                    {
                        "status": _STATUS_DISABLED,
                        "error": "SMTP not configured",
                        "id": event_id,
                    },
                )
                logger.warning("EmailEvent %s marked DISABLED — SMTP not configured", event_id)
                return

            # Mark as SENDING
            db.execute(
                text("UPDATE email_events SET status = :status WHERE id = :id"),
                {"status": _STATUS_SENDING, "id": event_id},
            )
            db.commit()

        # ── Attempt SMTP (outside the session to release the DB lock) ─────────
        to_address = row.to_address
        subject = row.subject or "Re: Your Event Enquiry"
        body = row.body or ""

        try:
            message_id = send_email(
                to_address=to_address, subject=subject, body=body
            )
            self._update_status(event_id, _STATUS_SENT, message_id=message_id)
            logger.info("EmailEvent %s → SENT (message_id=%s)", event_id, message_id)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._update_status(event_id, _STATUS_FAILED, error=error)
            logger.error("EmailEvent %s → FAILED: %s", event_id, error)
            raise

    def _update_status(
        self,
        event_id: str,
        status: str,
        *,
        message_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with get_db_session() as db:
            db.execute(
                text(
                    "UPDATE email_events "
                    "SET status = :status, message_id = :message_id, error = :error "
                    "WHERE id = :id"
                ),
                {
                    "status": status,
                    "message_id": message_id,
                    "error": error,
                    "id": event_id,
                },
            )
