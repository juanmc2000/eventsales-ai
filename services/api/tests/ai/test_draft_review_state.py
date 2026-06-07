"""Tests for AUTO-002 — Draft Review Status Lifecycle.

Validates:
- DraftReviewState dataclass structure and defaults
- DraftReviewStateService.evaluate() transitions for all 6 statuses
- approved() and sent() transition helpers
- VALIDATION_FAILED when compliance fails
- HUMAN_REVIEW_REQUIRED when gate not run or blocked
- AUTO_SEND_ELIGIBLE when all gates pass
- review_state wired into DraftGenerationResult schema
"""

from __future__ import annotations

import pytest

from app.modules.ai.draft_review_state import (
    APPROVED_TO_SEND,
    AUTO_SEND_ELIGIBLE,
    DRAFT_CREATED,
    HUMAN_REVIEW_REQUIRED,
    SENT,
    VALIDATION_FAILED,
    ALL_STATUSES,
    DraftReviewState,
    DraftReviewStateService,
)


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _make_compliance(passed: bool, violations: list[str] | None = None):
    from app.modules.ai.draft_compliance_validator import ComplianceResult
    return ComplianceResult(
        passed=passed,
        violations=violations or [],
        unsafe_to_send=not passed,
    )


def _make_readiness(auto_send_allowed: bool, blockers: list[str] | None = None):
    from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessResult
    return AutoSendReadinessResult(
        auto_send_allowed=auto_send_allowed,
        auto_send_blockers=blockers or [],
    )


# ── Status constants ─────────────────────────────────────────────────────────────


class TestStatusConstants:
    def test_all_six_statuses_defined(self) -> None:
        assert DRAFT_CREATED == "DRAFT_CREATED"
        assert VALIDATION_FAILED == "VALIDATION_FAILED"
        assert HUMAN_REVIEW_REQUIRED == "HUMAN_REVIEW_REQUIRED"
        assert AUTO_SEND_ELIGIBLE == "AUTO_SEND_ELIGIBLE"
        assert APPROVED_TO_SEND == "APPROVED_TO_SEND"
        assert SENT == "SENT"

    def test_all_statuses_tuple_contains_all(self) -> None:
        for s in (
            DRAFT_CREATED, VALIDATION_FAILED, HUMAN_REVIEW_REQUIRED,
            AUTO_SEND_ELIGIBLE, APPROVED_TO_SEND, SENT,
        ):
            assert s in ALL_STATUSES


# ── DraftReviewState defaults ────────────────────────────────────────────────────


class TestDraftReviewStateDefaults:
    def test_default_auto_send_allowed_false(self) -> None:
        state = DraftReviewState(status=DRAFT_CREATED)
        assert state.auto_send_allowed is False

    def test_default_blockers_empty(self) -> None:
        state = DraftReviewState(status=DRAFT_CREATED)
        assert state.blockers == []

    def test_default_validation_passed_true(self) -> None:
        state = DraftReviewState(status=DRAFT_CREATED)
        assert state.validation_passed is True

    def test_to_dict_contains_expected_keys(self) -> None:
        state = DraftReviewState(status=AUTO_SEND_ELIGIBLE, auto_send_allowed=True)
        d = state.to_dict()
        assert set(d.keys()) == {
            "status", "auto_send_allowed", "blockers",
            "validation_passed", "validation_violations",
            "auto_send_blockers", "reviewer_notes",
        }

    def test_to_dict_values_match_fields(self) -> None:
        state = DraftReviewState(
            status=VALIDATION_FAILED,
            auto_send_allowed=False,
            blockers=["bad content"],
            validation_passed=False,
            validation_violations=["bad content"],
        )
        d = state.to_dict()
        assert d["status"] == VALIDATION_FAILED
        assert d["auto_send_allowed"] is False
        assert d["blockers"] == ["bad content"]
        assert d["validation_passed"] is False


# ── evaluate() — compliance failure ──────────────────────────────────────────────


class TestEvaluateComplianceFailure:
    def test_failed_compliance_gives_validation_failed(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(False, ["availability overclaim"]),
        )
        assert state.status == VALIDATION_FAILED

    def test_failed_compliance_auto_send_false(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(False, ["fake url"]),
        )
        assert state.auto_send_allowed is False

    def test_failed_compliance_violations_in_blockers(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(False, ["spend too soft"]),
        )
        assert "spend too soft" in state.blockers

    def test_failed_compliance_validation_passed_false(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(False),
        )
        assert state.validation_passed is False


# ── evaluate() — readiness gate not run ──────────────────────────────────────────


