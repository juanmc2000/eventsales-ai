"""Draft generation service.

Orchestrates context assembly, AI Gateway invocation, draft generation,
and persistence of the draft as an outbound EnquiryMessage.

Responsibilities:
- Load enquiry, persona, and restaurant from the database.
- Assemble DraftContext and input_payload from the loaded records.
- Call AIGateway.run() — no direct provider calls.
- Generate the fallback draft body when the gateway returns is_fallback=True.
- Persist the draft as an outbound 'draft' channel EnquiryMessage.
- Return a DraftGenerationResult to the caller.

The AI Gateway handles all LLM calls, prompt resolution, and trace logging.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.ai.constants import (
    PROMPT_KEY_DRAFT_RESPONSE,
    TRIGGER_MANUAL_GENERATE_DRAFT,
    TRIGGER_SOURCE_API,
)
from app.modules.ai.gateway import AIGateway
from app.modules.ai.provider import FallbackProvider
from app.modules.ai.schemas import (
    AIContextOut,
    AIGatewayRequest,
    DraftContext,
    DraftGenerationResult,
)
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.personas.repository import PersonaRepository
from app.modules.restaurants.repository import RestaurantRepository, RoomRepository

# EnquiryProcessingSnapshot is added by DATA-015 / WORKFLOW-007.  Lazy import so
# this service is importable on deployments that haven't applied those migrations.
try:
    from app.modules.enquiries.models import EnquiryProcessingSnapshot
    _PROCESSING_MODEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    EnquiryProcessingSnapshot = None  # type: ignore[assignment,misc]
    _PROCESSING_MODEL_AVAILABLE = False

logger = logging.getLogger(__name__)


class DraftGenerationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._enquiry_repo = EnquiryRepository(db)
        self._persona_repo = PersonaRepository(db)
        self._restaurant_repo = RestaurantRepository(db)
        self._room_repo = RoomRepository(db)

    def generate_draft(
        self,
        enquiry_id: uuid.UUID,
        trigger_type: str = TRIGGER_MANUAL_GENERATE_DRAFT,
    ) -> DraftGenerationResult:
        """Generate and store a persona-based draft response for an enquiry.

        Routes all LLM calls through AIGateway.run().
        Falls back to template-based generation when no API key is configured.

        Raises ValueError if the enquiry does not exist.
        """
        enquiry = self._enquiry_repo.get_by_id(enquiry_id)
        if not enquiry:
            raise ValueError(f"Enquiry {enquiry_id} not found.")

        # Load restaurant
        restaurant = self._restaurant_repo.get_by_id(enquiry.restaurant_id)
        restaurant_name = restaurant.name if restaurant else "our venue"
        restaurant_description = restaurant.description if restaurant else None
        restaurant_address = restaurant.address if restaurant else None

        # Load persona (from enquiry assignment, or fall back to restaurant default)
        persona = None
        if enquiry.persona_id:
            persona = self._persona_repo.get_by_id(enquiry.persona_id)
        if not persona:
            persona = self._persona_repo.get_default_persona_for_restaurant(
                enquiry.restaurant_id
            )

        persona_name = persona.name if persona else "Events Team"
        persona_tone = persona.tone if persona else "professional"
        persona_style = persona.style if persona else "concise"
        persona_system_prompt = persona.system_prompt if persona else ""

        # Extract recommended minimum spend from enquiry metadata
        recommended_minimum_spend: float | None = None
        if enquiry.metadata_ and isinstance(enquiry.metadata_, dict):
            raw = enquiry.metadata_.get("recommended_minimum_spend")
            if raw is not None:
                try:
                    recommended_minimum_spend = float(raw)
                except (TypeError, ValueError):
                    pass

        # Extract guest's initial message from stored notes or first inbound message
        guest_message = _extract_guest_message(enquiry.notes)

        # Match a suitable room/PDR deterministically
        preferred_area = getattr(enquiry, "preferred_area", None)
        room = _match_room(
            rooms=self._room_repo.list_for_restaurant(
                enquiry.restaurant_id, active_only=True
            ),
            party_size=enquiry.party_size,
            preferred_area=preferred_area,
        )

        # Build DraftContext for fallback body generation (preserved behavior)
        context = DraftContext(
            enquiry_id=enquiry_id,
            guest_first_name=enquiry.first_name,
            guest_last_name=enquiry.last_name,
            event_type=enquiry.event_type,
            event_date=str(enquiry.event_date) if enquiry.event_date else None,
            party_size=enquiry.party_size,
            guest_message=guest_message,
            restaurant_name=restaurant_name,
            restaurant_description=restaurant_description,
            persona_name=persona_name,
            persona_tone=persona_tone,
            persona_style=persona_style,
            persona_system_prompt=persona_system_prompt,
            recommended_minimum_spend=recommended_minimum_spend,
            restaurant_address=restaurant_address,
            room_name=room.name if room else None,
            room_type=room.room_type if room else None,
            room_seated_capacity=room.seated_capacity if room else None,
            room_standing_capacity=room.standing_capacity if room else None,
            room_layouts=list(room.layouts) if room and room.layouts else None,
            room_amenities=list(room.amenities) if room and room.amenities else None,
            room_suitability_notes=room.suitability_notes if room else None,
            room_booking_url=room.booking_url if room else None,
            room_is_private_dining=room.is_private_dining if room else False,
        )

        # ── Sprint 7: Load processing snapshot for enriched context ──────────
        snapshot = _load_latest_processing_snapshot(self._db, enquiry_id)
        if snapshot is not None:
            context = _enrich_context_from_snapshot(context, snapshot)

        # ── RESP-003: Load response preparation plan for goal-driven drafting ─
        context = _enrich_context_from_response_plan(self._db, enquiry_id, context)

        # Build input_payload for the draft_response prompt template
        input_payload = _build_draft_input_payload(context)

        # ── Call AI Gateway (single entry point for all LLM calls) ────────────
        gateway = AIGateway(db=self._db, api_key=settings.anthropic_api_key)
        gateway_result = gateway.run(AIGatewayRequest(
            prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
            input_payload=input_payload,
            tenant_id="default",
            restaurant_id=enquiry.restaurant_id,
            persona_id=enquiry.persona_id,
            enquiry_id=enquiry_id,
            trigger_type=trigger_type,
            trigger_source=TRIGGER_SOURCE_API,
        ))

        # ── Determine draft body ──────────────────────────────────────────────
        is_fallback = gateway_result.is_fallback
        model_name = gateway_result.model_name

        if is_fallback or not gateway_result.raw_response:
            # No LLM response — use template-based fallback (pure Python, no API call)
            draft_body = FallbackProvider().generate(context)
        else:
            draft_body = gateway_result.raw_response

        # ── Build AI transparency context ─────────────────────────────────────
        ai_context = AIContextOut(
            model=model_name,
            is_fallback=is_fallback,
            persona_name=persona_name,
            persona_tone=persona_tone,
            persona_style=persona_style,
            guest_message_used=guest_message,
            room_name=context.room_name,
            recommended_minimum_spend=recommended_minimum_spend,
            system_prompt=gateway_result.rendered_system_prompt,
            user_message=gateway_result.rendered_user_prompt,
            prompt_run_id=gateway_result.run_id if not is_fallback else None,
        )

        subject = _build_subject(enquiry.first_name, enquiry.last_name, enquiry.event_type)

        # Persist draft as an outbound message so it appears in the message thread
        message = self._enquiry_repo.add_message(
            enquiry_id,
            {
                "direction": "outbound",
                "channel": "draft",
                "subject": subject,
                "body": draft_body,
                "sent_at": None,  # Draft — not yet sent
            },
        )
        self._db.commit()

        return DraftGenerationResult(
            enquiry_id=enquiry_id,
            message_id=message.id,
            subject=subject,
            body=draft_body,
            persona_name=persona_name,
            is_fallback=is_fallback,
            model=model_name,
            ai_context=ai_context,
        )


# ── Internal helpers ───────────────────────────────────────────────────────────


def _build_draft_input_payload(context: DraftContext) -> dict:
    """Build the input_payload dict for the draft_response prompt template.

    Converts DraftContext fields into the {variable} placeholders used by
    the prompt template.  Optional line variables are pre-formatted so the
    renderer can substitute them as complete lines.
    """
    payload: dict = {
        # Required variables
        "persona_system_prompt": context.persona_system_prompt or "",
        "persona_name": context.persona_name,
        "restaurant_name": context.restaurant_name,
        "persona_tone": context.persona_tone,
        "persona_style": context.persona_style,
        "guest_first_name": context.guest_first_name,
        "guest_last_name": context.guest_last_name,
        # Optional line variables — empty string when absent
        "event_type_line": (
            f"Event type: {context.event_type.replace('_', ' ').title()}\n"
            if context.event_type else ""
        ),
        "event_date_line": (
            f"Event date: {context.event_date}\n" if context.event_date else ""
        ),
        "party_size_line": (
            f"Party size: {context.party_size}\n" if context.party_size else ""
        ),
        "spend_line": _build_spend_line(context),
        "room_lines": _build_room_lines(context),
        # Sprint 7 enrichment variables (present only when processing snapshot is available)
        "availability_line": _build_availability_line(context),
        "missing_questions_line": _build_missing_questions_line(context),
        # RESP-005: response goal — new goals take precedence; legacy alias kept for
        # stored DB records that may still hold READY_TO_CONFIRM_AVAILABILITY.
        "response_goal": context.response_goal or "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
        "audience_type_line": (
            f"Audience type: {context.audience_type}\n" if context.audience_type else ""
        ),
        "clarification_questions_line": _build_clarification_questions_line(context),
        # RESP-006: structured draft context — separates tone from operational facts
        "guest_message_line": _build_guest_tone_line(context),
        "confirmed_venue_facts_line": _build_confirmed_venue_facts_line(context),
        "requested_preferences_line": _build_requested_preferences_line(context),
        "prohibited_claims_line": _build_prohibited_claims_line(context),
    }
    return payload


def _build_spend_line(context: DraftContext) -> str:
    """Build spend line — prefer confirmed_minimum_spend from snapshot over metadata.

    Labels the spend as 'Minimum spend' — a mandatory venue requirement.
    """
    spend = context.confirmed_minimum_spend or context.recommended_minimum_spend
    if spend and spend > 0:
        return f"Minimum spend: £{spend:,.0f}\n"
    return ""


def _derive_availability_contract(context: DraftContext) -> str:
    """Map DraftContext fields to one of the five V4 availability contract states.

    Contract states:
      CONFIRMED_AVAILABLE       — deterministic check confirmed available
      CONFIRMED_UNAVAILABLE     — deterministic check confirmed booked/held
      NOT_CHECKED               — no availability check performed
      PENDING_DATE_CONFIRMATION — date is ambiguous; cannot check yet
      INSUFFICIENT_INFORMATION  — required info missing to check availability
    """
    status = context.availability_status
    if status == "available":
        return "CONFIRMED_AVAILABLE"
    if status in ("booked", "held", "unavailable"):
        return "CONFIRMED_UNAVAILABLE"
    goal = context.response_goal or ""
    # RESP-005 new goals map directly to contract states
    if goal == "CONFIRM_AVAILABLE":
        return "CONFIRMED_AVAILABLE"
    if goal == "RESPOND_UNAVAILABLE":
        return "CONFIRMED_UNAVAILABLE"
    if goal == "REQUEST_DATE_CONFIRMATION":
        return "PENDING_DATE_CONFIRMATION"
    if goal in ("REQUEST_MISSING_INFORMATION", "REQUEST_WEBFORM"):
        return "INSUFFICIENT_INFORMATION"
    return "NOT_CHECKED"


def _build_availability_line(context: DraftContext) -> str:
    """Build availability line with explicit V4 contract state.

    Always returns a non-empty string so the LLM receives an unambiguous
    availability contract status and cannot infer availability from silence.
    """
    contract = _derive_availability_contract(context)
    date_str = context.availability_date or ""
    period = context.availability_meal_period or ""
    slot = f"{date_str} {period}".strip()

    if contract == "CONFIRMED_AVAILABLE":
        return (
            f"Availability status: CONFIRMED_AVAILABLE\n"
            f"Availability: Room is available for {slot}.\n"
        )
    if contract == "CONFIRMED_UNAVAILABLE":
        return (
            f"Availability status: CONFIRMED_UNAVAILABLE\n"
            f"Availability: The requested slot ({slot}) is not available.\n"
        )
    if contract == "PENDING_DATE_CONFIRMATION":
        return (
            "Availability status: PENDING_DATE_CONFIRMATION\n"
            "Availability: Cannot check — date must be confirmed first.\n"
        )
    if contract == "INSUFFICIENT_INFORMATION":
        return (
            "Availability status: INSUFFICIENT_INFORMATION\n"
            "Availability: Cannot check — required information is missing.\n"
        )
    # NOT_CHECKED — default
    return (
        "Availability status: NOT_CHECKED\n"
        "Availability: Not yet checked — do not confirm availability.\n"
    )


def _build_missing_questions_line(context: DraftContext) -> str:
    """Format missing questions as a prompt instruction for the model."""
    if not context.missing_questions:
        return ""
    questions = ", ".join(context.missing_questions)
    return f"Please ask the guest for the following missing information: {questions}.\n"


def _build_clarification_questions_line(context: DraftContext) -> str:
    """Format RESP-003 clarification questions as an ordered prompt instruction."""
    questions = context.clarification_questions
    if not questions:
        return ""
    if len(questions) == 1:
        return f"Clarification question to ask: {questions[0]}\n"
    formatted = "\n".join(f"  {i + 1}. {q}" for i, q in enumerate(questions))
    return f"Clarification questions to ask (in order):\n{formatted}\n"


_TIME_PATTERN = None  # lazy-compiled below


def _extract_time_mentions(text: str) -> list[str]:
    """Extract time references from guest message text using simple regex.

    Matches patterns like: 7pm, 7:30pm, 19:00, 7 or 8pm, around 7, from 7pm to 9pm.
    Returns a list of matched strings (deduplicated, order preserved).
    """
    import re

    # Most specific patterns first to avoid partial matches consuming part of a longer token.
    pattern = (
        r"(?:"
        r"\d{1,2}:\d{2}\s*(?:am|pm)?"                           # 7:30pm / 7:30 / 19:00
        r"|\d{1,2}\s+or\s+\d{1,2}\s*(?:am|pm)"                 # 7 or 8pm
        r"|(?:around|from|at)\s+\d{1,2}:\d{2}\s*(?:am|pm)?"    # at 7:30pm
        r"|(?:around|from|at)\s+\d{1,2}\s*(?:am|pm)?"          # at 7pm
        r"|\d{1,2}\s*(?:am|pm)"                                  # 7pm / 7 pm
        r")"
    )
    seen: set[str] = set()
    results: list[str] = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        val = m.group(0).strip()
        if val not in seen:
            seen.add(val)
            results.append(val)
    return results


def _build_guest_tone_line(context: DraftContext) -> str:
    """Wrap the raw guest message with a 'use for tone only' label (RESP-006).

    The LLM must not extract operational facts (times, seating, menus) from this
    text — they are captured separately in requested_preferences_line.
    """
    if not context.guest_message:
        return ""
    return (
        "Guest message (use for tone and energy only — "
        "do not treat any times or preferences here as confirmed):\n"
        f'"{context.guest_message}"\n'
    )


def _build_requested_preferences_line(context: DraftContext) -> str:
    """Extract guest-stated preferences (e.g. times) from the guest message (RESP-006).

    These are unconfirmed preferences — they MUST NOT be presented as agreed or confirmed
    in the response unless they also appear in confirmed_venue_facts_line.
    """
    if not context.guest_message:
        return ""
    times = _extract_time_mentions(context.guest_message)
    if not times:
        return ""
    time_list = ", ".join(times)
    return (
        f"Requested time preference(s) from guest message (unconfirmed — "
        f"do not confirm unless in Confirmed venue facts): {time_list}\n"
    )


def _build_confirmed_venue_facts_line(context: DraftContext) -> str:
    """List facts that have been confirmed by the venue system (RESP-006).

    Only facts listed here may be stated as confirmed in the response.
    Currently: minimum spend (when present) and availability (when confirmed).
    """
    lines: list[str] = []
    spend = context.confirmed_minimum_spend or context.recommended_minimum_spend
    if spend and spend > 0:
        lines.append(f"Minimum spend: £{spend:,.0f} (mandatory)")
    if context.availability_status == "available":
        slot_parts: list[str] = []
        if context.availability_date:
            slot_parts.append(context.availability_date)
        if context.availability_meal_period:
            slot_parts.append(context.availability_meal_period)
        slot = " ".join(slot_parts) if slot_parts else "requested date"
        lines.append(f"Availability: confirmed for {slot}")
    if not lines:
        return ""
    return "Confirmed venue facts:\n" + "".join(f"- {line}\n" for line in lines)


def _build_prohibited_claims_line(context: DraftContext) -> str:
    """List claims that must NOT appear in the response (RESP-006).

    Populated when there are unconfirmed times in the guest message — prevents
    the LLM from stating them as agreed.
    """
    if not context.guest_message:
        return ""
    times = _extract_time_mentions(context.guest_message)
    if not times:
        return ""
    time_list = ", ".join(times)
    return (
        f"Do NOT confirm or state as agreed: {time_list} "
        f"(guest preference only — not confirmed by venue)\n"
    )


def _enrich_context_from_response_plan(
    db: Session, enquiry_id: uuid.UUID, context: DraftContext
) -> DraftContext:
    """Enrich DraftContext with response_goal and clarification_questions from the latest plan.

    Returns the original context unchanged when no plan exists or on any error.
    """
    try:
        from dataclasses import replace  # noqa: PLC0415
        from app.modules.enquiries.repository import ResponsePlanRepository  # noqa: PLC0415

        plan_repo = ResponsePlanRepository(db)
        plan = plan_repo.get_latest(enquiry_id)
        if plan is None:
            return context

        response_goal: str | None = getattr(plan, "response_goal", None)
        clarification_questions: list[str] | None = None
        raw_questions = getattr(plan, "clarification_questions", None)
        if isinstance(raw_questions, list):
            clarification_questions = [str(q) for q in raw_questions if q]

        # Audience type from customer_type_context JSON column
        audience_type: str | None = context.audience_type
        ctype_ctx = getattr(plan, "customer_type_context", None)
        if isinstance(ctype_ctx, dict):
            audience_type = ctype_ctx.get("final_customer_type") or audience_type

        return replace(
            context,
            response_goal=response_goal or context.response_goal,
            clarification_questions=clarification_questions or context.clarification_questions,
            audience_type=audience_type,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not enrich context from response plan for %s: %s", enquiry_id, exc)
        return context


def _load_latest_processing_snapshot(db: Session, enquiry_id: uuid.UUID):
    """Return the most recent processing snapshot for an enquiry, or None.

    Returns None safely when EnquiryProcessingSnapshot model is unavailable
    (DATA-015 not yet applied).
    """
    if not _PROCESSING_MODEL_AVAILABLE or EnquiryProcessingSnapshot is None:
        return None
    try:
        stmt = (
            select(EnquiryProcessingSnapshot)
            .where(EnquiryProcessingSnapshot.enquiry_id == enquiry_id)
            .order_by(EnquiryProcessingSnapshot.created_at.desc())
            .limit(1)
        )
        return db.scalars(stmt).first()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load processing snapshot for %s: %s", enquiry_id, exc)
        return None


def _enrich_context_from_snapshot(context: DraftContext, snapshot) -> DraftContext:
    """Return a copy of DraftContext enriched with processing snapshot data.

    Uses dataclass replace-style construction — does NOT mutate the original.
    """
    from dataclasses import replace

    availability_status = None
    availability_date = None
    availability_meal_period = None
    if isinstance(snapshot.availability_result_json, dict):
        avail = snapshot.availability_result_json
        availability_status = avail.get("status")
        availability_date = avail.get("date")
        availability_meal_period = avail.get("meal_period")

    confirmed_minimum_spend = None
    pricing_explanation = None
    if isinstance(snapshot.pricing_result_json, dict):
        pricing = snapshot.pricing_result_json
        confirmed_minimum_spend = pricing.get("minimum_spend")
        pricing_explanation = pricing.get("explanation")

    room_name = context.room_name
    if isinstance(snapshot.room_suitability_json, dict) and snapshot.room_suitability_json.get("matched"):
        room_name = snapshot.room_suitability_json.get("room_name") or room_name

    missing_questions: list[str] | None = None
    if isinstance(snapshot.missing_fields_json, list):
        missing_questions = list(snapshot.missing_fields_json)

    recommended_action = getattr(snapshot, "recommended_action", None)

    return replace(
        context,
        room_name=room_name,
        availability_status=availability_status,
        availability_date=availability_date,
        availability_meal_period=availability_meal_period,
        confirmed_minimum_spend=confirmed_minimum_spend,
        pricing_explanation=pricing_explanation,
        missing_questions=missing_questions,
        recommended_action=recommended_action,
    )


def _build_room_lines(context: DraftContext) -> str:
    """Format room context as a multi-line string for the prompt template."""
    if not context.room_name:
        return ""
    parts = [f"Suggested space: {context.room_name}"]
    if context.room_seated_capacity:
        parts.append(f"Seated capacity: {context.room_seated_capacity}")
    if context.room_layouts:
        parts.append(f"Available layouts: {', '.join(context.room_layouts)}")
    if context.room_amenities:
        parts.append(f"Amenities: {', '.join(context.room_amenities)}")
    if context.room_suitability_notes:
        parts.append(f"Suitability: {context.room_suitability_notes}")
    if context.room_booking_url:
        parts.append(f"Booking URL: {context.room_booking_url}")
    return "\n".join(parts) + "\n"


def _extract_guest_message(notes: str | None) -> str | None:
    """Pull the guest's initial message text out of the enquiry notes string.

    The intake service stores extra fields as 'Label: value' lines in notes.
    We skip those label lines and look for longer prose that represents the
    guest's free-text message.
    """
    if not notes:
        return None
    lines = notes.strip().splitlines()
    prose_lines = [
        line for line in lines
        if line.strip() and ":" not in line[:40]
    ]
    return " ".join(prose_lines).strip() or None


def _build_subject(first_name: str, last_name: str, event_type: str | None) -> str:
    type_label = event_type.replace("_", " ").title() if event_type else "Event"
    return f"Re: {type_label} Enquiry — {first_name} {last_name}"


def _match_room(rooms: list, party_size: int | None, preferred_area: str | None) -> object | None:
    """Select the most suitable room deterministically.

    Priority:
    1. If preferred_area is set, find a room whose name contains that string (case-insensitive).
    2. Find the first room whose min_capacity <= party_size <= max_capacity, ordered by display_order.
    3. Fall back to the first active room by display_order.
    4. If no rooms exist, return None.

    This is intentionally simple — no ML, no availability checking.
    """
    if not rooms:
        return None

    # 1. Preferred area / name match
    if preferred_area:
        term = preferred_area.strip().lower()
        for room in rooms:
            if term in room.name.lower():
                return room

    # 2. Capacity match
    if party_size is not None:
        for room in rooms:
            min_cap = room.min_capacity or 1
            max_cap = room.max_capacity or room.seated_capacity or 0
            if max_cap and min_cap <= party_size <= max_cap:
                return room

    # 3. First room
    return rooms[0]


# ── Training Example Service ───────────────────────────────────────────────────


class TrainingExampleService:
    """Manages creation and retrieval of AI training examples.

    Training examples capture original LLM outputs alongside optional
    human corrections for future evaluation or fine-tuning.

    Every example must link to an existing ai_prompt_run.
    No fine-tuning or dataset export is implemented in the POC.
    """

    def __init__(self, db: Session) -> None:
        from app.modules.ai.repository import AIPromptRunRepository
        self._repo = AIPromptRunRepository(db)
        self._db = db

    def create(self, data: dict) -> object:
        """Create a training example for a given prompt run.

        Validates that the prompt_run exists.
        Populates original_output from the run's parsed_response where available.
        Raises ValueError if the prompt_run does not exist.
        """
        run_id = data.get("prompt_run_id")
        run = self._repo.get_run(run_id)
        if run is None:
            raise ValueError(f"Prompt run {run_id} not found.")

        record = {
            "prompt_run_id": run_id,
            "tenant_id": run.tenant_id,
            "prompt_key": run.prompt_key,
            "original_output": run.parsed_response,
            "corrected_output": data.get("corrected_output"),
            "correction_reason": data.get("correction_reason"),
            "quality_rating": data.get("quality_rating"),
            "approved_for_training": data.get("approved_for_training", False),
            "reviewed_by_user_id": data.get("reviewed_by_user_id"),
        }
        example = self._repo.create_training_example_from_data(record)
        self._db.commit()
        return example

    def get(self, example_id) -> object | None:
        """Return a training example by ID, or None."""
        return self._repo.get_training_example(example_id)

    def list(
        self,
        prompt_key: str | None = None,
        prompt_run_id=None,
        approved_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list, int]:
        """Return paginated training examples with optional filters."""
        return self._repo.list_training_examples(
            prompt_key=prompt_key,
            prompt_run_id=prompt_run_id,
            approved_only=approved_only,
            skip=skip,
            limit=limit,
        )


# ── Prompt Experiment Service ──────────────────────────────────────────────────


class PromptExperimentService:
    """Manages creation and retrieval of prompt experiments and their run variants.

    Experiments group ai_prompt_runs for parameter comparison without
    re-running LLM calls.  The service validates that linked prompt runs exist
    before creating experiment run records.
    """

    def __init__(self, db: Session) -> None:
        from app.modules.ai.repository import AIPromptExperimentRepository, AIPromptRunRepository
        self._repo = AIPromptExperimentRepository(db)
        self._run_repo = AIPromptRunRepository(db)
        self._db = db

    def create_experiment(self, data: dict) -> object:
        """Create a new prompt experiment.

        Raises ValueError if prompt_key is missing.
        """
        if not data.get("prompt_key"):
            raise ValueError("prompt_key is required.")
        if not data.get("name"):
            raise ValueError("name is required.")
        experiment = self._repo.create_experiment(data)
        self._db.commit()
        return experiment

    def get_experiment(self, experiment_id) -> object | None:
        """Return an experiment by ID, or None."""
        return self._repo.get_experiment(experiment_id)

    def list_experiments(
        self,
        prompt_key: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list, int]:
        """Return paginated experiments with optional filters."""
        return self._repo.list_experiments(
            prompt_key=prompt_key,
            status=status,
            skip=skip,
            limit=limit,
        )

    def add_run(self, experiment_id, data: dict) -> object:
        """Add a prompt run variant to an experiment.

        Validates that both the experiment and the linked prompt run exist.
        Raises ValueError on missing entities.
        """
        experiment = self._repo.get_experiment(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found.")

        prompt_run_id = data.get("prompt_run_id")
        prompt_run = self._run_repo.get_run(prompt_run_id)
        if prompt_run is None:
            raise ValueError(f"Prompt run {prompt_run_id} not found.")

        record = {**data, "experiment_id": experiment_id}
        exp_run = self._repo.create_experiment_run(record)
        self._db.commit()
        return exp_run

    def list_runs(self, experiment_id, skip: int = 0, limit: int = 50) -> tuple[list, int]:
        """Return paginated experiment runs for the given experiment."""
        return self._repo.list_experiment_runs(experiment_id, skip=skip, limit=limit)

    def update_run(self, experiment_id, run_id, updates: dict) -> object:
        """Update evaluator_score, reviewer_notes, or selected_as_winner on an experiment run.

        Validates that the experiment run belongs to the given experiment.
        Raises ValueError if not found or not in the experiment.
        """
        exp_run = self._repo.get_experiment_run(run_id)
        if exp_run is None:
            raise ValueError(f"Experiment run {run_id} not found.")
        if str(exp_run.experiment_id) != str(experiment_id):
            raise ValueError(f"Experiment run {run_id} does not belong to experiment {experiment_id}.")

        # Only allow safe update fields — never mutate prompt_run_id or experiment_id
        allowed = {"evaluator_score", "reviewer_notes", "selected_as_winner",
                   "variant_name", "temperature", "top_p", "top_k", "max_tokens"}
        safe_updates = {k: v for k, v in updates.items() if k in allowed}
        exp_run = self._repo.update_experiment_run(run_id, safe_updates)
        self._db.commit()
        return exp_run


# ── Prompt Run Review Service ──────────────────────────────────────────────────

# Valid score range for all Numeric quality score fields
_SCORE_MIN = 0.0
_SCORE_MAX = 5.0
_SCORE_FIELDS = {
    "accuracy_score", "tone_fit_score", "persona_fit_score",
    "commercial_quality_score", "completeness_score", "hallucination_risk_score",
}


class PromptRunReviewService:
    """Manages creation and retrieval of prompt run quality reviews.

    Reviews capture structured human scoring of LLM outputs.
    They must link to existing ai_prompt_runs and must not mutate
    the run's output or trigger new LLM calls.
    """

    def __init__(self, db: Session) -> None:
        from app.modules.ai.repository import AIPromptRunRepository, AIPromptRunReviewRepository
        self._repo = AIPromptRunReviewRepository(db)
        self._run_repo = AIPromptRunRepository(db)
        self._db = db

    def _validate_scores(self, data: dict) -> None:
        """Raise ValueError if any score field is outside the valid range."""
        for field in _SCORE_FIELDS:
            value = data.get(field)
            if value is not None and not (_SCORE_MIN <= float(value) <= _SCORE_MAX):
                raise ValueError(
                    f"{field} must be between {_SCORE_MIN} and {_SCORE_MAX}, got {value}."
                )

    def create_review(self, data: dict) -> object:
        """Create a quality review for a prompt run.

        Validates that the prompt run exists and all scores are in range.
        Raises ValueError on invalid input.
        """
        run_id = data.get("prompt_run_id")
        run = self._run_repo.get_run(run_id)
        if run is None:
            raise ValueError(f"Prompt run {run_id} not found.")
        self._validate_scores(data)
        review = self._repo.create_review(data)
        self._db.commit()
        return review

    def get_review(self, review_id) -> object | None:
        """Return a review by ID, or None."""
        return self._repo.get_review(review_id)

    def list_reviews(self, prompt_run_id, skip: int = 0, limit: int = 50) -> tuple[list, int]:
        """Return paginated reviews for a prompt run, newest-first."""
        return self._repo.list_reviews_for_run(prompt_run_id, skip=skip, limit=limit)

    def update_review(self, review_id, updates: dict) -> object:
        """Update score fields, ready_to_send, or reviewer_notes.

        Does not allow changing prompt_run_id.
        Validates score ranges.
        Raises ValueError if not found.
        """
        allowed = _SCORE_FIELDS | {"ready_to_send", "reviewer_notes", "reviewer_user_id"}
        safe_updates = {k: v for k, v in updates.items() if k in allowed}
        self._validate_scores(safe_updates)
        review = self._repo.update_review(review_id, safe_updates)
        self._db.commit()
        return review
