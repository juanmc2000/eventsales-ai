from workers.celery_app import app


@app.task(
    bind=True,
    name="workers.enquiry.tasks.process_inbound_email",
    queue="enquiry",
    max_retries=3,
    default_retry_delay=30,
)
def process_inbound_email(self, raw_email: dict):
    """
    Parse a raw inbound email message and create an enquiry record in PostgreSQL.

    Placeholder — implementation added in enquiry module sprint.

    Args:
        raw_email: Dict containing sender, subject, body, received_at, external_message_id.

    This task is idempotency-aware: it checks for an existing enquiry with the same
    external_message_id before inserting to prevent duplicates.
    """
    # TODO: extract enquiry fields from raw_email
    # TODO: check for existing enquiry with same external_message_id
    # TODO: write enquiry record to PostgreSQL
    # TODO: trigger persona selection and pricing recommendation
    raise NotImplementedError("process_inbound_email not yet implemented")
