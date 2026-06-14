"""Tests for AUTO-001 — Auto-Send Eligibility Policy V1.

Validates:
- Allowed goals pass is_goal_eligible()
- Blocked goals fail is_goal_eligible() with a reason
- Allowed date statuses pass is_date_status_eligible()
- Blocked date statuses fail is_date_status_eligible()
- goal_block_reason() returns None for allowed goals, a string for blocked
- date_status_block_reason() returns None for allowed statuses, a string for blocked
- policy_summary() contains all expected keys
- AutoSendReadinessGate uses policy for goal and date-status checks
"""

from __future__ import annotations

import pytest

from app.modules.ai.auto_send_policy import AutoSendEligibilityPolicy


# ── Goal eligibility ────────────────────────────────────────────────────────────


class TestGoalEligibility:
    def test_confirm_available_is_eligible(self) -> None:
        assert AutoSendEligibilityPolicy.is_goal_eligible("CONFIRM_AVAILABLE") is True

    def test_acknowledge_and_check_is_eligible(self) -> None:
        assert AutoSendEligibilityPolicy.is_goal_eligible("ACKNOWLEDGE_AND_CHECK_AVAILABILITY") is True

    def test_respond_unavailable_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_goal_eligible("RESPOND_UNAVAILABLE") is False

    def test_request_date_confirmation_is_eligible(self) -> None:
        # HOTFIX-007: RDTC is now fully deterministic (RESP-073) — safe for auto-send
        assert AutoSendEligibilityPolicy.is_goal_eligible("REQUEST_DATE_CONFIRMATION") is True

    def test_request_webform_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_goal_eligible("REQUEST_WEBFORM") is False

    def test_escalate_to_human_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_goal_eligible("ESCALATE_TO_HUMAN") is False

    def test_request_missing_information_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_goal_eligible("REQUEST_MISSING_INFORMATION") is False

    def test_unknown_goal_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_goal_eligible("SOME_FUTURE_GOAL") is False


# ── Date status eligibility ─────────────────────────────────────────────────────


class TestDateStatusEligibility:
    def test_resolved_is_eligible(self) -> None:
        assert AutoSendEligibilityPolicy.is_date_status_eligible("resolved") is True

    def test_resolved_with_confirmation_is_eligible(self) -> None:
        assert AutoSendEligibilityPolicy.is_date_status_eligible("resolved_with_confirmation") is True

    def test_ambiguous_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_date_status_eligible("ambiguous") is False

    def test_unknown_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_date_status_eligible("unknown") is False

    def test_unresolved_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_date_status_eligible("unresolved") is False

    def test_empty_string_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_date_status_eligible("") is False

    def test_none_as_string_is_blocked(self) -> None:
        assert AutoSendEligibilityPolicy.is_date_status_eligible("None") is False

    def test_pending_date_confirmation_is_eligible(self) -> None:
        # HOTFIX-007: RDTC emails carry this status — allowed because response
        # communicates the ambiguity to the guest via deterministic copy block.
        assert AutoSendEligibilityPolicy.is_date_status_eligible("pending_date_confirmation") is True


# ── Block reasons ───────────────────────────────────────────────────────────────


class TestBlockReasons:
    def test_allowed_goal_returns_none_reason(self) -> None:
        assert AutoSendEligibilityPolicy.goal_block_reason("CONFIRM_AVAILABLE") is None

    def test_blocked_goal_returns_string_reason(self) -> None:
        reason = AutoSendEligibilityPolicy.goal_block_reason("RESPOND_UNAVAILABLE")
        assert reason is not None
        assert isinstance(reason, str)
        assert len(reason) > 10

    def test_respond_unavailable_mentions_human_review(self) -> None:
        reason = AutoSendEligibilityPolicy.goal_block_reason("RESPOND_UNAVAILABLE")
        assert "human review" in reason.lower() or "human" in reason.lower()

    def test_escalate_mentions_human(self) -> None:
        reason = AutoSendEligibilityPolicy.goal_block_reason("ESCALATE_TO_HUMAN")
        assert reason is not None
        assert "human" in reason.lower()

    def test_allowed_date_status_returns_none_reason(self) -> None:
        assert AutoSendEligibilityPolicy.date_status_block_reason("resolved") is None

    def test_blocked_date_status_returns_string_reason(self) -> None:
        reason = AutoSendEligibilityPolicy.date_status_block_reason("ambiguous")
        assert reason is not None
        assert "ambiguous" in reason


