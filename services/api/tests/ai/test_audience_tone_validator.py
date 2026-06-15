"""Tests for AudienceToneValidator (RESP-075).

Validates:
- Corporate responses fail when they contain social warmth patterns
- Agency responses fail on the same patterns as corporate
- Luxury responses fail on casual / enthusiastic language
- Social responses always pass (celebratory language is allowed)
- Unknown audience always passes (neutral fallback, no restrictions)
- Violation code is prefixed with 'audience_tone_violation:'
- Unrecognised audience types fall back to unknown (no restrictions)
"""

from __future__ import annotations

import pytest

from app.modules.ai.audience_tone_validator import AudienceToneValidator, ToneValidationResult


# ── Helpers ───────────────────────────────────────────────────────────────────


def _validate(draft: str, audience: str) -> ToneValidationResult:
    return AudienceToneValidator.validate(draft, audience)


# ── Corporate ─────────────────────────────────────────────────────────────────


class TestCorporateTone:
    def test_how_wonderful_fails_corporate(self) -> None:
        result = _validate(
            "How wonderful — a board dinner is such an important occasion.",
            "corporate",
        )
        assert result.passed is False
        assert any("audience_tone_violation" in v for v in result.violations)
        assert any("how wonderful" in v for v in result.violations)

    def test_how_lovely_fails_corporate(self) -> None:
        result = _validate(
            "How lovely — we would be delighted to host your team dinner.",
            "corporate",
        )
        assert result.passed is False
        assert any("how lovely" in v for v in result.violations)

    def test_such_a_special_occasion_fails_corporate(self) -> None:
        result = _validate(
            "I'm pleased to confirm — this is such a special occasion for your team.",
            "corporate",
        )
        assert result.passed is False
        assert any("such a special occasion" in v for v in result.violations)

    def test_such_a_meaningful_occasion_fails_corporate(self) -> None:
        result = _validate(
            "A board dinner is such a meaningful occasion.",
            "corporate",
        )
        assert result.passed is False
        assert any("such a meaningful occasion" in v for v in result.violations)

    def test_celebration_with_us_fails_corporate(self) -> None:
        result = _validate(
            "We look forward to your celebration with us.",
            "corporate",
        )
        assert result.passed is False
        assert any("celebration with us" in v for v in result.violations)

    def test_will_be_special_fails_corporate(self) -> None:
        result = _validate(
            "We're sure the evening will be special.",
            "corporate",
        )
        assert result.passed is False
        assert any("will be special" in v for v in result.violations)

    def test_thrilled_fails_corporate(self) -> None:
        result = _validate(
            "We are thrilled to confirm availability for your event.",
            "corporate",
        )
        assert result.passed is False
        assert any("thrilled" in v for v in result.violations)

    def test_professional_response_passes_corporate(self) -> None:
        result = _validate(
            "Thank you for your enquiry. I'm pleased to confirm that we have "
            "availability for dinner on 12 July 2026.\n\n"
            "Please note that our minimum spend for this space is £2,000.\n\n"
            "Please reply to this email to confirm you would like to proceed, "
            "and our events team will be in touch to finalise the booking.\n\n"
            "Warm regards,\nEleanor",
            "corporate",
        )
        assert result.passed is True
        assert result.violations == []

    def test_violation_identifies_audience_type(self) -> None:
        result = _validate("How wonderful — a client dinner!", "corporate")
        assert result.audience_type == "corporate"
        assert any("corporate" in v for v in result.violations)

    def test_case_insensitive_match(self) -> None:
        result = _validate("HOW WONDERFUL — amazing news.", "corporate")
        assert result.passed is False

    def test_multiple_violations_all_reported(self) -> None:
        result = _validate(
            "How wonderful — how lovely — thrilled to help!",
            "corporate",
        )
        assert result.passed is False
        assert len(result.violations) >= 2


# ── Agency ────────────────────────────────────────────────────────────────────


class TestAgencyTone:
    def test_how_wonderful_fails_agency(self) -> None:
        result = _validate(
            "How wonderful — we'd love to host your client dinner.",
            "agency",
        )
        assert result.passed is False
        assert any("how wonderful" in v for v in result.violations)

    def test_how_lovely_fails_agency(self) -> None:
        result = _validate(
            "How lovely — a corporate dinner for 20 sounds perfect.",
            "agency",
        )
        assert result.passed is False
        assert any("how lovely" in v for v in result.violations)

    def test_operational_response_passes_agency(self) -> None:
        result = _validate(
            "Thank you for your enquiry. I can confirm that we have availability "
            "for dinner on 14 July 2026.\n\n"
            "Please note that our minimum spend for this space is £3,000.\n\n"
            "Please reply to this email to confirm you would like to proceed.",
            "agency",
        )
        assert result.passed is True

    def test_violation_identifies_agency_audience(self) -> None:
        result = _validate("How wonderful — a great event!", "agency")
        assert result.audience_type == "agency"
        assert any("agency" in v for v in result.violations)


