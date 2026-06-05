import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.enquiries.intake_service import EnquiryIntakeService, FreeformIntakeService
from app.modules.enquiries.repository import DateRequestRepository, EnquiryRepository, ResponsePlanRepository
from app.modules.enquiries.schemas import (
    DraftResponseOut,
    EnquiryCandidateDateOut,
    EnquiryCreate,
    EnquiryDateRequestOut,
    EnquiryDiagnosticsOut,
    EnquiryIntakeOut,
    EnquiryListOut,
    EnquiryMessageCreate,
    EnquiryMessageOut,
    EnquiryOut,
    EnquiryStatusUpdate,
    EnquiryUpdate,
    FreeformIntakeOut,
    FreeformIntakeRequest,
    ReadinessEvaluationOut,
    ResponsePlanOut,
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


@router.get("/{enquiry_id}/readiness", response_model=ReadinessEvaluationOut)
def get_enquiry_readiness(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ReadinessEvaluationOut:
    """Return the readiness evaluation for an enquiry (ENQ-004).

    Reads the readiness evaluation stored in the latest extraction's
    normalized_json and returns it.  If no extraction exists, returns a
    deterministically computed INSUFFICIENT_INFORMATION result.

    Does not trigger extraction or re-evaluation.
    """
    from sqlalchemy import select  # noqa: PLC0415
    from app.modules.enquiries.models import EnquiryExtraction  # noqa: PLC0415
    from app.modules.enquiries.readiness_evaluator import EnquiryReadinessEvaluator  # noqa: PLC0415

    repo = EnquiryRepository(db)
    enquiry = repo.get_by_id(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    # Look for stored readiness evaluation in the latest extraction's normalized_json
    latest_extraction = db.scalars(
        select(EnquiryExtraction)
        .where(EnquiryExtraction.enquiry_id == enquiry_id)
        .order_by(EnquiryExtraction.created_at.desc())
        .limit(1)
    ).first()

    if latest_extraction is not None:
        normalized = latest_extraction.normalized_json or {}
        stored = normalized.get("readiness_evaluation")
        if stored and isinstance(stored, dict):
            return ReadinessEvaluationOut(**stored)
        # Extraction exists but no readiness stored — re-evaluate from extracted_json
        evaluation = EnquiryReadinessEvaluator().evaluate(latest_extraction.extracted_json)
        return ReadinessEvaluationOut(**evaluation.to_dict())

    # No extraction at all — return INSUFFICIENT_INFORMATION
    evaluation = EnquiryReadinessEvaluator().evaluate(None)
    return ReadinessEvaluationOut(**evaluation.to_dict())


@router.get("/{enquiry_id}/diagnostics", response_model=EnquiryDiagnosticsOut)
def get_enquiry_diagnostics(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> EnquiryDiagnosticsOut:
    """Return extraction quality diagnostics for an enquiry (ENQ-005).

    Aggregates missing-field signals, occasion normalisation, date context
    warnings, date ambiguity, and readiness outcome from the latest stored
    extraction.  Returns a deterministic INSUFFICIENT_INFORMATION result when
    no extraction has been run.

    Does not trigger extraction or re-evaluation.
    """
    from sqlalchemy import select  # noqa: PLC0415
    from app.modules.enquiries.models import EnquiryExtraction  # noqa: PLC0415
    from app.modules.enquiries.diagnostics_aggregator import DiagnosticsAggregator  # noqa: PLC0415

    repo = EnquiryRepository(db)
    enquiry = repo.get_by_id(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    latest_extraction = db.scalars(
        select(EnquiryExtraction)
        .where(EnquiryExtraction.enquiry_id == enquiry_id)
        .order_by(EnquiryExtraction.created_at.desc())
        .limit(1)
    ).first()

    diag = DiagnosticsAggregator().aggregate(
        enquiry_id=enquiry_id,
        extraction=latest_extraction,
    )

    return EnquiryDiagnosticsOut(
        enquiry_id=diag.enquiry_id,
        extraction_id=diag.extraction_id,
        prompt_run_id=diag.prompt_run_id,
        missing_critical_fields=diag.missing_critical_fields,
        has_missing_critical_fields=diag.has_missing_critical_fields,
        occasion_raw=diag.occasion_raw,
        occasion_canonical=diag.occasion_canonical,
        occasion_normalised=diag.occasion_normalised,
        date_context_warnings=diag.date_context_warnings,
        date_ambiguity_detected=diag.date_ambiguity_detected,
        date_clarification_required=diag.date_clarification_required,
        clarification_question=diag.clarification_question,
        readiness_status=diag.readiness_status,
        readiness_missing_for_availability=diag.readiness_missing_for_availability,
        readiness_notes=diag.readiness_notes,
        validation_status=diag.validation_status,
        is_fallback=diag.is_fallback,
        created_at=diag.created_at,
    )


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


@router.get("/{enquiry_id}/response-preparation/latest", response_model=ResponsePlanOut)
def get_latest_response_preparation(
    enquiry_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ResponsePlanOut:
    """Return the latest response preparation plan for an enquiry (ORCH-007).

    Returns the most recently created EnquiryResponsePlan row.
    Returns 404 when the enquiry does not exist.
    Returns a safe empty-state plan when no preparation has been run yet.
    """
    repo = EnquiryRepository(db)
    enquiry = repo.get_by_id(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    plan_repo = ResponsePlanRepository(db)
    plan = plan_repo.get_latest(enquiry_id)
    if plan is None:
        # Return a safe empty state — no plan has been run yet
        from datetime import datetime, timezone
        import uuid as _uuid
        return ResponsePlanOut(
            id=_uuid.UUID(int=0),
            enquiry_id=enquiry_id,
            snapshot_id=None,
            response_goal="NOT_RUN",
            response_priority="NORMAL",
            can_generate_draft=False,
            goal_reason="No response preparation has been run for this enquiry.",
            blocking_fields=[],
            known_facts=None,
            missing_information=None,
            clarification_questions=[],
            date_context=None,
            availability_context=None,
            customer_type_context=None,
            persona_context=None,
            draft_instructions=None,
            created_at=datetime.now(tz=timezone.utc),
        )
    return ResponsePlanOut.model_validate(plan)
