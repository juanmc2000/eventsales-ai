"""Repository for AI prompt run trace persistence.

Provides create and update operations for ai_prompt_runs and
ai_training_examples.  All database writes go through this repository.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.ai.models import AIPromptRun, AITrainingExample


class AIPromptRunRepository:
    """Persistence layer for ai_prompt_runs and ai_training_examples."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_run(self, data: dict[str, Any]) -> AIPromptRun:
        """Insert a new ai_prompt_run row and flush.

        The caller is responsible for committing the session.
        """
        run = AIPromptRun(id=uuid.uuid4(), **data)
        self._db.add(run)
        self._db.flush()
        return run

    def update_run(self, run_id: uuid.UUID, updates: dict[str, Any]) -> AIPromptRun:
        """Apply field updates to an existing run row and flush."""
        run = self._db.get(AIPromptRun, run_id)
        if run is None:
            raise ValueError(f"AIPromptRun {run_id} not found")
        for key, value in updates.items():
            setattr(run, key, value)
        self._db.flush()
        return run

    def get_run(self, run_id: uuid.UUID) -> AIPromptRun | None:
        """Return the run row for the given ID, or None."""
        return self._db.get(AIPromptRun, run_id)

    def create_training_example(self, run_id: uuid.UUID, tenant_id: str | None, prompt_key: str | None) -> AITrainingExample:
        """Insert a training example row linked to the given run."""
        example = AITrainingExample(
            id=uuid.uuid4(),
            prompt_run_id=run_id,
            tenant_id=tenant_id,
            prompt_key=prompt_key,
            approved_for_training=False,
        )
        self._db.add(example)
        self._db.flush()
        return example