# ── Luxury ────────────────────────────────────────────────────────────────────


class TestLuxuryTone:
    def test_amazing_fails_luxury(self) -> None:
        result = _validate(
            "This is amazing — we would love to host your private dinner.",
            "luxury",
        )
        assert result.passed is False
        assert any("amazing" in v for v in result.violations)

    def test_fantastic_fails_luxury(self) -> None:
        result = _validate(
            "Fantastic news — we have availability for your event!",
            "luxury",
        )
        assert result.passed is False
        assert any("fantastic" in v for v in result.violations)

    def test_brilliant_fails_luxury(self) -> None:
        result = _validate(
            "Brilliant — we'd be happy to accommodate your dinner.",
            "luxury",
        )
        assert result.passed is False
        assert any("brilliant" in v for v in result.violations)

    def test_cant_wait_fails_luxury(self) -> None:
        result = _validate(
            "We can't wait to welcome your guests.",
            "luxury",
        )
        assert result.passed is False
        assert any("can't wait" in v for v in result.violations)

    def test_refined_response_passes_luxury(self) -> None:
        result = _validate(
            "Thank you for your enquiry. It would be a pleasure to welcome your guests — "
            "I'm pleased to confirm availability for dinner on 13 August 2026.\n\n"
            "Please note that our minimum spend for this space is £2,000.\n\n"
            "Please reply to this email to confirm you would like to proceed, "
            "and our events team will be in touch to finalise the booking.\n\n"
            "Warm regards,\nEleanor",
            "luxury",
        )
        assert result.passed is True

    def test_how_wonderful_is_not_forbidden_for_luxury(self) -> None:
        # Luxury rules are softer — "How wonderful" is corporate/agency specific
        result = _validate("How wonderful — we look forward to your visit.", "luxury")
        # "how wonderful" is not in the luxury forbidden list
        assert result.passed is True

    def test_violation_identifies_luxury_audience(self) -> None:
        result = _validate("This is amazing news!", "luxury")
        assert result.audience_type == "luxury"
        assert any("luxury" in v for v in result.violations)


# ── Social ────────────────────────────────────────────────────────────────────


class TestSocialTone:
    def test_how_wonderful_passes_social(self) -> None:
        result = _validate(
            "How wonderful — a birthday celebration with us!",
            "social",
        )
        assert result.passed is True
        assert result.violations == []

    def test_how_lovely_passes_social(self) -> None:
        result = _validate(
            "How lovely — an engagement dinner is such a special occasion.",
            "social",
        )
        assert result.passed is True

    def test_celebration_language_passes_social(self) -> None:
        result = _validate(
            "I'm delighted to confirm that we have availability for dinner on 19 July 2026. "
            "How wonderful to be celebrating your birthday with us!",
            "social",
        )
        assert result.passed is True

    def test_social_result_has_no_violations(self) -> None:
        result = _validate("How wonderful — what a lovely occasion!", "social")
        assert result.violations == []


# ── Unknown ───────────────────────────────────────────────────────────────────


class TestUnknownTone:
    def test_unknown_always_passes(self) -> None:
        result = _validate(
            "How wonderful — I'm thrilled to confirm availability.",
            "unknown",
        )
        assert result.passed is True
        assert result.violations == []

    def test_unrecognised_audience_treated_as_unknown(self) -> None:
        result = _validate(
            "How wonderful — a spectacular event!",
            "not_a_real_type",
        )
        assert result.passed is True

    def test_none_audience_treated_as_unknown(self) -> None:
        result = _validate("How wonderful!", None)
        assert result.passed is True

    def test_empty_audience_treated_as_unknown(self) -> None:
        result = _validate("How wonderful!", "")
        assert result.passed is True


# ── Result structure ──────────────────────────────────────────────────────────


class TestResultStructure:
    def test_passed_result_has_empty_violations(self) -> None:
        result = _validate("Professional response here.", "corporate")
        assert result.passed is True
        assert result.violations == []

    def test_failed_result_has_non_empty_violations(self) -> None:
        result = _validate("How wonderful — great!", "corporate")
        assert result.passed is False
        assert len(result.violations) > 0

    def test_violation_string_format(self) -> None:
        result = _validate("How wonderful!", "corporate")
        assert any(v.startswith("audience_tone_violation:") for v in result.violations)

    def test_audience_type_preserved_in_result(self) -> None:
        for aud in ("corporate", "agency", "luxury", "social", "unknown"):
            result = _validate("Some draft text.", aud)
            assert result.audience_type == aud

    def test_empty_draft_returns_passed(self) -> None:
        # Empty draft has no violations
        result = _validate("", "corporate")
        assert result.passed is True

    def test_none_draft_returns_passed(self) -> None:
        result = _validate(None, "corporate")
        assert result.passed is True

    def test_no_llm_calls_in_module(self) -> None:
        import app.modules.ai.audience_tone_validator as mod
        source = open(mod.__file__).read()
        assert "AIGateway" not in source
        assert "anthropic" not in source
        assert "client.messages" not in source
