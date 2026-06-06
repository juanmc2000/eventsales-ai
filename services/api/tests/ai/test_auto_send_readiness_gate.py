"""Tests for RESP-014 — Auto-Send Readiness Gate.

Validates:
- auto_send_allowed True when all conditions pass
- Draft compliance failure blocks auto-send
- Non-auto-sendable goals block auto-send
- Ambiguous or unknown date status blocks auto-send
- ESCALATE_TO_HUMAN goal blocks auto-send
- Multiple blockers all captured
- to_dict returns expected keys
- RESPOND_UNAVAILABLE and REQUEST_WEBFORM are blocked
"""

from __future__ import annotations

import pytest

from app.modules.ai.auto_send_readiness_gate import (
    AutoSendReadinessGate,
    AutoSendReadinessResult,
    _AUTO_SEND_GOALS,
)
from app.modules.ai.draft_compliance_validator import ComplianceResult


# ── Helpers ────────────────────────────────────────────────────────────────────


def _passing_compliance() -> ComplianceResult:
    return ComplianceResult(passed=True, violations=[], unsafe_to_send=False)


def _failing_compliance(violations: list[str] | None = None) -> ComplianceResult:
    v = violations or ["Draft confirmed availability when contract is NOT_CHECKED."]
    return ComplianceResult(passed=False, violations=v, unsafe_to_send=True)


def _evaluate(
    response_goal: str = "CONFIRM_AVAILABLE",
    compliance: ComplianceResult | None = None,
    date_status: str = "resolved",
    **kwargs,
) -> AutoSendReadinessResult:
    return AutoSendReadinessGate.evaluate(
        response_goal=response_goal,
        draft_compliance_result=compliance or _passing_compliance(),
        date_status=date_status,
        **kwargs,
    )


# ── AutoSendReadinessResult dataclass ─────────────────────────────────────────


class TestAutoSendReadinessResult:
    def test_to_dict_has_expected_keys(self) -> None:
        result = AutoSendReadinessResult(
            auto_send_allowed=True,
            auto_send_blockers=[],
            review_required_reason="",
        )
        d = result.to_dict()
        assert set(d.keys()) == {"auto_send_allowed", "auto_send_blockers", "review_required_reason"}

    def test_allowed_result(self) -> None:
        result = AutoSendReadinessResult(auto_send_allowed=True, auto_send_blockers=[], review_required_reason="")
        assert result.auto_send_allowed is True
        assert result.auto_send_blockers == []
        assert result.review_required_reason == ""

    def test_blocked_result(self) -> None:
        result = AutoSendReadinessResult(
            auto_send_allowed=False,
            auto_send_blockers=["Draft failed compliance."],
            review_required_reason="Draft failed compliance.",
        )
        assert result.auto_send_allowed is False
        assert len(result.auto_send_blockers) == 1


# ── Happy path: all conditions pass ───────────────────────────────────────────


