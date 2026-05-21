import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.enquiries.intake_service import EnquiryIntakeService
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.enquiries.schemas import (
    DraftResponseOut,
    EnquiryCreate,
    EnquiryIntakeOut,
    EnquiryListOut,
    EnquiryMessageCreate,
    EnquiryMessageOut,
    EnquiryOut,
    EnquiryStatusUpdate,
    EnquiryUpdate,
    WebformIntakeRequest,
)
from app.modules.enquiries.service import EnquiryService
from app.modules.personas.repository import PersonaRepository

router = APIRouter(prefix="/api/v1/enquiries", tags=["enquiries"])


def get_service(db: Session = Depends(get_db)) -> EnquiryService:
    return EnquiryService(db)


def get_draft_service(db: Session = Depends(get_db)):  # type: ignore[return]
    # Lazy import — DraftGenerationService lives in the ai module (AI-001).
    from app.modules.ai.service import DraftGenerationService  # noqa: PLC0415
    return DraftGenerationService(db)


def get_intake_service(db: Session = Depends(get_db)) -> EnquiryIntakeService:
    return EnquiryIntakeService(db)


@router.post("/intake", response_model=EnquiryIntakeOut, status_code=201)
def intake_enquiry(
    data: WebformIntakeRequest,
    service: EnquiryIntakeService = Depends(get_intake_service),
) -> EnquiryIntakeOut:
    """Accept a webform submission and return the created enquiry with persona and pricing context."""
    try:
        return service.intake(data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=EnquiryListOut)
def list_enquiries(
    restaurant_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: EnquiryService = Depends(get_service),
) -> EnquiryListOut:
    items, total = service.list_enquiries(
        restaurant_id=restaurant_id, status=status, skip=skip, limit=limit
    )
    return EnquiryListOut(items=items, total=total)


@router.get("/{enquiry_id}", response_model=EnquiryOut)
def get_enquiry(
    enquiry_id: uuid.UUID,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    enquiry = service.get_enquiry(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return enquiry


@router.post("", response_model=EnquiryOut, status_code=201)
def create_enquiry(
    data: EnquiryCreate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    return service.create_enquiry(data)


@router.patch("/{enquiry_id}/status", response_model=EnquiryOut)
def update_enquiry_status(
    enquiry_id: uuid.UUID,
    data: EnquiryStatusUpdate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    try:
        enquiry = service.update_enquiry_status(enquiry_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return enquiry


@router.patch("/{enquiry_id}", response_model=EnquiryOut)
def update_enquiry(
    enquiry_id: uuid.UUID,
    data: EnquiryUpdate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    enquiry = service.update_enquiry(enquiry_id, data)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return enquiry


# ── Messages ──────────────────────────────────────────────────────────────────


@router.get("/{enquiry_id}/messages", response_model=list[EnquiryMessageOut])
def list_enquiry_messages(
    enquiry_id: uuid.UUID,
    service: EnquiryService = Depends(get_service),
) -> list[EnquiryMessageOut]:
    enquiry = service.get_enquiry(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return service.list_messages(enquiry_id)


@router.post("/{enquiry_id}/messages", response_model=EnquiryMessageOut, status_code=201)
def add_enquiry_message(
    enquiry_id: uuid.UUID,
    data: EnquiryMessageCreate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryMessageOut:
    message = service.add_message(enquiry_id, data)
    if not message:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return message


# ── Draft response ─────────────────────────────────────────────────────────────


@router.post("/{enquiry_id}/draft", response_model=DraftResponseOut, status_code=201)
def generate_draft(
    enquiry_id: uuid.UUID,
    draft_service=Depends(get_draft_service),  # type: ignore[assignment]
) -> DraftResponseOut:
    """Generate (or regenerate) a persona-based draft response for an enquiry.

    Calls the AI draft generation service, stores the result as an outbound
    message, and returns the draft with persona and pricing context.
    No email is sent.
    """
    try:
        result = draft_service.generate_draft(enquiry_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return DraftResponseOut(
        enquiry_id=result.enquiry_id,
        message_id=result.message_id,
        subject=result.subject,
        body=result.body,
        persona_name=result.persona_name,
        recommended_minimum_spend=None,
        pricing_explanation=None,
        is_fallback=result.is_fallback,
        model=result.model,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/{enquiry_id}/draft", response_model=DraftResponseOut)
def get_draft(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Retrieve the latest stored draft response for an enquiry.

    Returns 404 if no draft has been generated yet.
    """
    repo = EnquiryRepository(db)
    enquiry = repo.get_by_id(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    message = repo.get_latest_draft_message(enquiry_id)
    if not message:
        raise HTTPException(status_code=404, detail="No draft response found for this enquiry")

    # Resolve persona name from enquiry assignment
    persona_name: str | None = None
    if enquiry.persona_id:
        persona_repo = PersonaRepository(db)
        persona = persona_repo.get_by_id(enquiry.persona_id)
        if persona:
            persona_name = persona.name

    # Extract pricing context from enquiry metadata
    recommended_minimum_spend: float | None = None
    if enquiry.metadata_ and isinstance(enquiry.metadata_, dict):
        raw = enquiry.metadata_.get("recommended_minimum_spend")
        if raw is not None:
            try:
                recommended_minimum_spend = float(raw)
            except (TypeError, ValueError):
                pass

    return DraftResponseOut(
        enquiry_id=enquiry_id,
        message_id=message.id,
        subject=message.subject,
        body=message.body,
        persona_name=persona_name,
        recommended_minimum_spend=recommended_minimum_spend,
        pricing_explanation=None,
        is_fallback=None,
        model=None,
        generated_at=message.created_at,
    )
