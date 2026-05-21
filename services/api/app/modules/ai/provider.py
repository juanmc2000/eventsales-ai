"""
AI draft generation providers.

FallbackProvider: deterministic hospitality template, no API call required.
AnthropicProvider: calls claude-haiku-4-5-20251001, falls back on error.

AI-001: Persona-Based Draft Response Generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class DraftContext:
    enquiry_id: object  # uuid.UUID
    guest_first_name: str
    guest_last_name: str
    event_type: str | None
    event_date: str | None
    party_size: int | None
    guest_message: str | None
    restaurant_name: str
    restaurant_description: str | None
    persona_name: str
    persona_tone: str
    persona_style: str
    persona_system_prompt: str
    recommended_minimum_spend: float | None


@runtime_checkable
class LLMProvider(Protocol):
    @property
    def model_name(self) -> str: ...
    def generate(self, context: DraftContext) -> str: ...


class FallbackProvider:
    """Deterministic hospitality template. No API key required."""

    model_name = "fallback-template-v1"

    def generate(self, context: DraftContext) -> str:
        spend_line = ""
        if context.recommended_minimum_spend:
            spend_line = (
                f"\n\nBased on your event details, we recommend a minimum spend of "
                f"£{context.recommended_minimum_spend:,.0f}."
            )

        event_line = ""
        if context.event_type or context.event_date or context.party_size:
            parts = []
            if context.event_type:
                parts.append(context.event_type)
            if context.party_size:
                parts.append(f"{context.party_size} guests")
            if context.event_date:
                parts.append(f"on {context.event_date}")
            event_line = f" for your {', '.join(parts)}" if parts else ""

        return (
            f"Dear {context.guest_first_name},\n\n"
            f"Thank you for your enquiry{event_line} at {context.restaurant_name}.\n\n"
            f"We would love to host your event and will be in touch shortly with "
            f"a tailored proposal.{spend_line}\n\n"
            f"Warm regards,\n{context.persona_name}\n{context.restaurant_name}"
        )


def make_provider(api_key: str) -> tuple[LLMProvider, bool]:
    """
    Return (provider, is_fallback).

    Uses FallbackProvider when api_key is empty. Otherwise attempts
    AnthropicProvider and falls back on error.
    """
    if not api_key:
        return FallbackProvider(), True
    try:
        from app.modules.ai._anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key), False
    except Exception:
        return FallbackProvider(), True
