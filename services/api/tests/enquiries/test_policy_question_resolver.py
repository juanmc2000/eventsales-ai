"""Tests for PolicyQuestionResolver (RESP-045)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.enquiries.policy_question_resolver import (
    AnsweredPolicyQuestion,
    PolicyQuestionResolver,
    PolicyQuestionResolverResult,
)
from app.modules.restaurants.models import (
    ANSWER_POLICY_ALLOWED,
    ANSWER_POLICY_APPROVAL_REQUIRED,
    ANSWER_POLICY_INFORMATION_ONLY,
    ANSWER_POLICY_NOT_ALLOWED,
    ANSWER_POLICY_UNKNOWN,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _faq(
    question_key: str,
    answer_policy: str,
    answer_text: str | None = "some answer",
    requires_review: bool = False,
) -> MagicMock:
    faq = MagicMock()
    faq.question_key = question_key
    faq.answer_policy = answer_policy
    faq.answer_text = answer_text
    faq.requires_human_review = requires_review
    faq.is_active = True
    return faq


RESTAURANT_ID = uuid.uuid4()
ROOM_ID = uuid.uuid4()


def _pq(question_key: str, raw_question: str = "test question") -> dict:
    return {
        "question_key": question_key,
        "raw_question": raw_question,
        "scope_hint": "unknown",
        "confidence": 0.9,
    }


# ── Output dataclasses ─────────────────────────────────────────────────────────


def test_result_has_review_required_false_when_empty():
    result = PolicyQuestionResolverResult()
    assert result.has_review_required is False


def test_result_has_review_required_true_when_populated():
    result = PolicyQuestionResolverResult(
        review_required_policy_questions=[{"question_key": "unknown_question"}],
    )
    assert result.has_review_required is True


def test_answered_question_to_dict():
    aq = AnsweredPolicyQuestion(
        question_key="candles_allowed",
        raw_question="Can we have candles?",
        answer_policy=ANSWER_POLICY_ALLOWED,
        answer_text="Yes, candles are permitted.",
        resolved_from="restaurant",
    )
    d = aq.to_dict()
    assert d["question_key"] == "candles_allowed"
    assert d["resolved_from"] == "restaurant"


# ── Resolver: empty input ──────────────────────────────────────────────────────


def test_empty_policy_questions_returns_empty_result():
    db = MagicMock()
    result = PolicyQuestionResolver.resolve(
        db=db,
        policy_questions=[],
        restaurant_id=RESTAURANT_ID,
    )
    assert result.answered_policy_questions == []
    assert result.review_required_policy_questions == []
    assert result.has_review_required is False


# ── Resolver: restaurant answer ────────────────────────────────────────────────


def test_resolves_from_restaurant_allowed():
    db = MagicMock()
    faq = _faq("candles_allowed", ANSWER_POLICY_ALLOWED, "Birthday candles are permitted.")

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=None), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", return_value=faq):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[_pq("candles_allowed", "Can we light a candle?")],
            restaurant_id=RESTAURANT_ID,
        )

    assert len(result.answered_policy_questions) == 1
    assert result.answered_policy_questions[0].answer_policy == ANSWER_POLICY_ALLOWED
    assert result.answered_policy_questions[0].resolved_from == "restaurant"
    assert result.has_review_required is False


def test_resolves_from_restaurant_not_allowed():
    db = MagicMock()
    faq = _faq("pets_allowed", ANSWER_POLICY_NOT_ALLOWED, "Pets are not permitted.")

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=None), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", return_value=faq):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[_pq("pets_allowed", "Can I bring my dog?")],
            restaurant_id=RESTAURANT_ID,
        )

    assert len(result.answered_policy_questions) == 1
    assert result.answered_policy_questions[0].answer_policy == ANSWER_POLICY_NOT_ALLOWED


def test_resolves_information_only():
    db = MagicMock()
    faq = _faq("microphone_available", ANSWER_POLICY_INFORMATION_ONLY, "Microphone available on request.")

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=None), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", return_value=faq):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[_pq("microphone_available", "Is there a microphone?")],
            restaurant_id=RESTAURANT_ID,
        )

    assert len(result.answered_policy_questions) == 1
    assert result.answered_policy_questions[0].answer_policy == ANSWER_POLICY_INFORMATION_ONLY


# ── Resolver: room answer overrides restaurant ────────────────────────────────


def test_room_answer_overrides_restaurant():
    db = MagicMock()
    room_faq = _faq("decorations_allowed", ANSWER_POLICY_ALLOWED, "Decorations allowed in this room.")
    restaurant_faq = _faq("decorations_allowed", ANSWER_POLICY_APPROVAL_REQUIRED, None, requires_review=True)

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=room_faq), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", return_value=restaurant_faq):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[_pq("decorations_allowed", "Can we decorate the room?")],
            restaurant_id=RESTAURANT_ID,
            room_id=ROOM_ID,
        )

    assert len(result.answered_policy_questions) == 1
    assert result.answered_policy_questions[0].resolved_from == "room"
    assert result.answered_policy_questions[0].answer_policy == ANSWER_POLICY_ALLOWED
    assert result.has_review_required is False


# ── Resolver: approval_required → review ──────────────────────────────────────


def test_approval_required_goes_to_review():
    db = MagicMock()
    faq = _faq("external_performer_allowed", ANSWER_POLICY_APPROVAL_REQUIRED, None, requires_review=True)

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=None), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", return_value=faq):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[_pq("external_performer_allowed", "Can we hire a singer?")],
            restaurant_id=RESTAURANT_ID,
        )

    assert len(result.answered_policy_questions) == 0
    assert len(result.review_required_policy_questions) == 1
    assert result.has_review_required is True


# ── Resolver: unknown question → review ───────────────────────────────────────


def test_unknown_question_key_goes_to_review():
    db = MagicMock()

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=None), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", return_value=None):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[_pq("unknown", "Can we do something unusual?")],
            restaurant_id=RESTAURANT_ID,
        )

    assert len(result.review_required_policy_questions) == 1
    assert result.has_review_required is True


def test_no_faq_found_goes_to_review():
    db = MagicMock()

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=None), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", return_value=None):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[_pq("agency_commission", "What is the commission?")],
            restaurant_id=RESTAURANT_ID,
        )

    assert len(result.review_required_policy_questions) == 1


# ── Resolver: multiple questions mixed ────────────────────────────────────────


def test_mixed_questions_correctly_split():
    db = MagicMock()
    candles_faq = _faq("candles_allowed", ANSWER_POLICY_ALLOWED, "Candles are permitted.")
    dj_faq = _faq("dj_allowed", ANSWER_POLICY_APPROVAL_REQUIRED, None, requires_review=True)

    def _mock_restaurant_faq(_db, restaurant_id, question_key):
        if question_key == "candles_allowed":
            return candles_faq
        if question_key == "dj_allowed":
            return dj_faq
        return None

    with patch.object(PolicyQuestionResolver, "_lookup_room_faq", return_value=None), \
         patch.object(PolicyQuestionResolver, "_lookup_restaurant_faq", side_effect=_mock_restaurant_faq):

        result = PolicyQuestionResolver.resolve(
            db=db,
            policy_questions=[
                _pq("candles_allowed", "Can we have birthday candles?"),
                _pq("dj_allowed", "Can we bring a DJ?"),
                _pq("unknown", "Can we do X?"),
            ],
            restaurant_id=RESTAURANT_ID,
        )

    assert len(result.answered_policy_questions) == 1
    assert len(result.review_required_policy_questions) == 2
    assert result.answered_policy_questions[0].question_key == "candles_allowed"
