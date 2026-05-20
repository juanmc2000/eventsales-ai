from workers.celery_app import app


@app.task(
    bind=True,
    name="workers.inbox.tasks.read_inbox",
    queue="inbox",
    max_retries=3,
    default_retry_delay=60,
)
def read_inbox(self):
    """
    Poll the Gmail inbox via IMAP and queue processing for new messages.

    Placeholder — implementation added in email module sprint.

    Each unread message triggers a process_inbound_email task on the enquiry queue.
    Messages are marked as processed to prevent duplicate enquiry creation.
    """
    # TODO: connect to Gmail IMAP
    # TODO: fetch unread messages
    # TODO: queue workers.enquiry.tasks.process_inbound_email for each new message
    # TODO: mark messages as processed
    raise NotImplementedError("read_inbox not yet implemented")
