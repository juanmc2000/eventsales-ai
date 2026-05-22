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
