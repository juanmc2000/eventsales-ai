"""API endpoints for AI prompt runs and training examples.

Prompt run endpoints (read-only):
  GET  /api/v1/ai/prompt-runs          — paginated list with filters
  GET  /api/v1/ai/prompt-runs/{id}     — full detail (admin/debugging only)

Training example endpoints:
  POST /api/v1/ai/training-examples          — create a training example
  GET  /api/v1/ai/training-examples          — paginated list with filters
  GET  /api/v1/ai/training-examples/{id}     — single training example

These endpoints are for internal debugging and quality review.
They must not be exposed on the frontend or used by guest-facing flows.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.ai.repository import AIPromptRunRepository
from app.modules.ai.schemas import (
    PromptRunDetailOut,
    PromptRunListOut,
    PromptRunOut,
    TrainingExampleCreate,
    TrainingExampleListOut,
    TrainingExampleOut,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


def get_repo(db: Session = Depends(get_db)) -> AIPromptRunRepository:
    return AIPromptRunRepository(db)


def get_training_service(db: Session = Depends(get_db)):  # type: ignore[return]
    from app.modules.ai.service import TrainingExampleService
    return TrainingExampleService(db)


@router.get("/prompt-runs", response_model=PromptRunListOut)
def list_prompt_runs(
    enquiry_id: uuid.UUID | None = Query(default=None),
    restaurant_id: uuid.UUID | None = Query(default=None),
    persona_id: uuid.UUID | None = Query(default=None),
    prompt_key: str | None = Query(default=None),
    status: str | None = Query(default=None),
    validation_status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    repo: AIPromptRunRepository = Depends(get_repo),
) -> PromptRunListOut:
    """List AI prompt runs with optional filters.

    All filter parameters are optional and AND-combined.
    Results are ordered newest-first.
    """
    runs, total = repo.list_runs(
        enquiry_id=enquiry_id,
        restaurant_id=restaurant_id,
        persona_id=persona_id,
        prompt_key=prompt_key,
        status=status,
        validation_status=validation_status,
        skip=skip,
        limit=limit,
    )
    return PromptRunListOut(
        items=[PromptRunOut.model_validate(r) for r in runs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/prompt-runs/{prompt_run_id}", response_model=PromptRunDetailOut)
def get_prompt_run(
    prompt_run_id: uuid.UUID,
    repo: AIPromptRunRepository = Depends(get_repo),
) -> PromptRunDetailOut:
    """Return the full detail of a single prompt run.

    Includes rendered prompts and raw LLM response for debugging.
    This endpoint is intended for backend/admin use only.
    """
    run = repo.get_run(prompt_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Prompt run {prompt_run_id} not found")
    return PromptRunDetailOut.model_validate(run)


# ── Training example endpoints ────────────────────────────────────────────────


@router.post("/training-examples", response_model=TrainingExampleOut, status_code=201)
def create_training_example(
    data: TrainingExampleCreate,
    service=Depends(get_training_service),
) -> TrainingExampleOut:
    """Create a training example linked to an existing prompt run.

    The original_output is automatically populated from the run's parsed_response.
    Raises 404 if the prompt run does not exist.
    """
    try:
        example = service.create(data.model_dump())
        return TrainingExampleOut.model_validate(example)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/training-examples", response_model=TrainingExampleListOut)
def list_training_examples(
    prompt_key: str | None = Query(default=None),
    prompt_run_id: uuid.UUID | None = Query(default=None),
    approved_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service=Depends(get_training_service),
) -> TrainingExampleListOut:
    """List training examples with optional filters."""
    examples, total = service.list(
        prompt_key=prompt_key,
        prompt_run_id=prompt_run_id,
        approved_only=approved_only,
        skip=skip,
        limit=limit,
    )
    return TrainingExampleListOut(
        items=[TrainingExampleOut.model_validate(e) for e in examples],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/training-examples/{example_id}", response_model=TrainingExampleOut)
def get_training_example(
    example_id: uuid.UUID,
    service=Depends(get_training_service),
) -> TrainingExampleOut:
    """Return a single training example by ID."""
    example = service.get(example_id)
    if example is None:
        raise HTTPException(status_code=404, detail=f"Training example {example_id} not found")
    return TrainingExampleOut.model_validate(example)
