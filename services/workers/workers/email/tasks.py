from workers.celery_app import app


@app.task(
    bind=True,
    name="workers.email.tasks.send_test_email",
    queue="email",
    max_retries=3,
    default_retry_delay=30,
)
def send_test_email(self, enquiry_id: str, to_email: str, subject: str, body: str):
    """
    Send a test email via Gmail SMTP.

    Placeholder — implementation added in email module sprint.

    Args:
        enquiry_id: UUID of the enquiry this email is associated with.
        to_email: Recipient email address.
        subject: Email subject line.
        body: Email body text.
    """
    # TODO: implement Gmail SMTP sending
    # TODO: write email_events record to PostgreSQL on success or failure
    raise NotImplementedError("send_test_email not yet implemented")
