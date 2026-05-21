"""Email delivery status constants.

These values are written to the email_events.status column in PostgreSQL.
They represent the full lifecycle of an outbound email send attempt.
"""


class EmailDeliveryStatus:
    # Draft created but no send attempted
    DRAFT = "draft"
    # Send was skipped because SMTP credentials are not configured
    DISABLED = "disabled"
    # Send request accepted and enqueued in Celery (not yet processed)
    QUEUED = "queued"
    # Celery task is actively sending via SMTP
    SENDING = "sending"
    # SMTP accepted the message
    SENT = "sent"
    # SMTP rejected or connection failed
    FAILED = "failed"

    ALL: tuple[str, ...] = (DRAFT, DISABLED, QUEUED, SENDING, SENT, FAILED)
