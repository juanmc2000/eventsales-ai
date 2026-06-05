"""Tests for PersonaRoutingContextBuilder (ORCH-005)."""

from __future__ import annotations

import uuid

import pytest

from app.modules.enquiries.persona_routing_context import (
    TONE_GUIDANCE,
    PersonaRoutingContext,
    PersonaRoutingContextBuilder,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _persona(name: str, audience: str | None = None, tone: str = "professional") -> dict:
    return {"id": str(uuid.uuid4()), "name": name, "audience": audience, "tone": tone}


def _social_persona():
    return _persona("Bella", audience="social", tone="warm")


def _corporate_persona():
    return _persona("Alex", audience="corporate", tone="professional")


def _agency_persona():
    return _persona("Jordan", audience="agency", tone="precise")


def _default_persona():
    return _persona("Sam", audience=None, tone="professional")


# ── PersonaRoutingContext ─────────────────────────────────────────────────────


def test_to_dict_has_all_keys():
    c = PersonaRoutingContext(customer_type="social")
    assert set(c.to_dict().keys()) == {
        "selected_persona_id",
        "selected_persona_name",
        "customer_type",
        "tone_guidance",
        "routing_reason",
    }


# ── TONE_GUIDANCE ─────────────────────────────────────────────────────────────


def test_tone_guidance_has_all_four_types():
    assert set(TONE_GUIDANCE.keys()) == {"social", "corporate", "agency", "unknown"}


def test_social_tone_includes_warm():
    assert "warm" in TONE_GUIDANCE["social"]


def test_corporate_tone_includes_professional():
    assert "professional" in TONE_GUIDANCE["corporate"]


def test_agency_tone_includes_detailed():
    assert "detailed" in TONE_GUIDANCE["agency"]


# ── Social routing ────────────────────────────────────────────────────────────


def test_social_routes_to_social_persona():
    personas = [_social_persona(), _corporate_persona(), _default_persona()]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="social",
        assigned_personas=personas,
    )
    assert ctx.customer_type == "social"
    assert ctx.selected_persona_name == "Bella"
    assert "warm" in ctx.tone_guidance


def test_social_routing_reason_mentions_persona_name():
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="social",
        assigned_personas=[_social_persona()],
    )
    assert "Bella" in ctx.routing_reason


# ── Corporate routing ─────────────────────────────────────────────────────────


def test_corporate_routes_to_corporate_persona():
    personas = [_social_persona(), _corporate_persona(), _default_persona()]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="corporate",
        assigned_personas=personas,
    )
    assert ctx.selected_persona_name == "Alex"
    assert "professional" in ctx.tone_guidance


# ── Agency routing ────────────────────────────────────────────────────────────


def test_agency_routes_to_agency_persona():
    personas = [_agency_persona(), _default_persona()]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="agency",
        assigned_personas=personas,
    )
    assert ctx.selected_persona_name == "Jordan"
    assert "detailed" in ctx.tone_guidance


# ── Default persona fallback ──────────────────────────────────────────────────


def test_falls_back_to_default_when_no_audience_match():
    personas = [_default_persona()]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="corporate",
        assigned_personas=personas,
    )
    assert ctx.selected_persona_name == "Sam"
    assert "fell back to default" in ctx.routing_reason.lower()


def test_falls_back_to_default_for_unknown_type():
    personas = [_default_persona()]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="unknown",
        assigned_personas=personas,
    )
    assert ctx.selected_persona_name == "Sam"


# ── No persona available ──────────────────────────────────────────────────────


def test_no_personas_returns_tone_guidance_only():
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="social",
        assigned_personas=[],
    )
    assert ctx.selected_persona_id is None
    assert ctx.selected_persona_name is None
    assert "warm" in ctx.tone_guidance
    assert "No persona available" in ctx.routing_reason


def test_none_personas_returns_tone_guidance_only():
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="corporate",
        assigned_personas=None,
    )
    assert ctx.selected_persona_id is None
    assert "professional" in ctx.tone_guidance


# ── ORM-style objects ─────────────────────────────────────────────────────────


class _FakePersona:
    def __init__(self, name: str, audience: str | None, tone: str = "professional") -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.audience = audience
        self.tone = tone


def test_orm_style_objects_work():
    personas = [_FakePersona("ORM Persona", audience="social", tone="warm")]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="social",
        assigned_personas=personas,
    )
    assert ctx.selected_persona_name == "ORM Persona"
    assert "warm" in ctx.tone_guidance


# ── Unknown customer type ─────────────────────────────────────────────────────


def test_unknown_type_with_no_audience_match_uses_default():
    personas = [_default_persona()]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="unknown",
        assigned_personas=personas,
    )
    assert ctx.customer_type == "unknown"
    assert "professional" in ctx.tone_guidance


# ── Tone merging ──────────────────────────────────────────────────────────────


def test_persona_tone_prepended_if_not_already_present():
    personas = [_persona("Test", audience="social", tone="elegant")]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="social",
        assigned_personas=personas,
    )
    assert ctx.tone_guidance[0] == "elegant"
    assert "warm" in ctx.tone_guidance


def test_persona_tone_not_duplicated_if_already_present():
    personas = [_persona("Test", audience="social", tone="warm")]
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="social",
        assigned_personas=personas,
    )
    assert ctx.tone_guidance.count("warm") == 1


# ── Confidence and reason ─────────────────────────────────────────────────────


def test_routing_reason_mentions_confidence():
    ctx = PersonaRoutingContextBuilder.build(
        final_customer_type="corporate",
        final_customer_type_confidence=0.90,
        customer_type_resolution_reason="known_corporate_domain",
        assigned_personas=[_corporate_persona()],
    )
    assert "0.90" in ctx.routing_reason
    assert "known_corporate_domain" in ctx.routing_reason
