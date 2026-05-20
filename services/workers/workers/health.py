from workers.celery_app import app


@app.task(name="workers.health.ping", queue="email")
def ping():
    """Health check task. Returns 'pong' to confirm the worker is running."""
    return "pong"
