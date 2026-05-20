from workers.celery_app import app


@app.task(
    bind=True,
    name="workers.seed.tasks.generate_seed_data",
    queue="seed",
    max_retries=1,
)
def generate_seed_data(self):
    """
    Populate the database with POC fake data.

    Placeholder — implementation added in seed data sprint.

    Seeded data includes:
    - 4 test restaurants (The Garden Table, Harbour & Hearth, Lumiere Dining Room, Maison Aurelia)
    - 3 default personas (Corporate, Social/Casual, Luxury/Ultra Luxury)
    - Pricing rules per restaurant
    - 1 year of fake demand events (bank holidays, sports, theatre, graduation weeks, etc.)
    - Fake enquiries across all statuses

    This task is idempotency-aware: it checks for existing records before inserting.
    """
    # TODO: seed restaurants
    # TODO: seed personas and restaurant_personas
    # TODO: seed pricing rules
    # TODO: seed demand events
    # TODO: seed fake enquiries
    raise NotImplementedError("generate_seed_data not yet implemented")
