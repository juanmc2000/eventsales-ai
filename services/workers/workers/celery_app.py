import os

from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    "eventsales_workers",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "workers.email.tasks",
        "workers.inbox.tasks",
        "workers.enquiry.tasks",
        "workers.seed.tasks",
        "workers.dashboard.tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Queue definitions — one per POC background job type
    task_queues={
        "email": {},
        "inbox": {},
        "enquiry": {},
        "seed": {},
        "metrics": {},
    },
    task_default_queue="email",
)
