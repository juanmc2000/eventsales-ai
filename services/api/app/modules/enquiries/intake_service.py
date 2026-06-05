"""Enquiry intake orchestration service.

Coordinates webform-submitted enquiry creation:
1. Validates the target restaurant exists.
2. Resolves the default persona assigned to the restaurant.
3. Calculates a deterministic pricing recommendation.
4. Creates the enquiry record with persona and pricing context.
5. Creates an initial inbound message if a message body was provided.

No AI calls are made here — persona assignment and pricing are deterministic.
Draft response generation is handled by a separate service (AI-001).

FreeformIntakeService extends this with Sprint 7 extraction → processing →
draft chaining for natural-language submissions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.modules.personas.models import Persona as _Persona

from app.modules.enquiries.models import Enquiry
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.enquiries.schemas import (
    EnquiryIntakeOut,
    ExtractionSummaryOut,
    FreeformIntakeOut,
    FreeformIntakeRequest,
    WebformIntakeRequest,
)
from app.modules.personas.models import Persona
from app.modules.personas.repository import PersonaRepository
from app.modules.pricing.schemas import PricingRecommendationOut, PricingRecommendationRequest
from app.modules.pricing.service import PricingRuleService
from app.modules.restaurants.repository import RestaurantRepository

logger = logging.getLogger(__name__)

# ── Lazy imports for Sprint 7 services (not yet on main) ──────────────────────
try:
    from app.modules.enquiries.extraction_service import (  # noqa: PLC0415
        EnquiryExtractionService,
        ExtractionRequest,
    )
    _EXTRACTION_AVAILABLE = True
except ImportError:
    _EXTRACTION_AVAILABLE = False

try:
    from app.modules.enquiries.processing_service import (  # noqa: PLC0415
        EnquiryProcessingService,
        ProcessingRequest,
    )
    _PROCESSING_AVAILABLE = True
except ImportError:
    _PROCESSING_AVAILABLE = False

try:
    from app.modules.enquiries.date_resolution_service import (  # noqa: PLC0415
        DateResolutionRequest,
        EnquiryDateResolutionService,
    )
    _DATE_RESOLUTION_AVAILABLE = True
except ImportError:
    _DATE_RESOLUTION_AVAILABLE = False

# ── Lazy imports for Sprint 10 response preparation (ORCH-008) ────────────────
try:
    from app.modules.enquiries.availability_decision_service import AvailabilityDecisionService  # noqa: PLC0415
    from app.modules.enquiries.date_resolution_status import DateResolutionStatus, STATUS_AMBIGUOUS, STATUS_RESOLVED, STATUS_RESOLVED_WITH_CONFIRMATION, STATUS_UNKNOWN  # noqa: PLC0415
    from app.modules.enquiries.missing_information_engine import MissingInformationDecisionEngine  # noqa: PLC0415
    from app.modules.enquiries.persona_routing_context import PersonaRoutingContextBuilder  # noqa: PLC0415
    from app.modules.enquiries.readiness_evaluator import EnquiryReadinessEvaluator  # noqa: PLC0415
    from app.modules.enquiries.repository import DateRequestRepository, ResponsePlanRepository  # noqa: PLC0415
    from app.modules.enquiries.response_preparation_builder import ResponsePreparationBuilder  # noqa: PLC0415
    from app.modules.enquiries.response_priority_engine import ResponsePriorityEngine  # noqa: PLC0415
    _RESP_PREP_AVAILABLE = True
except ImportError:
    _RESP_PREP_AVAILABLE = False


class EnquiryIntakeService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._enquiry_repo = EnquiryRepository(db)
        self._persona_repo = PersonaRepository(db)
        self._pricing_service = PricingRuleService(db)
        self._restaurant_repo = RestaurantRepository(db)

    def intake(self, request: WebformIntakeRequest) -> EnquiryIntakeOut:
        """Orchestrate webform enquiry intake and return enriched context."""

        # 1. Validate restaurant exists
        restaurant = self._restaurant_repo.get_by_id(request.restaurant_id)
        if not restaurant:
            raise ValueError(f"Restaurant {request.restaurant_id} not found.")

        # 2. Resolve persona: audience-specific first, fallback to default
        persona: Persona | None = None
        if request.audience_type:
            persona = self._persona_repo.get_persona_for_audience(
                request.restaurant_id, request.audience_type
            )
        if persona is None:
            persona = self._persona_repo.get_default_persona_for_restaurant(
                request.restaurant_id
            )

        # 3. Calculate deterministic pricing recommendation
        day_of_week = (
            request.event_date.weekday()
            if request.event_date
            else datetime.now(tz=timezone.utc).weekday()
        )
        pricing: PricingRecommendationOut = self._pricing_service.calculate_recommendation(
            PricingRecommendationRequest(
                restaurant_id=request.restaurant_id,
                day_of_week=day_of_week,
                meal_period=request.meal_period,
                party_size=request.party_size,
            )
        )

        # 4. Build enquiry payload and persist
        notes_parts = []
        for field_name, label in [
            ("company_name", "Company"),
            ("budget_indication", "Budget Indication"),
            ("preferred_area", "Preferred Area"),
            ("dietary_requirements", "Dietary Requirements"),
            ("special_requests", "Special Requests"),
        ]:
            val = getattr(request, field_name, None)
            if val:
                notes_parts.append(f"{label}: {val}")

        enquiry_payload: dict = {
            "restaurant_id": request.restaurant_id,
            "persona_id": persona.id if persona else None,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "email": str(request.email),
            "phone": request.phone,
            "party_size": request.party_size,
            "event_date": request.event_date,
            "event_type": request.event_type,
            "source": "webform",
            "status": "new",
            "notes": "\n".join(notes_parts) if notes_parts else None,
            "metadata_": {"recommended_minimum_spend": pricing.recommended_minimum_spend},
        }

        enquiry: Enquiry = self._enquiry_repo.create(enquiry_payload)

        # 5. Create initial inbound message if guest provided one
        if request.message:
            self._enquiry_repo.add_message(
                enquiry.id,
                {
                    "direction": "inbound",
                    "channel": "webform",
                    "body": request.message,
                },
            )

        self._db.commit()

        return EnquiryIntakeOut(
            enquiry_id=enquiry.id,
            reference=enquiry.reference,
            status=enquiry.status,
            restaurant_id=enquiry.restaurant_id,
            persona_id=persona.id if persona else None,
            persona_name=persona.name if persona else None,
            audience_type=request.audience_type,
            recommended_minimum_spend=pricing.recommended_minimum_spend,
            pricing_explanation=pricing.explanation,
            created_at=enquiry.created_at,
        )


# ── Freeform intake service ────────────────────────────────────────────────────


class FreeformIntakeService:
    """Orchestrates freeform webform intake: extraction → processing → draft.

    Wraps all Sprint 7 services in a single transactional flow.
    Failures in extraction, processing, or draft generation are captured and
    surfaced in the response rather than raising exceptions, so the enquiry
    record is always persisted.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._enquiry_repo = EnquiryRepository(db)
        self._persona_repo = PersonaRepository(db)
        self._restaurant_repo = RestaurantRepository(db)

    def intake_freeform(self, request: FreeformIntakeRequest) -> FreeformIntakeOut:
        """Create enquiry from freeform text and chain extraction → processing → draft.

        Raises ValueError if the restaurant does not exist.
        Extraction, processing, and draft errors are captured; the enquiry is
        always returned even when downstream steps fail.
        """
        from app.core.config import settings  # noqa: PLC0415
        from app.modules.ai.constants import (  # noqa: PLC0415
            TRIGGER_FREEFORM_WEBFORM_AUTO_DRAFT,
            TRIGGER_SOURCE_API,
        )

        # 1. Validate restaurant
        restaurant = self._restaurant_repo.get_by_id(request.restaurant_id)
        if not restaurant:
            raise ValueError(f"Restaurant {request.restaurant_id} not found.")

        # 2. Resolve persona: audience-specific first, fallback to default
        persona: Persona | None = None
        if request.audience_type:
            persona = self._persona_repo.get_persona_for_audience(
                request.restaurant_id, request.audience_type
            )
        if persona is None:
            persona = self._persona_repo.get_default_persona_for_restaurant(
                request.restaurant_id
            )

        # 3. Create enquiry (no structured fields — extraction populates them)
        enquiry: Enquiry = self._enquiry_repo.create({
            "restaurant_id": request.restaurant_id,
            "persona_id": persona.id if persona else None,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "email": str(request.email),
            "phone": request.phone,
            "source": "webform",
            "status": "new",
        })

        # 4. Store freeform text as initial inbound message
        inbound_message = self._enquiry_repo.add_message(
            enquiry.id,
            {
                "direction": "inbound",
                "channel": "webform",
                "body": request.freeform_text,
            },
        )
        self._db.commit()

        # Capture enquiry fields into locals immediately after commit.
        # SQLAlchemy expires all ORM attributes on commit; if a later pipeline
        # step poisons the session, any subsequent lazy-load raises
        # PendingRollbackError.  Reading the values here avoids that.
        enquiry_id = enquiry.id
        enquiry_reference = enquiry.reference
        enquiry_status = enquiry.status
        enquiry_restaurant_id = enquiry.restaurant_id
        enquiry_created_at = enquiry.created_at
        inbound_message_id = inbound_message.id

        extraction_summary: ExtractionSummaryOut | None = None
        recommended_action: str | None = None
        draft_subject: str | None = None
        draft_body: str | None = None
        draft_message_id = None
        draft_is_fallback: bool | None = None
        draft_ai_context = None

        # 5. Extraction step (lazy — requires API-014 to be merged)
        extraction_result = None
        if _EXTRACTION_AVAILABLE:
            try:
                svc = EnquiryExtractionService(self._db)
                extraction_result = svc.extract(ExtractionRequest(
                    enquiry_id=enquiry_id,
                    freeform_text=request.freeform_text,
                    restaurant_name=restaurant.name,
                    restaurant_id=request.restaurant_id,
                    source_message_id=inbound_message_id,
                    tenant_id="default",
                    api_key=settings.anthropic_api_key or "",
                ))
                parsed = extraction_result.parsed or {}
                extraction_summary = ExtractionSummaryOut(
                    extraction_id=extraction_result.extraction_id,
                    prompt_run_id=extraction_result.prompt_run_id,
                    is_fallback=extraction_result.is_fallback,
                    validation_status=extraction_result.validation_status,
                    guest_count=parsed.get("guest_count"),
                    event_date=parsed.get("event_date"),
                    event_type=parsed.get("event_type"),
                    # ENQ-001: occasion fields — raw from LLM, canonical from normaliser
                    occasion_raw=parsed.get("occasion"),
                    occasion_canonical=extraction_result.occasion_canonical,
                    missing_fields=parsed.get("missing_fields"),
                    extraction_system_prompt=extraction_result.rendered_system_prompt if not extraction_result.is_fallback else None,
                    extraction_user_prompt=extraction_result.rendered_user_prompt if not extraction_result.is_fallback else None,
                    extraction_raw_response=extraction_result.raw_response if not extraction_result.is_fallback else None,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Extraction failed for enquiry %s: %s", enquiry_id, exc)
                self._db.rollback()
                extraction_summary = ExtractionSummaryOut(
                    is_fallback=True,
                    validation_status="error",
                )

        # 6. Date resolution step — expand date_request into candidate dates
        if (
            _DATE_RESOLUTION_AVAILABLE
            and extraction_result is not None
            and not extraction_result.is_fallback
            and extraction_result.parsed
        ):
            date_request_dict = extraction_result.parsed.get("date_request")
            if date_request_dict and isinstance(date_request_dict, dict):
                try:
                    dr_svc = EnquiryDateResolutionService(self._db)
                    dr_svc.resolve(DateResolutionRequest(
                        enquiry_id=enquiry_id,
                        date_request_dict=date_request_dict,
                        tenant_id="default",
                        extraction_id=extraction_result.extraction_id,
                        prompt_run_id=extraction_result.prompt_run_id,
                    ))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Date resolution failed for enquiry %s: %s", enquiry_id, exc)
                    self._db.rollback()

        # 7. Processing step (lazy — requires WORKFLOW-007 to be merged)
        processing_result = None
        if _PROCESSING_AVAILABLE and extraction_result is not None and extraction_result.extraction_id is not None:
            try:
                proc_svc = EnquiryProcessingService(self._db)
                processing_result = proc_svc.process(ProcessingRequest(
                    enquiry_id=enquiry_id,
                    restaurant_id=request.restaurant_id,
                    extraction_id=extraction_result.extraction_id,
                    extraction_parsed=extraction_result.parsed or {},
                    tenant_id="default",
                ))
                recommended_action = processing_result.recommended_action
            except Exception as exc:  # noqa: BLE001
                logger.warning("Processing failed for enquiry %s: %s", enquiry_id, exc)
                self._db.rollback()

        # 7.5 Response preparation (ORCH-008) — runs after processing, before draft
        response_preparation_summary: dict | None = None
        if _RESP_PREP_AVAILABLE and extraction_result is not None and not extraction_result.is_fallback:
            try:
                response_preparation_summary = _run_response_preparation(
                    db=self._db,
                    enquiry_id=enquiry_id,
                    extraction_result=extraction_result,
                    processing_result=processing_result,
                    persona=persona,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Response preparation failed for enquiry %s: %s", enquiry_id, exc)
                self._db.rollback()

        # 8. Draft generation (always attempted — has its own fallback)
        try:
            from app.modules.ai.service import DraftGenerationService  # noqa: PLC0415
            draft_svc = DraftGenerationService(self._db)
            draft_result = draft_svc.generate_draft(
                enquiry_id,
                trigger_type=TRIGGER_FREEFORM_WEBFORM_AUTO_DRAFT,
            )
            draft_subject = draft_result.subject
            draft_body = draft_result.body
            draft_message_id = draft_result.message_id
            draft_is_fallback = draft_result.is_fallback
            draft_ai_context = draft_result.ai_context
        except Exception as exc:  # noqa: BLE001
            logger.warning("Draft generation failed for enquiry %s: %s", enquiry_id, exc)

        return FreeformIntakeOut(
            enquiry_id=enquiry_id,
            reference=enquiry_reference,
            status=enquiry_status,
            restaurant_id=enquiry_restaurant_id,
            persona_id=persona.id if persona else None,
            persona_name=persona.name if persona else None,
            audience_type=request.audience_type,
            created_at=enquiry_created_at,
            extraction=extraction_summary,
            recommended_action=recommended_action,
            draft_subject=draft_subject,
            draft_body=draft_body,
            draft_message_id=draft_message_id,
            draft_is_fallback=draft_is_fallback,
            draft_ai_context=draft_ai_context,
            response_preparation_summary=response_preparation_summary,
        )


# ── ORCH-008 helper — response preparation step ───────────────────────────────


def _run_response_preparation(
    db: "Session",
    enquiry_id: "uuid.UUID",
    extraction_result: "Any",
    processing_result: "Any",
    persona: "Persona | None",
) -> dict:
    """Run response preparation after processing and persist the plan.

    Returns a summary dict for inclusion in FreeformIntakeOut.
    Raises on any error — caller wraps in try/except.
    """
    import uuid as _uuid  # noqa: PLC0415

    parsed = extraction_result.parsed or {}

    # ── Readiness evaluation ──────────────────────────────────────────────────
    readiness = EnquiryReadinessEvaluator().evaluate(parsed)

    # ── Date resolution status from stored date request ───────────────────────
    date_request_repo = DateRequestRepository(db)
    stored_dr = date_request_repo.get_latest_date_request(enquiry_id)
    candidate_dates_orm = date_request_repo.list_candidate_dates(enquiry_id)

    date_request_dict = parsed.get("date_request") or {}
    date_status = _build_date_resolution_status(stored_dr, date_request_dict)

    # ── Candidate dates list ──────────────────────────────────────────────────
    candidate_dates = list(candidate_dates_orm)

    # ── Customer type ─────────────────────────────────────────────────────────
    customer_type = (
        parsed.get("audience_type_from_content")
        or parsed.get("audience_type")
        or "unknown"
    ) or "unknown"
    customer_type_confidence = float(parsed.get("audience_confidence") or 0.0)
    customer_type_reason = parsed.get("audience_evidence") or ""

    # ── Availability decision ─────────────────────────────────────────────────
    availability_decision = AvailabilityDecisionService.decide(
        candidate_dates=candidate_dates,
        date_resolution_status=date_status,
        guest_count=parsed.get("guest_count"),
        meal_period=parsed.get("meal_period"),
        room_availability_results=(
            processing_result.availability_result_json if processing_result else None
        ),
    )

    # ── Missing information ───────────────────────────────────────────────────
    missing_info = MissingInformationDecisionEngine.decide(
        date_status=date_status.status,
        date_clarification_question=date_status.clarification_question,
        guest_count_present=readiness.guest_count_present,
        occasion_understood=readiness.occasion_understood,
        meal_period_present=readiness.meal_period_present,
    )

    # ── Persona routing context ───────────────────────────────────────────────
    assigned_personas: list = []
    if persona is not None:
        assigned_personas = [persona]
    persona_ctx = PersonaRoutingContextBuilder.build(
        final_customer_type=customer_type,
        final_customer_type_confidence=customer_type_confidence,
        customer_type_resolution_reason=customer_type_reason,
        assigned_personas=assigned_personas,
    )

    # ── Response priority ─────────────────────────────────────────────────────
    resolved_date = date_status.resolved_date
    candidate_iso = [
        str(getattr(cd, "candidate_date", "") or "")
        for cd in candidate_dates
        if getattr(cd, "candidate_date", None)
    ]
    priority_result = ResponsePriorityEngine.decide(
        resolved_event_date=resolved_date,
        candidate_dates=candidate_iso,
        date_status=date_status.status,
    )

    # ── Assemble response plan ────────────────────────────────────────────────
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        date_resolution_status=date_status,
        candidate_dates=candidate_dates,
        customer_type=customer_type,
        customer_type_confidence=customer_type_confidence,
        customer_type_reason=customer_type_reason,
        availability_decision=availability_decision,
        missing_information_result=missing_info,
        persona_routing_context=persona_ctx,
        response_priority_result=priority_result,
    )

    # ── Persist ───────────────────────────────────────────────────────────────
    snapshot_id = (
        processing_result.snapshot_id
        if processing_result and processing_result.snapshot_id
        else None
    )
    plan_repo = ResponsePlanRepository(db)
    plan_repo.create(
        enquiry_id=enquiry_id,
        snapshot_id=snapshot_id,
        tenant_id="default",
        plan_data={
            "response_goal": plan.response_goal,
            "response_priority": plan.response_priority,
            "can_generate_draft": plan.can_generate_draft,
            "goal_reason": plan.goal_reason,
            "blocking_fields": plan.blocking_fields,
            "known_facts": plan.known_facts,
            "missing_information": plan.missing_information,
            "clarification_questions": plan.clarification_questions,
            "date_context": plan.date_context,
            "availability_context": plan.availability_context,
            "customer_type_context": plan.customer_type_context,
            "persona_context": plan.persona_context,
            "draft_instructions": plan.draft_instructions,
        },
    )
    db.commit()

    return {
        "response_goal": plan.response_goal,
        "response_priority": plan.response_priority,
        "can_generate_draft": plan.can_generate_draft,
        "clarification_questions": plan.clarification_questions,
    }


def _build_date_resolution_status(
    stored_dr: "Any",
    date_request_dict: dict,
) -> "DateResolutionStatus":
    """Construct a DateResolutionStatus from a stored EnquiryDateRequest row."""
    if stored_dr is None:
        return DateResolutionStatus.unknown(
            original_text=date_request_dict.get("raw_text")
        )

    raw_text = getattr(stored_dr, "raw_text", None) or date_request_dict.get("raw_text")
    ambiguity_type = getattr(stored_dr, "ambiguity_type", None)
    clarification_required = getattr(stored_dr, "clarification_required", None)
    clarification_required_bool = bool(
        clarification_required
        if clarification_required is not None
        else getattr(stored_dr, "requires_date_clarification", False)
    )
    clarification_question = getattr(stored_dr, "clarification_question", None)
    clarification_reason = getattr(stored_dr, "clarification_reason", None)
    assumed_date = getattr(stored_dr, "assumed_date", None)
    alternative_date = getattr(stored_dr, "alternative_date", None)

    # Map ambiguity_type → DateResolutionStatus.status
    if ambiguity_type == "resolved":
        status = STATUS_RESOLVED
    elif ambiguity_type == "resolved_with_confirmation":
        status = STATUS_RESOLVED_WITH_CONFIRMATION
    elif ambiguity_type == "unresolved_ambiguity":
        status = STATUS_AMBIGUOUS
    elif clarification_required_bool:
        status = STATUS_AMBIGUOUS
    elif assumed_date is not None:
        status = STATUS_RESOLVED
    else:
        status = STATUS_UNKNOWN

    return DateResolutionStatus(
        status=status,
        original_text=raw_text,
        resolution_method="intake_pipeline",
        resolved_date=assumed_date.isoformat() if assumed_date else None,
        alternative_date=alternative_date.isoformat() if alternative_date else None,
        clarification_required=clarification_required_bool,
        clarification_reason=clarification_reason,
        clarification_question=clarification_question,
    )
