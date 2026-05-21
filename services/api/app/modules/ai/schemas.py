"""Schemas for the AI draft generation module.

These schemas define the internal context object passed to the
draft generation service and the structured result returned to callers.

The raw prompt text is never included in any response schema — it is
assembled and discarded internally by the service.
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
class DraftGenerationResult:
    """Structured output of the draft generation service.

    Returned to the caller (API-009 endpoint) for further handling.
    The raw prompt is not included.
    """

    enquiry_id: uuid.UUID
    message_id: uuid.UUID           # ID of the stored EnquiryMessage
    subject: str                    # Suggested email subject line
    body: str                       # Draft response body
    persona_name: str
    is_fallback: bool               # True when generated without an LLM call
    model: str                      # Model name or "fallback"
