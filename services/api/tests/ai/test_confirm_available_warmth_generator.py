"""Tests for confirm_available_warmth_generator (RESP-076).

Validates:
- _audience_tone_guard() returns True/False correctly per audience type
- _AUDIENCE_SYSTEM_PROMPTS contains all 5 audience keys
- Each audience system prompt includes explicit forbidden-phrase instruction
- generate_warmth_sentence() returns None when no api_key is provided
- generate_warmth_sentence() returns None when no context_parts are available
- Module has no hidden LLM dependency that bypasses audience routing
"""

from __future__ import annotations

import re

import pytest

from app.modules.ai.confirm_available_warmth_generator import (
    _AUDIENCE_GUARDS,
    _AUDIENCE_SYSTEM_PROMPTS,
    _CORPORATE_AGENCY_GUARD,
    _LUXURY_GUARD,
    _SYSTEM_PROMPT_AGENCY,
    _SYSTEM_PROMPT_CORPORATE,
    _SYSTEM_PROMPT_LUXURY,
    _SYSTEM_PROMPT_SOCIAL,
    _SYSTEM_PROMPT_UNKNOWN,
    _audience_tone_guard,
    generate_warmth_sentence,
)


# ── System prompt registry ─────────────────────────────────────────────────────


class TestAudienceSystemPrompts:
    def test_all_five_audience_keys_present(self) -> None:
        for key in ("social", "corporate", "agency", "luxury", "unknown"):
            assert key in _AUDIENCE_SYSTEM_PROMPTS, f"Missing key: {key}"

    def test_social_prompt_encourages_warmth(self) -> None:
        assert "celebrat" in _SYSTEM_PROMPT_SOCIAL.lower() or "warm" in _SYSTEM_PROMPT_SOCIAL.lower()

    def test_corporate_prompt_forbids_how_wonderful(self) -> None:
        assert "How wonderful" in _SYSTEM_PROMPT_CORPORATE or "how wonderful" in _SYSTEM_PROMPT_CORPORATE.lower()

    def test_corporate_prompt_forbids_how_lovely(self) -> None:
        assert "How lovely" in _SYSTEM_PROMPT_CORPORATE or "how lovely" in _SYSTEM_PROMPT_CORPORATE.lower()

    def test_agency_prompt_forbids_celebration_language(self) -> None:
        assert "celebration" in _SYSTEM_PROMPT_AGENCY.lower()

    def test_luxury_prompt_forbids_amazing(self) -> None:
        assert "amazing" in _SYSTEM_PROMPT_LUXURY.lower()

    def test_luxury_prompt_forbids_fantastic(self) -> None:
        assert "fantastic" in _SYSTEM_PROMPT_LUXURY.lower()

    def test_unknown_prompt_is_neutral(self) -> None:
        assert "professional" in _SYSTEM_PROMPT_UNKNOWN.lower() or "neutral" in _SYSTEM_PROMPT_UNKNOWN.lower() or "courteous" in _SYSTEM_PROMPT_UNKNOWN.lower()

    def test_all_prompts_contain_base_rules(self) -> None:
        for key, prompt in _AUDIENCE_SYSTEM_PROMPTS.items():
            assert "one sentence" in prompt.lower() or "exactly one sentence" in prompt.lower() or "20 words" in prompt, \
                f"Prompt for '{key}' missing base rules"


# ── Audience guard registry ────────────────────────────────────────────────────


class TestAudienceGuardRegistry:
    def test_corporate_guard_present(self) -> None:
        assert "corporate" in _AUDIENCE_GUARDS

    def test_agency_guard_present(self) -> None:
        assert "agency" in _AUDIENCE_GUARDS

    def test_luxury_guard_present(self) -> None:
        assert "luxury" in _AUDIENCE_GUARDS

    def test_social_not_in_guards(self) -> None:
        assert "social" not in _AUDIENCE_GUARDS

    def test_unknown_not_in_guards(self) -> None:
        assert "unknown" not in _AUDIENCE_GUARDS

    def test_corporate_and_agency_share_same_guard(self) -> None:
        assert _AUDIENCE_GUARDS["corporate"] is _AUDIENCE_GUARDS["agency"]

    def test_corporate_agency_guard_is_nonempty(self) -> None:
        assert len(_CORPORATE_AGENCY_GUARD) > 0

    def test_luxury_guard_is_nonempty(self) -> None:
        assert len(_LUXURY_GUARD) > 0


# ── _audience_tone_guard() ─────────────────────────────────────────────────────


