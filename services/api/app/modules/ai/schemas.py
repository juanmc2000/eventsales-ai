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
