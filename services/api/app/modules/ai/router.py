"""Read-only API endpoints for AI prompt run traces.

Endpoints:
  GET /api/v1/ai/prompt-runs          — paginated list with filters
  GET /api/v1/ai/prompt-runs/{id}     — full detail (admin/debugging only)

These endpoints are for internal debugging and quality review.
They must not be exposed on the frontend or used by guest-facing flows.
Rendered prompts and raw responses are only included in the detail endpoint.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.ai.repository import AIPromptRunRepository
from app.modules.ai.schemas import PromptRunDetailOut, PromptRunListOut, PromptRunOut

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


def get_repo(db: Session = Depends(get_db)) -> AIPromptRunRepository:
    return AIPromptRunRepository(db)


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
