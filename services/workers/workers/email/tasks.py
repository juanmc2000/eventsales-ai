"""Celery task: send a draft email via Gmail SMTP.

The task delegates all business logic to EmailWorkerService.
Retries up to 3 times for transient SMTP errors (connection failures,
timeouts) with exponential back-off. Permanent failures (auth errors,
SMTP DISABLED state) are not retried.
"""
import logging

from workers.celery_app import app
from workers.email.worker_service import EmailWorkerService

logger = logging.getLogger(__name__)

# Exceptions that warrant a retry (transient network / server issues)
_RETRYABLE = (
    ConnectionRefusedError,
    ConnectionResetError,
    TimeoutError,
    OSError,
)


@app.task(
    bind=True,
    name="workers.email.tasks.send_draft_email",
    queue="email",
    max_retries=3,
    default_retry_delay=30,
)
def send_draft_email(self, event_id: str) -> dict:
    """
    Send a queued draft email and update email_events delivery status.

    Args:
        event_id: UUID string of the email_events row to process.

    Returns:
        Dict with event_id and final status string.

    Raises:
        celery.exceptions.Retry: on transient SMTP errors (up to max_retries).
    """
    logger.info("send_draft_email: starting event_id=%s (attempt %d)", event_id, self.request.retries + 1)

    svc = EmailWorkerService()
    try:
        svc.execute(event_id=event_id)
    except _RETRYABLE as exc:
        logger.warning(
            "send_draft_email: transient error for event_id=%s — retrying: %s",
            event_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    except Exception as exc:
        # Non-retryable (auth failure, etc.) — status already written to DB
        logger.error(
            "send_draft_email: permanent failure for event_id=%s: %s", event_id, exc
        )
        return {"event_id": event_id, "status": "failed"}

    return {"event_id": event_id, "status": "sent"}