class TestEvaluateReadinessGateNotRun:
    def test_none_readiness_gives_human_review(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=None,
        )
        assert state.status == HUMAN_REVIEW_REQUIRED

    def test_none_readiness_auto_send_false(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=None,
        )
        assert state.auto_send_allowed is False

    def test_none_readiness_blocker_message_present(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=None,
        )
        assert len(state.blockers) > 0


# ── evaluate() — readiness blocked ───────────────────────────────────────────────


class TestEvaluateReadinessBlocked:
    def test_blocked_readiness_gives_human_review(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(False, ["goal is RESPOND_UNAVAILABLE"]),
        )
        assert state.status == HUMAN_REVIEW_REQUIRED

    def test_blocked_readiness_auto_send_false(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(False, ["date status ambiguous"]),
        )
        assert state.auto_send_allowed is False

    def test_blocked_readiness_blockers_populated(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(False, ["date status ambiguous"]),
        )
        assert "date status ambiguous" in state.auto_send_blockers


# ── evaluate() — auto-send eligible ──────────────────────────────────────────────


class TestEvaluateAutoSendEligible:
    def test_clean_draft_gives_auto_send_eligible(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
        )
        assert state.status == AUTO_SEND_ELIGIBLE

    def test_eligible_auto_send_allowed_true(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
        )
        assert state.auto_send_allowed is True

    def test_eligible_blockers_empty(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
        )
        assert state.blockers == []
        assert state.auto_send_blockers == []

    def test_eligible_validation_passed_true(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
        )
        assert state.validation_passed is True


# ── reviewer_notes propagation ────────────────────────────────────────────────────


class TestReviewerNotes:
    def test_reviewer_notes_stored_on_validation_failed(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(False),
            reviewer_notes="Checked by Alice",
        )
        assert state.reviewer_notes == "Checked by Alice"

    def test_reviewer_notes_stored_on_human_review(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(False),
            reviewer_notes="Needs ops check",
        )
        assert state.reviewer_notes == "Needs ops check"


# ── approved() transition ─────────────────────────────────────────────────────────


class TestApprovedTransition:
    def test_approved_sets_status(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(False, ["date ambiguous"]),
        )
        approved = DraftReviewStateService.approved(state, reviewer_notes="Approved by Bob")
        assert approved.status == APPROVED_TO_SEND

    def test_approved_preserves_other_fields(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(False, ["date ambiguous"]),
        )
        approved = DraftReviewStateService.approved(state)
        assert approved.auto_send_allowed == state.auto_send_allowed
        assert approved.blockers == state.blockers

    def test_approved_updates_reviewer_notes(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
        )
        approved = DraftReviewStateService.approved(state, reviewer_notes="Reviewed")
        assert approved.reviewer_notes == "Reviewed"

    def test_approved_keeps_existing_notes_when_empty(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
            reviewer_notes="Original note",
        )
        approved = DraftReviewStateService.approved(state, reviewer_notes="")
        assert approved.reviewer_notes == "Original note"


# ── sent() transition ─────────────────────────────────────────────────────────────


class TestSentTransition:
    def test_sent_sets_status(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
        )
        sent = DraftReviewStateService.sent(state)
        assert sent.status == SENT

    def test_sent_preserves_auto_send_field(self) -> None:
        state = DraftReviewStateService.evaluate(
            compliance_result=_make_compliance(True),
            readiness_result=_make_readiness(True),
        )
        sent = DraftReviewStateService.sent(state)
        assert sent.auto_send_allowed is True


# ── DraftGenerationResult schema integration ──────────────────────────────────────


class TestDraftGenerationResultSchema:
    def test_review_state_field_exists(self) -> None:
        from app.modules.ai.schemas import DraftGenerationResult
        import uuid
        result = DraftGenerationResult(
            enquiry_id=uuid.uuid4(),
            message_id=uuid.uuid4(),
            subject="Test",
            body="Test body",
            persona_name="Events Team",
            is_fallback=False,
            model="claude-sonnet-4-6",
        )
        assert result.review_state is None

    def test_review_state_accepts_draft_review_state(self) -> None:
        from app.modules.ai.schemas import DraftGenerationResult
        import uuid
        state = DraftReviewState(status=AUTO_SEND_ELIGIBLE, auto_send_allowed=True)
        result = DraftGenerationResult(
            enquiry_id=uuid.uuid4(),
            message_id=uuid.uuid4(),
            subject="Test",
            body="Test body",
            persona_name="Events Team",
            is_fallback=False,
            model="claude-sonnet-4-6",
            review_state=state,
        )
        assert result.review_state is not None
        assert result.review_state.status == AUTO_SEND_ELIGIBLE
        assert result.review_state.auto_send_allowed is True
