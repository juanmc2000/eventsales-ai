from workers.celery_app import app


@app.task(
    bind=True,
    name="workers.dashboard.tasks.refresh_dashboard_metrics",
    queue="metrics",
    max_retries=2,
    default_retry_delay=15,
)
def refresh_dashboard_metrics(self, restaurant_id: str = None):
    """
    Recompute and cache dashboard KPI metrics from PostgreSQL.

    Placeholder — implementation added in dashboard module sprint.

    Args:
        restaurant_id: Optional UUID. If provided, refresh metrics for one restaurant only.
                       If None, refresh portfolio-level metrics.

    Results are written to insight_snapshots in PostgreSQL and optionally cached in Redis.
    Redis cache is always rebuildable from PostgreSQL — it is not the source of truth.
    """
    # TODO: query enquiry and booking aggregates from PostgreSQL
    # TODO: write insight_snapshots records
    # TODO: optionally cache results in Redis with TTL
    raise NotImplementedError("refresh_dashboard_metrics not yet implemented")
