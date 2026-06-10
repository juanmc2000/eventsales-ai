"""Tests for DeterministicPolicyAnswerComposer (RESP-046)."""

from __future__ import annotations

import pytest

from app.modules.enquiries.deterministic_policy_answer_composer import (
    DeterministicPolicyAnswerComposer,
    PolicyAnswerComposerResult,
    _REVIEW_HOLDING_PHRASE,
)
from app.modules.enquiries.policy_question_resolver import AnsweredPolicyQuestion
from app.modules.restaurants.models import (
    ANSWER_POLICY_ALLOWED,
    ANSWER_POLICY_APPROVAL_REQUIRED,
    ANSWER_POLICY_INFORMATION_ONLY,
    ANSWER_POLICY_NOT_ALLOWED,
    ANSWER_POLICY_UNKNOWN,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _aq(
    question_key: str,
    answer_policy: str,
    answer_text: str | None = None,
    requires_human_review: bool = False,
) -> AnsweredPolicyQuestion:
    return AnsweredPolicyQuestion(
        question_key=question_key,
        raw_question="Test question about " + question_key,
        answer_policy=answer_policy,
        answer_text=answer_text,
        resolved_from="restaurant",
        requires_human_review=requires_human_review,
    )


# ── Empty inputs ───────────────────────────────────────────────────────────────


def test_empty_inputs_returns_empty_result():
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[],
        review_required_policy_questions=[],
    )
    assert result.has_approved_answers is False
    assert result.has_review_required is False
    assert result.approved_answers_block == ""
    assert result.review_required_block == ""


# ── Allowed ────────────────────────────────────────────────────────────────────


def test_allowed_uses_answer_text():
    aq = _aq("candles_allowed", ANSWER_POLICY_ALLOWED, "Birthday candles are permitted.")
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[aq],
        review_required_policy_questions=[],
    )
    assert result.has_approved_answers is True
    assert "Birthday candles are permitted." in result.approved_answers_block


def test_allowed_without_answer_text_uses_fallback():
    aq = _aq("children_allowed", ANSWER_POLICY_ALLOWED, None)
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[aq],
        review_required_policy_questions=[],
    )
    assert result.has_approved_answers is True
    # Fallback should reference the question key
    assert "children" in result.approved_answers_block.lower() or "permitted" in result.approved_answers_block


# ── Not allowed ────────────────────────────────────────────────────────────────


def test_not_allowed_uses_answer_text():
    aq = _aq("pets_allowed", ANSWER_POLICY_NOT_ALLOWED, "Unfortunately, we are unable to accommodate pets.")
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[aq],
        review_required_policy_questions=[],
    )
    assert "unable to accommodate pets" in result.approved_answers_block


def test_not_allowed_without_answer_text_uses_fallback():
    aq = _aq("pets_allowed", ANSWER_POLICY_NOT_ALLOWED, None)
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[aq],
        review_required_policy_questions=[],
    )
    assert "unable" in result.approved_answers_block.lower()


# ── Information only ───────────────────────────────────────────────────────────


def test_information_only_uses_answer_text():
    aq = _aq("microphone_available", ANSWER_POLICY_INFORMATION_ONLY, "A microphone is available on request.")
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[aq],
        review_required_policy_questions=[],
    )
    assert "available on request" in result.approved_answers_block


# ── Approval required ──────────────────────────────────────────────────────────


def test_approval_required_in_answered_list_goes_to_review():
    # When approval_required lands in answered but with requires_human_review=True
    aq = _aq("external_performer_allowed", ANSWER_POLICY_APPROVAL_REQUIRED, None, requires_human_review=True)
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[aq],
        review_required_policy_questions=[],
    )
    assert result.has_approved_answers is False
    assert result.has_review_required is True
    assert _REVIEW_HOLDING_PHRASE in result.review_required_block


# ── Review required questions ──────────────────────────────────────────────────


def test_review_required_produces_holding_phrase():
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[],
        review_required_policy_questions=[
            {"question_key": "unknown", "raw_question": "Can we do something unusual?"}
        ],
    )
    assert result.has_review_required is True
    assert _REVIEW_HOLDING_PHRASE in result.review_required_block


def test_multiple_review_questions_deduplicated_to_one_phrase():
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[],
        review_required_policy_questions=[
            {"question_key": "unknown", "raw_question": "Q1"},
            {"question_key": "dj_allowed", "raw_question": "Q2"},
        ],
    )
    assert result.has_review_required is True
    # Only one unique holding phrase should appear
    assert result.review_required_block.count(_REVIEW_HOLDING_PHRASE) == 1


# ── Mixed ──────────────────────────────────────────────────────────────────────


def test_mixed_answered_and_review():
    candles = _aq("candles_allowed", ANSWER_POLICY_ALLOWED, "Candles are permitted.")
    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=[candles],
        review_required_policy_questions=[
            {"question_key": "unknown", "raw_question": "Can we do X?"}
        ],
    )
    assert result.has_approved_answers is True
    assert result.has_review_required is True
    assert "Candles are permitted." in result.approved_answers_block
    assert _REVIEW_HOLDING_PHRASE in result.review_required_block


# ── to_dict ────────────────────────────────────────────────────────────────────


def test_to_dict_has_all_keys():
    result = DeterministicPolicyAnswerComposer.compose([], [])
    d = result.to_dict()
    assert "approved_answers_block" in d
    assert "review_required_block" in d
    assert "has_approved_answers" in d
    assert "has_review_required" in d
    assert "answer_lines" in d
    assert "review_lines" in d
