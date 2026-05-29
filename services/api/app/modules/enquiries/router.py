import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.enquiries.intake_service import EnquiryIntakeService, FreeformIntakeService
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.enquiries.repository import DateRequestRepository
from app.modules.enquiries.schemas import (
    DraftResponseOut,
    EnquiryCandidateDateOut,
    EnquiryCreate,
    EnquiryDateRequestOut,
    EnquiryIntakeOut,
    EnquiryListOut,
    EnquiryMessageCreate,
    EnquiryMessageOut,
    EnquiryOut,
    EnquiryStatusUpdate,
    EnquiryUpdate,
    FreeformIntakeOut,
    FreeformIntakeRequest,
    WebformIntakeRequest,
)
from app.modules.enquiries.service import EnquiryService
from app.modules.personas.repository import PersonaRepository

router = APIRouter(prefix="/api/v1/enquiries", tags=["enquiries"])


def get_service(db: Session = Depends(get_db)) -> EnquiryService:
    return EnquiryService(db)


def get_intake_service(db: Session = Depends(get_db)) -> EnquiryIntakeService:
    return EnquiryIntakeService(db)


def get_draft_service(db: Session = Depends(get_db)):  # type: ignore[return]
    from app.modules.ai.service import DraftGenerationService  # noqa: PLC0415
    return DraftGenerationService(db)


def get_freeform_intake_service(db: Session = Depends(get_db)) -> FreeformIntakeService:
    return FreeformIntakeService(db)


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


@router.post("/intake/freeform", response_model=FreeformIntakeOut, status_code=201)
def intake_freeform_enquiry(
    data: FreeformIntakeRequest,
    service: FreeformIntakeService = Depends(get_freeform_intake_service),
) -> FreeformIntakeOut:
    """Accept a freeform natural-language enquiry and run extraction → processing → draft.

    Returns the created enquiry with extraction summary, recommended action,
    and generated draft body in a single response.
    """
    try:
        return service.intake_freeform(data)
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
    """Generate a persona-based draft response for an enquiry. No email is sent."""
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
        ai_context=result.ai_context,
    )


@router.get("/{enquiry_id}/draft", response_model=DraftResponseOut)
def get_draft(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DraftResponseOut:
    """Retrieve the latest stored draft response for an enquiry."""
    repo = EnquiryRepository(db)
    enquiry = repo.get_by_id(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    message = repo.get_latest_draft_message(enquiry_id)
    if not message:
        raise HTTPException(status_code=404, detail="No draft response found for this enquiry")

    persona_name: str | None = None
    if enquiry.persona_id:
        persona_repo = PersonaRepository(db)
        persona = persona_repo.get_by_id(enquiry.persona_id)
        if persona:
            persona_name = persona.name

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


# ── Email events ───────────────────────────────────────────────────────────────


@router.get("/{enquiry_id}/email-events")
def get_email_events(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list:
    """Return all email events for an enquiry."""
    from app.modules.email.models import EmailEvent  # noqa: PLC0415
    from app.modules.email.schemas import EmailEventOut  # noqa: PLC0415
    from sqlalchemy import select as sa_select  # noqa: PLC0415

    stmt = (
        sa_select(EmailEvent)
        .where(EmailEvent.enquiry_id == enquiry_id)
        .order_by(EmailEvent.created_at.desc())
    )
    events = db.scalars(stmt).all()
    return [EmailEventOut.model_validate(e) for e in events]


# ── Date request and candidate dates (API-019) ─────────────────────────────────


@router.get("/{enquiry_id}/date-request/latest", response_model=EnquiryDateRequestOut)
def get_latest_date_request(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> EnquiryDateRequestOut:
    """Return the latest extracted date request for an enquiry.

    Returns 404 when no date request has been run for this enquiry.
    Does not trigger date resolution.
    """
    repo = EnquiryRepository(db)
    enquiry = repo.get_by_id(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    date_repo = DateRequestRepository(db)
    date_request = date_repo.get_latest_date_request(enquiry_id)
    if not date_request:
        raise HTTPException(status_code=404, detail="No date request found for this enquiry")

    return EnquiryDateRequestOut.model_validate(date_request)


@router.get("/{enquiry_id}/candidate-dates", response_model=list[EnquiryCandidateDateOut])
def list_candidate_dates(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[EnquiryCandidateDateOut]:
    """Return all candidate dates for an enquiry ordered by date.

    Returns an empty list when no candidate dates exist.
    Does not trigger availability or pricing checks.
    """
    repo = EnquiryRepository(db)
    enquiry = repo.get_by_id(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    date_repo = DateRequestRepository(db)
    candidates = date_repo.list_candidate_dates(enquiry_id)
    return [EnquiryCandidateDateOut.model_validate(c) for c in candidates]
