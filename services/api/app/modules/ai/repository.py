"""Repository for AI prompt run trace persistence.

Provides create, update, and read operations for ai_prompt_runs and
ai_training_examples.  All database writes go through this repository.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
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

    def list_runs(
        self,
        enquiry_id: uuid.UUID | None = None,
        restaurant_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
        prompt_key: str | None = None,
        status: str | None = None,
        validation_status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AIPromptRun], int]:
        """Return a paginated list of prompt runs and the total count.

        All filters are optional and additive (AND conditions).
        Results are ordered by created_at descending.
        """
        stmt = select(AIPromptRun)
        count_stmt = select(AIPromptRun)

        if enquiry_id is not None:
            stmt = stmt.where(AIPromptRun.enquiry_id == enquiry_id)
            count_stmt = count_stmt.where(AIPromptRun.enquiry_id == enquiry_id)
        if restaurant_id is not None:
            stmt = stmt.where(AIPromptRun.restaurant_id == restaurant_id)
            count_stmt = count_stmt.where(AIPromptRun.restaurant_id == restaurant_id)
        if persona_id is not None:
            stmt = stmt.where(AIPromptRun.persona_id == persona_id)
            count_stmt = count_stmt.where(AIPromptRun.persona_id == persona_id)
        if prompt_key is not None:
            stmt = stmt.where(AIPromptRun.prompt_key == prompt_key)
            count_stmt = count_stmt.where(AIPromptRun.prompt_key == prompt_key)
        if status is not None:
            stmt = stmt.where(AIPromptRun.status == status)
            count_stmt = count_stmt.where(AIPromptRun.status == status)
        if validation_status is not None:
            stmt = stmt.where(AIPromptRun.validation_status == validation_status)
            count_stmt = count_stmt.where(AIPromptRun.validation_status == validation_status)

        total = len(self._db.scalars(count_stmt).all())
        runs = list(
            self._db.scalars(
                stmt.order_by(AIPromptRun.created_at.desc()).offset(skip).limit(limit)
            ).all()
        )
        return runs, total

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