# ── Policy summary ──────────────────────────────────────────────────────────────


class TestPolicySummary:
    def test_policy_summary_has_required_keys(self) -> None:
        summary = AutoSendEligibilityPolicy.policy_summary()
        assert "policy_version" in summary
        assert "allowed_goals" in summary
        assert "blocked_goals" in summary
        assert "allowed_date_statuses" in summary
        assert "additional_requirements" in summary

    def test_policy_summary_allowed_goals(self) -> None:
        summary = AutoSendEligibilityPolicy.policy_summary()
        assert "CONFIRM_AVAILABLE" in summary["allowed_goals"]
        assert "ACKNOWLEDGE_AND_CHECK_AVAILABILITY" in summary["allowed_goals"]

    def test_policy_summary_blocked_goals(self) -> None:
        summary = AutoSendEligibilityPolicy.policy_summary()
        assert "RESPOND_UNAVAILABLE" in summary["blocked_goals"]
        assert "ESCALATE_TO_HUMAN" in summary["blocked_goals"]

    def test_policy_summary_allowed_date_statuses(self) -> None:
        summary = AutoSendEligibilityPolicy.policy_summary()
        assert "resolved" in summary["allowed_date_statuses"]
        assert "resolved_with_confirmation" in summary["allowed_date_statuses"]

    def test_policy_version_is_set(self) -> None:
        assert AutoSendEligibilityPolicy.VERSION == "1.0"


# ── AutoSendReadinessGate integration ─────────────────────────────────────────


class TestGateUsesPolicy:
    """Verify AutoSendReadinessGate still honours policy rules after refactor."""

    def _make_compliance(self, passed: bool):
        from app.modules.ai.draft_compliance_validator import ComplianceResult
        return ComplianceResult(passed=passed, violations=[], unsafe_to_send=not passed)

    def _make_integrity(self, passed: bool):
        from app.modules.enquiries.response_context_integrity_gate import IntegrityCheckResult
        return IntegrityCheckResult(passed=passed)

    def test_respond_unavailable_blocks_gate(self) -> None:
        from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
        result = AutoSendReadinessGate.evaluate(
            response_goal="RESPOND_UNAVAILABLE",
            draft_compliance_result=self._make_compliance(True),
            date_status="resolved",
            integrity_result=self._make_integrity(True),
        )
        assert result.auto_send_allowed is False
        assert any("unavailable" in b.lower() or "human" in b.lower()
                   for b in result.auto_send_blockers)

    def test_ambiguous_date_blocks_gate(self) -> None:
        from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
        result = AutoSendReadinessGate.evaluate(
            response_goal="CONFIRM_AVAILABLE",
            draft_compliance_result=self._make_compliance(True),
            date_status="ambiguous",
            integrity_result=self._make_integrity(True),
        )
        assert result.auto_send_allowed is False
        assert any("ambiguous" in b for b in result.auto_send_blockers)

    def test_clean_confirm_available_passes(self) -> None:
        from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
        result = AutoSendReadinessGate.evaluate(
            response_goal="CONFIRM_AVAILABLE",
            draft_compliance_result=self._make_compliance(True),
            date_status="resolved",
            integrity_result=self._make_integrity(True),
        )
        assert result.auto_send_allowed is True

    def test_clean_acknowledge_passes(self) -> None:
        from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
        result = AutoSendReadinessGate.evaluate(
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            draft_compliance_result=self._make_compliance(True),
            date_status="resolved",
            integrity_result=self._make_integrity(True),
        )
        assert result.auto_send_allowed is True
