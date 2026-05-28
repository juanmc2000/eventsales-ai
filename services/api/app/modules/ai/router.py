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
    PromptExperimentCreate,
    PromptExperimentListOut,
    PromptExperimentOut,
    PromptExperimentRunCreate,
    PromptExperimentRunListOut,
    PromptExperimentRunOut,
    PromptExperimentRunUpdate,
    PromptRunDetailOut,
    PromptRunListOut,
    PromptRunOut,
    PromptRunReviewCreate,
    PromptRunReviewListOut,
    PromptRunReviewOut,
    PromptRunReviewUpdate,
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


def get_experiment_service(db: Session = Depends(get_db)):  # type: ignore[return]
    from app.modules.ai.service import PromptExperimentService
    return PromptExperimentService(db)


def get_review_service(db: Session = Depends(get_db)):  # type: ignore[return]
    from app.modules.ai.service import PromptRunReviewService
    return PromptRunReviewService(db)


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


# ── Prompt experiment endpoints ────────────────────────────────────────────────


@router.post("/prompt-experiments", response_model=PromptExperimentOut, status_code=201)
def create_prompt_experiment(
    data: PromptExperimentCreate,
    service=Depends(get_experiment_service),
) -> PromptExperimentOut:
    """Create a new prompt experiment.

    Experiments group prompt runs for parameter comparison.
    """
    try:
        experiment = service.create_experiment(data.model_dump())
        return PromptExperimentOut.model_validate(experiment)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/prompt-experiments", response_model=PromptExperimentListOut)
def list_prompt_experiments(
    prompt_key: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service=Depends(get_experiment_service),
) -> PromptExperimentListOut:
    """List prompt experiments with optional filters."""
    experiments, total = service.list_experiments(
        prompt_key=prompt_key,
        status=status,
        skip=skip,
        limit=limit,
    )
    return PromptExperimentListOut(
        items=[PromptExperimentOut.model_validate(e) for e in experiments],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/prompt-experiments/{experiment_id}", response_model=PromptExperimentOut)
def get_prompt_experiment(
    experiment_id: uuid.UUID,
    service=Depends(get_experiment_service),
) -> PromptExperimentOut:
    """Return a single prompt experiment by ID."""
    experiment = service.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
    return PromptExperimentOut.model_validate(experiment)


@router.post(
    "/prompt-experiments/{experiment_id}/runs",
    response_model=PromptExperimentRunOut,
    status_code=201,
)
def add_experiment_run(
    experiment_id: uuid.UUID,
    data: PromptExperimentRunCreate,
    service=Depends(get_experiment_service),
) -> PromptExperimentRunOut:
    """Add a prompt run variant to an experiment.

    The prompt_run_id must reference an existing ai_prompt_runs record.
    """
    try:
        run = service.add_run(experiment_id, data.model_dump())
        return PromptExperimentRunOut.model_validate(run)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/prompt-experiments/{experiment_id}/runs",
    response_model=PromptExperimentRunListOut,
)
def list_experiment_runs(
    experiment_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service=Depends(get_experiment_service),
) -> PromptExperimentRunListOut:
    """List all variant runs for a prompt experiment."""
    runs, total = service.list_runs(experiment_id, skip=skip, limit=limit)
    return PromptExperimentRunListOut(
        items=[PromptExperimentRunOut.model_validate(r) for r in runs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/prompt-experiments/{experiment_id}/runs/{run_id}",
    response_model=PromptExperimentRunOut,
)
def update_experiment_run(
    experiment_id: uuid.UUID,
    run_id: uuid.UUID,
    data: PromptExperimentRunUpdate,
    service=Depends(get_experiment_service),
) -> PromptExperimentRunOut:
    """Update an experiment run — score, notes, or winner selection."""
    try:
        run = service.update_run(
            experiment_id,
            run_id,
            data.model_dump(exclude_none=True),
        )
        return PromptExperimentRunOut.model_validate(run)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Prompt run review endpoints ────────────────────────────────────────────────


@router.post(
    "/prompt-runs/{prompt_run_id}/reviews",
    response_model=PromptRunReviewOut,
    status_code=201,
)
def create_prompt_run_review(
    prompt_run_id: uuid.UUID,
    data: PromptRunReviewCreate,
    service=Depends(get_review_service),
) -> PromptRunReviewOut:
    """Create a quality review for a prompt run.

    All score fields are optional.  Score values must be between 0.0 and 5.0.
    ready_to_send is reviewer judgment only — it does not trigger automated send.
    """
    try:
        payload = data.model_dump()
        payload["prompt_run_id"] = prompt_run_id
        review = service.create_review(payload)
        return PromptRunReviewOut.model_validate(review)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc) else 422, detail=str(exc))


@router.get(
    "/prompt-runs/{prompt_run_id}/reviews",
    response_model=PromptRunReviewListOut,
)
def list_prompt_run_reviews(
    prompt_run_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service=Depends(get_review_service),
) -> PromptRunReviewListOut:
    """List all quality reviews for a prompt run, newest-first."""
    reviews, total = service.list_reviews(prompt_run_id, skip=skip, limit=limit)
    return PromptRunReviewListOut(
        items=[PromptRunReviewOut.model_validate(r) for r in reviews],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/prompt-run-reviews/{review_id}",
    response_model=PromptRunReviewOut,
)
def update_prompt_run_review(
    review_id: uuid.UUID,
    data: PromptRunReviewUpdate,
    service=Depends(get_review_service),
) -> PromptRunReviewOut:
    """Update score fields, ready_to_send, or reviewer_notes on a quality review.

    Cannot change the linked prompt_run_id.
    """
    try:
        review = service.update_review(review_id, data.model_dump(exclude_none=True))
        return PromptRunReviewOut.model_validate(review)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
