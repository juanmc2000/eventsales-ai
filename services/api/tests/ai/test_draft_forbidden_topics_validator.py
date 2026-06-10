"""Tests for RESP-033 — structured forbidden-topic compliance validation.

Validates that DraftComplianceValidator detects forbidden topics and returns
structured violations with code, severity, and matched_text.
"""

from __future__ import annotations

import pytest

from app.modules.ai.draft_compliance_validator import (
    DraftComplianceValidator,
    ValidationContext,
    ViolationDetail,
)


def _ctx(**kwargs) -> ValidationContext:
    defaults = dict(
        availability_contract="NOT_CHECKED",
        response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
    )
    defaults.update(kwargs)
    return ValidationContext(**defaults)


def _validate(draft: str, **kwargs) -> "ComplianceResult":  # type: ignore[name-defined]
    return DraftComplianceValidator.validate(draft, _ctx(**kwargs))


# ── ViolationDetail dataclass ─────────────────────────────────────────────────


class TestViolationDetail:
    def test_to_dict_has_all_fields(self) -> None:
        v = ViolationDetail(
            code="forbidden_topic_menu",
            severity="high",
            matched_text="menu options",
            message="Draft discusses menu.",
        )
        d = v.to_dict()
        assert set(d.keys()) == {"code", "severity", "matched_text", "message"}

    def test_fields_preserved(self) -> None:
        v = ViolationDetail(
            code="forbidden_topic_call_scheduling",
            severity="medium",
            matched_text="arrange a call",
            message="Calls not allowed.",
        )
        assert v.code == "forbidden_topic_call_scheduling"
        assert v.severity == "medium"
        assert v.matched_text == "arrange a call"


# ── ComplianceResult.structured_violations ────────────────────────────────────


class TestStructuredViolationsField:
    def test_structured_violations_empty_when_no_violations(self) -> None:
        result = _validate("Dear Alice, thank you for your enquiry. Kind regards, Eleanor")
        assert result.structured_violations == []

    def test_structured_violations_populated_for_menu_topic(self) -> None:
        result = _validate(
            "We can discuss menu options once availability is confirmed.",
            allow_menu_discussion=False,
        )
        assert len(result.structured_violations) >= 1
        codes = [v.code for v in result.structured_violations]
        assert "forbidden_topic_menu" in codes

    def test_structured_violations_have_matched_text(self) -> None:
        result = _validate(
            "We can discuss menu options for the evening.",
            allow_menu_discussion=False,
        )
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_menu"]
        assert sv
        assert sv[0].matched_text != ""

    def test_structured_violations_in_to_dict(self) -> None:
        result = _validate(
            "We can discuss menu options.",
            allow_menu_discussion=False,
        )
        d = result.to_dict()
        assert "structured_violations" in d
        assert isinstance(d["structured_violations"], list)


# ── Menu / dietary topic ──────────────────────────────────────────────────────


class TestMenuTopic:
    def test_menu_options_flagged(self) -> None:
        result = _validate(
            "We can discuss menu options once availability is confirmed.",
            allow_menu_discussion=False,
        )
        assert result.passed is False
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_menu"]
        assert sv
        assert sv[0].severity == "high"

    def test_dietary_requirements_flagged(self) -> None:
        result = _validate(
            "We are happy to accommodate dietary requirements.",
            allow_menu_discussion=False,
        )
        assert result.passed is False
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_menu"]
        assert sv

    def test_menu_passes_when_allowed(self) -> None:
        result = _validate(
            "We can discuss menu options at your convenience.",
            allow_menu_discussion=True,
        )
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_menu"]
        assert sv == []


# ── Special touches topic ─────────────────────────────────────────────────────


class TestSpecialTouchesTopic:
    def test_special_touches_flagged(self) -> None:
        result = _validate(
            "We can arrange special touches to make the evening memorable.",
            allow_special_touches=False,
        )
        assert result.passed is False
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_special_touches"]
        assert sv
        assert sv[0].severity == "medium"

    def test_decorations_flagged(self) -> None:
        result = _validate(
            "We can add decorations to personalise the space.",
            allow_special_touches=False,
        )
        assert result.passed is False

    def test_special_touches_passes_when_allowed(self) -> None:
        result = _validate(
            "We can arrange special touches for your celebration.",
            allow_special_touches=True,
        )
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_special_touches"]
        assert sv == []


# ── Call scheduling topic ─────────────────────────────────────────────────────


class TestCallSchedulingTopic:
    def test_arrange_a_call_flagged(self) -> None:
        result = _validate(
            "We would be happy to arrange a call to discuss the details.",
            allow_call_scheduling=False,
        )
        assert result.passed is False
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_call_scheduling"]
        assert sv
        assert sv[0].severity == "medium"

    def test_call_scheduling_passes_when_allowed(self) -> None:
        result = _validate(
            "We would be happy to arrange a call to discuss the details.",
            allow_call_scheduling=True,
        )
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_call_scheduling"]
        assert sv == []


# ── Timing discussion topic ───────────────────────────────────────────────────


class TestTimingDiscussionTopic:
    def test_preferred_timing_flagged(self) -> None:
        result = _validate(
            "We can discuss your preferred timing once availability is confirmed.",
            allow_timing_discussion=False,
        )
        assert result.passed is False
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_timing"]
        assert sv
        assert sv[0].severity == "high"

    def test_timing_preferences_flagged(self) -> None:
        result = _validate(
            "Please share your timing preferences when you reply.",
            allow_timing_discussion=False,
        )
        assert result.passed is False

    def test_timing_discussion_passes_when_allowed(self) -> None:
        result = _validate(
            "We can discuss your preferred timing at the next step.",
            allow_timing_discussion=True,
        )
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_timing"]
        assert sv == []


# ── Alternative dates topic ───────────────────────────────────────────────────


class TestAlternativeDatesTopic:
    def test_alternative_dates_flagged_when_not_allowed_not_checked(self) -> None:
        result = _validate(
            "Alternatively, we could explore other dates in July.",
            alternatives_allowed=False,
            availability_contract="NOT_CHECKED",
        )
        assert result.passed is False
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_alternatives"]
        assert sv
        assert sv[0].severity == "high"

    def test_alternatives_not_double_flagged_for_confirmed_unavailable(self) -> None:
        # CONFIRMED_UNAVAILABLE has its own check — the forbidden-topics check should skip
        result = _validate(
            "Alternatively, we could explore other dates.",
            alternatives_allowed=False,
            availability_contract="CONFIRMED_UNAVAILABLE",
        )
        # Only one alternatives violation (from the existing check), not two
        alt_violations = [v for v in result.violations if "alternative" in v.lower()]
        assert len(alt_violations) == 1

    def test_alternatives_pass_when_confirmed_available(self) -> None:
        # When availability is confirmed, alternatives phrasing is acceptable
        result = _validate(
            "Alternatively, we could also host a lunch event.",
            alternatives_allowed=False,
            availability_contract="CONFIRMED_AVAILABLE",
        )
        sv = [v for v in result.structured_violations if v.code == "forbidden_topic_alternatives"]
        assert sv == []

    def test_multiple_structured_violations_accumulated(self) -> None:
        result = _validate(
            "We can discuss menu options. We can arrange special touches.",
            allow_menu_discussion=False,
            allow_special_touches=False,
        )
        codes = [v.code for v in result.structured_violations]
        assert "forbidden_topic_menu" in codes
        assert "forbidden_topic_special_touches" in codes
