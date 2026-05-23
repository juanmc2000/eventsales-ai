"""Schemas for the AI draft generation module.

These schemas define the internal context object passed to the
draft generation service and the structured result returned to callers.

The raw prompts (system_prompt, user_message) are captured by the service
and included in AIContextOut for AI transparency reporting on the webform
response page. They are never stored in the database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class DraftContext:
    """All context needed to generate a persona-based draft response.

    Assembled from the enquiry, restaurant, persona, and pricing data.
    Never serialised or exposed via the API.
    """

    enquiry_id: uuid.UUID
    guest_first_name: str
    guest_last_name: str
    event_type: str | None
    event_date: str | None          # ISO date string, e.g. "2026-08-15"
    party_size: int | None
    guest_message: str | None       # Initial message body from the guest
    restaurant_name: str
    restaurant_description: str | None
    persona_name: str
    persona_tone: str               # e.g. "warm and formal"
    persona_style: str              # e.g. "concise"
    persona_system_prompt: str      # Base persona instruction
    recommended_minimum_spend: float | None
    # Restaurant venue context (added in AI-002)
    restaurant_address: str | None = field(default=None)
    # Room/PDR context — present when a suitable room has been matched
    room_name: str | None = field(default=None)
    room_type: str | None = field(default=None)
    room_seated_capacity: int | None = field(default=None)
    room_standing_capacity: int | None = field(default=None)
    room_layouts: list[str] | None = field(default=None)
    room_amenities: list[str] | None = field(default=None)
    room_suitability_notes: str | None = field(default=None)
    room_booking_url: str | None = field(default=None)
    room_is_private_dining: bool = field(default=False)


@dataclass
class AIContextOut:
    """AI transparency context returned with every draft response.

    Captures what data and prompts were used to generate the draft.
    system_prompt and user_message are None when the fallback provider was used
    (no LLM call was made).
    """

    model: str
    is_fallback: bool
    persona_name: str | None
    persona_tone: str | None
    persona_style: str | None
    guest_message_used: str | None
    room_name: str | None
    recommended_minimum_spend: float | None
    system_prompt: str | None       # Exact system prompt sent to Claude; None for fallback
    user_message: str | None        # Exact user message sent to Claude; None for fallback
    prompt_run_id: uuid.UUID | None = field(default=None)  # ai_prompt_runs.id for this call


@dataclass
class AIGatewayRequest:
    """Input to the AI Gateway for a single LLM call.

    input_payload contains the template variables to be rendered into the
    system and user prompt templates.  It must satisfy the required_variables
    of the selected PromptDefinition.
    """

    prompt_key: str
    input_payload: dict
    tenant_id: str | None = field(default=None)
    restaurant_id: uuid.UUID | None = field(default=None)
    persona_id: uuid.UUID | None = field(default=None)
    enquiry_id: uuid.UUID | None = field(default=None)
    trigger_type: str | None = field(default=None)
    trigger_source: str | None = field(default=None)
    triggered_by_user_id: str | None = field(default=None)
    # Optional: output schema class used for structured validation (AI-005)
    output_schema: type | None = field(default=None)


@dataclass
class AIGatewayResult:
    """Typed result returned by the AI Gateway after executing a prompt run.

    Every run — including fallback runs — produces a result.
    raw_response is None for fallback runs.
    """

    run_id: uuid.UUID
    prompt_key: str
    prompt_version: int
    model_name: str
    model_provider: str
    rendered_system_prompt: str | None
    rendered_user_prompt: str | None
    raw_response: str | None
    is_fallback: bool
    fallback_reason: str | None
    validation_status: str
    latency_ms: int
    status: str
    parsed_response: dict | None = field(default=None)
    validation_errors: list | None = field(default=None)
    error_message: str | None = field(default=None)


@dataclass
class DraftGenerationResult:
    """Structured output of the draft generation service.

    Returned to the caller (API-013 endpoint) for further handling.
    """

    enquiry_id: uuid.UUID
    message_id: uuid.UUID           # ID of the stored EnquiryMessage
    subject: str                    # Suggested email subject line
    body: str                       # Draft response body
    persona_name: str
    is_fallback: bool               # True when generated without an LLM call
    model: str                      # Model name or "fallback"
    ai_context: AIContextOut | None = field(default=None)