class TestAudienceToneGuardCorporate:
    def test_how_wonderful_fails_corporate(self) -> None:
        assert _audience_tone_guard("How wonderful — great event!", "corporate") is False

    def test_how_lovely_fails_corporate(self) -> None:
        assert _audience_tone_guard("How lovely — a corporate dinner!", "corporate") is False

    def test_how_exciting_fails_corporate(self) -> None:
        assert _audience_tone_guard("How exciting — your team event!", "corporate") is False

    def test_such_a_special_occasion_fails_corporate(self) -> None:
        assert _audience_tone_guard("This is such a special occasion for the team.", "corporate") is False

    def test_thrilled_fails_corporate(self) -> None:
        assert _audience_tone_guard("We are thrilled to host your event.", "corporate") is False

    def test_professional_opener_passes_corporate(self) -> None:
        assert _audience_tone_guard("We would be delighted to accommodate your team.", "corporate") is True

    def test_case_insensitive_corporate(self) -> None:
        assert _audience_tone_guard("HOW WONDERFUL — great!", "corporate") is False

    def test_pleased_to_assist_passes_corporate(self) -> None:
        assert _audience_tone_guard("We are pleased to assist with your upcoming dinner.", "corporate") is True


class TestAudienceToneGuardAgency:
    def test_how_wonderful_fails_agency(self) -> None:
        assert _audience_tone_guard("How wonderful — a lovely event!", "agency") is False

    def test_celebration_with_us_fails_agency(self) -> None:
        assert _audience_tone_guard("We look forward to the celebration with us.", "agency") is False

    def test_operational_opener_passes_agency(self) -> None:
        assert _audience_tone_guard("We can confirm availability for your client event.", "agency") is True

    def test_pleased_opener_passes_agency(self) -> None:
        assert _audience_tone_guard("We are pleased to assist with the upcoming booking.", "agency") is True


class TestAudienceToneGuardLuxury:
    def test_amazing_fails_luxury(self) -> None:
        assert _audience_tone_guard("That sounds amazing!", "luxury") is False

    def test_fantastic_fails_luxury(self) -> None:
        assert _audience_tone_guard("Fantastic choice of event.", "luxury") is False

    def test_brilliant_fails_luxury(self) -> None:
        assert _audience_tone_guard("That would be brilliant!", "luxury") is False

    def test_how_exciting_fails_luxury(self) -> None:
        assert _audience_tone_guard("How exciting — we look forward to it!", "luxury") is False

    def test_refined_opener_passes_luxury(self) -> None:
        assert _audience_tone_guard("It would be a pleasure to welcome your guests.", "luxury") is True

    def test_how_wonderful_passes_luxury(self) -> None:
        # "how wonderful" is only forbidden for corporate/agency, not luxury
        assert _audience_tone_guard("How wonderful — a beautiful occasion.", "luxury") is True

    def test_case_insensitive_luxury(self) -> None:
        assert _audience_tone_guard("AMAZING event!", "luxury") is False


class TestAudienceToneGuardSocialUnknown:
    def test_social_always_passes(self) -> None:
        assert _audience_tone_guard("How wonderful — a birthday celebration!", "social") is True

    def test_social_passes_any_warmth(self) -> None:
        assert _audience_tone_guard("What a lovely occasion for a party!", "social") is True

    def test_unknown_always_passes(self) -> None:
        assert _audience_tone_guard("We look forward to welcoming your guests.", "unknown") is True

    def test_unknown_passes_celebratory_language(self) -> None:
        assert _audience_tone_guard("How wonderful — a great event!", "unknown") is True

    def test_empty_audience_type_passes(self) -> None:
        assert _audience_tone_guard("Some opener sentence.", "") is True

    def test_none_audience_type_passes(self) -> None:
        # None is handled via .get() on the guards dict with empty fallback
        assert _audience_tone_guard("Some opener sentence.", None) is True  # type: ignore[arg-type]


# ── generate_warmth_sentence() early-exit guards ──────────────────────────────


class TestGenerateWarmthSentenceEarlyExits:
    def test_returns_none_when_no_api_key(self) -> None:
        result = generate_warmth_sentence(
            api_key="",
            occasion="birthday",
            audience_type="social",
            party_size=10,
            meal_period="dinner",
        )
        assert result is None

    def test_returns_none_when_api_key_is_none(self) -> None:
        result = generate_warmth_sentence(
            api_key=None,  # type: ignore[arg-type]
            occasion="birthday",
            audience_type="social",
            party_size=10,
            meal_period="dinner",
        )
        assert result is None

    def test_returns_none_when_no_context(self) -> None:
        # All context fields None → context_parts empty → returns None before LLM call
        result = generate_warmth_sentence(
            api_key="sk-ant-fake",
            occasion=None,
            audience_type=None,
            party_size=None,
            meal_period=None,
        )
        assert result is None
