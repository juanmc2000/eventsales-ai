"""Persona Routing Context Builder (ORCH-005).

Deterministic service that selects the appropriate persona and tone for draft
generation based on the resolved customer type.

The draft LLM must not infer persona routing from extraction data — it should
receive a pre-built PersonaRoutingContext that the backend has already decided.

Tone guidance by customer type:
  social:    warm, friendly, celebratory
  corporate: concise, professional, efficient
  agency:    detailed, operationally precise, low-friction
  unknown:   professional (safe default)

Inputs:
  - final_customer_type: str — resolved type from CustomerTypeResolver (CUST-002)
  - final_customer_type_confidence: float — 0.0–1.0
  - customer_type_resolution_reason: str — how the type was resolved
  - assigned_personas: list of persona dicts/objects for the restaurant
    Each item must expose: id, name, tone, audience (None = default persona)

Outputs:
  PersonaRoutingContext with:
  - selected_persona_id: UUID string | None
  - selected_persona_name: str | None
  - customer_type: str
  - tone_guidance: list[str]
  - routing_reason: str

No LLM calls are made.  No database mutations are performed.

Usage::

    from app.modules.enquiries.persona_routing_context import PersonaRoutingContextBuilder

    context = PersonaRoutingContextBuilder.build(
        final_customer_type="corporate",
        final_customer_type_confidence=0.90,
        customer_type_resolution_reason="known_corporate_domain",
        assigned_personas=restaurant_personas,
    )
    # context.customer_type → "corporate"
    # context.tone_guidance → ["concise", "professional", "efficient"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Tone guidance mapping ─────────────────────────────────────────────────────

TONE_GUIDANCE: dict[str, list[str]] = {
    "social":    ["warm", "friendly", "celebratory"],
    "corporate": ["concise", "professional", "efficient"],
    "agency":    ["detailed", "operationally precise", "low-friction"],
    "unknown":   ["professional"],
}

# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class PersonaRoutingContext:
    """Outcome of PersonaRoutingContextBuilder.build().

    Attributes:
        selected_persona_id:   UUID string of the selected persona, or None.
        selected_persona_name: Display name of the selected persona, or None.
        customer_type:         Resolved customer type string.
        tone_guidance:         Ordered list of tone descriptors for the draft LLM.
        routing_reason:        Human-readable explanation of the routing decision.
    """

    customer_type: str
    tone_guidance: list[str] = field(default_factory=list)
    selected_persona_id: str | None = None
    selected_persona_name: str | None = None
    routing_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_persona_id": self.selected_persona_id,
            "selected_persona_name": self.selected_persona_name,
            "customer_type": self.customer_type,
            "tone_guidance": self.tone_guidance,
            "routing_reason": self.routing_reason,
        }


# ── Builder ────────────────────────────────────────────────────────────────────


class PersonaRoutingContextBuilder:
    """Selects the appropriate persona and tone for a resolved customer type.

    Routing logic:
      1. Find a persona whose ``audience`` matches ``final_customer_type``.
      2. If none found, fall back to the restaurant's default persona
         (``audience`` is None or empty).
      3. If no default persona exists, return tone guidance without a persona ID.
    """

    @classmethod
    def build(
        cls,
        final_customer_type: str = "unknown",
        final_customer_type_confidence: float = 0.0,
        customer_type_resolution_reason: str = "",
        assigned_personas: list[Any] | None = None,
    ) -> PersonaRoutingContext:
        """Build a PersonaRoutingContext.

        Args:
            final_customer_type:              Resolved type (social | corporate |
                                              agency | unknown).
            final_customer_type_confidence:   Confidence score 0.0–1.0.
            customer_type_resolution_reason:  How the type was resolved.
            assigned_personas:                List of persona dicts or ORM objects
                                              for the restaurant.  Each must expose
                                              ``id``, ``name``, ``tone``, and
                                              ``audience`` (None = default persona).

        Returns:
            PersonaRoutingContext.
        """
        personas = assigned_personas or []
        customer_type = final_customer_type or "unknown"
        tone_guidance = TONE_GUIDANCE.get(customer_type, TONE_GUIDANCE["unknown"])

        # ── Step 1: audience-specific match ──────────────────────────────────
        audience_persona = cls._find_audience_persona(personas, customer_type)
        if audience_persona is not None:
            persona_id = str(_get_field(audience_persona, "id") or "")
            persona_name = str(_get_field(audience_persona, "name") or "")
            persona_tone = _get_field(audience_persona, "tone")
            merged_tone = cls._merge_tone(tone_guidance, persona_tone)
            return PersonaRoutingContext(
                customer_type=customer_type,
                tone_guidance=merged_tone,
                selected_persona_id=persona_id or None,
                selected_persona_name=persona_name or None,
                routing_reason=(
                    f"Routed to {customer_type}-specific persona '{persona_name}' "
                    f"(confidence={final_customer_type_confidence:.2f}, "
                    f"method={customer_type_resolution_reason})."
                ),
            )

        # ── Step 2: default persona fallback ─────────────────────────────────
        default_persona = cls._find_default_persona(personas)
        if default_persona is not None:
            persona_id = str(_get_field(default_persona, "id") or "")
            persona_name = str(_get_field(default_persona, "name") or "")
            persona_tone = _get_field(default_persona, "tone")
            merged_tone = cls._merge_tone(tone_guidance, persona_tone)
            return PersonaRoutingContext(
                customer_type=customer_type,
                tone_guidance=merged_tone,
                selected_persona_id=persona_id or None,
                selected_persona_name=persona_name or None,
                routing_reason=(
                    f"No {customer_type}-specific persona found; "
                    f"fell back to default persona '{persona_name}'."
                ),
            )

        # ── Step 3: tone guidance only — no persona ───────────────────────────
        return PersonaRoutingContext(
            customer_type=customer_type,
            tone_guidance=tone_guidance,
            selected_persona_id=None,
            selected_persona_name=None,
            routing_reason=(
                f"No persona available for restaurant; "
                f"using {customer_type} tone guidance only."
            ),
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _find_audience_persona(personas: list[Any], customer_type: str) -> Any | None:
        """Return the first persona whose audience matches customer_type."""
        for p in personas:
            audience = _get_field(p, "audience")
            if audience and str(audience).lower() == customer_type.lower():
                return p
        return None

    @staticmethod
    def _find_default_persona(personas: list[Any]) -> Any | None:
        """Return the first persona whose audience is None/empty (the default)."""
        for p in personas:
            audience = _get_field(p, "audience")
            if not audience:
                return p
        return None

    @staticmethod
    def _merge_tone(type_tone: list[str], persona_tone: str | None) -> list[str]:
        """Prepend persona tone descriptor if it is not already in the list."""
        if not persona_tone:
            return list(type_tone)
        if persona_tone.lower() in [t.lower() for t in type_tone]:
            return list(type_tone)
        return [persona_tone] + list(type_tone)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_field(obj: Any, key: str) -> Any:
    """Get a field from a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