class TestAutoSendAllowed:
    @pytest.mark.parametrize("goal", sorted(_AUTO_SEND_GOALS))
    def test_allowed_for_each_auto_send_goal(self, goal: str) -> None:
        result = _evaluate(response_goal=goal, date_status="resolved")
        assert result.auto_send_allowed is True
        assert result.auto_send_blockers == []

    def test_review_required_reason_empty_when_allowed(self) -> None:
        result = _evaluate(response_goal="CONFIRM_AVAILABLE")
        assert result.review_required_reason == ""

    def test_allowed_with_resolved_with_confirmation_date_status(self) -> None:
        result = _evaluate(response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY", date_status="resolved_with_confirmation")
        assert result.auto_send_allowed is True

    def test_allowed_when_customer_type_confidence_low(self) -> None:
        # Low confidence does not block auto-send in initial rules
        result = _evaluate(
            response_goal="CONFIRM_AVAILABLE",
            customer_type_confidence=0.1,
        )
        assert result.auto_send_allowed is True


# ── Rule 1: draft compliance ───────────────────────────────────────────────────


class TestComplianceRule:
    def test_blocked_when_compliance_fails(self) -> None:
        result = _evaluate(
            response_goal="CONFIRM_AVAILABLE",
            compliance=_failing_compliance(),
        )
        assert result.auto_send_allowed is False
        assert any("compliance" in b.lower() for b in result.auto_send_blockers)

    def test_blocker_includes_violation_text(self) -> None:
        violation = "Draft confirmed availability when NOT_CHECKED."
        result = _evaluate(
            response_goal="CONFIRM_AVAILABLE",
            compliance=_failing_compliance(violations=[violation]),
        )
        assert any(violation in b for b in result.auto_send_blockers)

    def test_allowed_when_compliance_passes(self) -> None:
        result = _evaluate(
            response_goal="CONFIRM_AVAILABLE",
            compliance=_passing_compliance(),
        )
        assert result.auto_send_allowed is True


# ── Rule 2: response goal ──────────────────────────────────────────────────────


class TestResponseGoalRule:
    @pytest.mark.parametrize("goal", [
        "RESPOND_UNAVAILABLE",
        "REQUEST_WEBFORM",
        "ESCALATE_TO_HUMAN",
        "REQUEST_DATE_CONFIRMATION",
        "UNKNOWN_GOAL",
    ])
    def test_blocked_for_non_auto_send_goals(self, goal: str) -> None:
        result = _evaluate(response_goal=goal)
        assert result.auto_send_allowed is False
        # Must have a blocker about the goal OR escalation
        assert len(result.auto_send_blockers) >= 1

    def test_blocker_names_the_goal(self) -> None:
        result = _evaluate(response_goal="RESPOND_UNAVAILABLE")
        assert any("RESPOND_UNAVAILABLE" in b for b in result.auto_send_blockers)

    def test_blocker_lists_allowed_goals(self) -> None:
        result = _evaluate(response_goal="RESPOND_UNAVAILABLE")
        blocker_text = " ".join(result.auto_send_blockers)
        # At least one auto-send goal should be mentioned
        assert any(goal in blocker_text for goal in _AUTO_SEND_GOALS)


# ── Rule 3: date status ────────────────────────────────────────────────────────


class TestDateStatusRule:
    def test_blocked_when_date_ambiguous(self) -> None:
        result = _evaluate(response_goal="CONFIRM_AVAILABLE", date_status="ambiguous")
        assert result.auto_send_allowed is False
        assert any("ambiguous" in b.lower() for b in result.auto_send_blockers)

    def test_blocked_when_date_unknown(self) -> None:
        result = _evaluate(response_goal="CONFIRM_AVAILABLE", date_status="unknown")
        assert result.auto_send_allowed is False
        assert any("unknown" in b.lower() for b in result.auto_send_blockers)

    def test_allowed_when_date_resolved(self) -> None:
        result = _evaluate(response_goal="CONFIRM_AVAILABLE", date_status="resolved")
        assert result.auto_send_allowed is True

    def test_allowed_when_date_resolved_with_confirmation(self) -> None:
        result = _evaluate(response_goal="CONFIRM_AVAILABLE", date_status="resolved_with_confirmation")
        assert result.auto_send_allowed is True

    def test_blocker_includes_date_status_value(self) -> None:
        result = _evaluate(response_goal="CONFIRM_AVAILABLE", date_status="ambiguous")
        assert any("ambiguous" in b for b in result.auto_send_blockers)


# ── Rule 4: no escalation ──────────────────────────────────────────────────────


class TestEscalationRule:
    def test_blocked_when_goal_is_escalate_to_human(self) -> None:
        result = _evaluate(response_goal="ESCALATE_TO_HUMAN")
        assert result.auto_send_allowed is False
        assert any("escalate" in b.lower() or "human" in b.lower() for b in result.auto_send_blockers)

    def test_escalate_produces_two_blockers(self) -> None:
        # ESCALATE_TO_HUMAN fails both rule 2 (not in auto-send goals) and rule 4 (escalation check)
        result = _evaluate(response_goal="ESCALATE_TO_HUMAN")
        assert len(result.auto_send_blockers) >= 2


# ── Multiple blockers ──────────────────────────────────────────────────────────


class TestMultipleBlockers:
    def test_all_blockers_captured_together(self) -> None:
        # Compliance failure + non-auto-send goal + ambiguous date = 3 blockers
        result = _evaluate(
            response_goal="RESPOND_UNAVAILABLE",
            compliance=_failing_compliance(),
            date_status="ambiguous",
        )
        assert result.auto_send_allowed is False
        assert len(result.auto_send_blockers) >= 2

    def test_review_required_reason_summarises_blockers(self) -> None:
        result = _evaluate(
            response_goal="RESPOND_UNAVAILABLE",
            compliance=_failing_compliance(),
        )
        assert result.review_required_reason != ""
        assert len(result.review_required_reason) > 0


# ── Specific goal coverage ─────────────────────────────────────────────────────


class TestGoalCoverage:
    def test_respond_unavailable_blocked(self) -> None:
        result = _evaluate(response_goal="RESPOND_UNAVAILABLE")
        assert result.auto_send_allowed is False

    def test_request_webform_blocked(self) -> None:
        result = _evaluate(response_goal="REQUEST_WEBFORM")
        assert result.auto_send_allowed is False

    def test_request_date_confirmation_blocked(self) -> None:
        result = _evaluate(response_goal="REQUEST_DATE_CONFIRMATION")
        assert result.auto_send_allowed is False

    def test_confirm_available_allowed(self) -> None:
        result = _evaluate(response_goal="CONFIRM_AVAILABLE")
        assert result.auto_send_allowed is True

    def test_acknowledge_and_check_allowed(self) -> None:
        result = _evaluate(response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert result.auto_send_allowed is True

    def test_request_missing_information_allowed(self) -> None:
        result = _evaluate(response_goal="REQUEST_MISSING_INFORMATION")
        assert result.auto_send_allowed is True
