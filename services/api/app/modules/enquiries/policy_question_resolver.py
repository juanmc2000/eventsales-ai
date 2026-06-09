"""Policy Question Resolver (RESP-045).

Resolves extracted policy questions against restaurant and room policy data.

Resolution logic (first match wins):
  1. Room-specific answer (room_policy_faqs) — if room_id provided
  2. Restaurant-level answer (restaurant_policy_faqs)
  3. No answer found → mark as needs_human_review

Output:
  PolicyQuestionResolverResult containing:
  - answered_policy_questions:       Questions with a policy answer
  - review_required_policy_questions: Questions that need human review

No LLM calls are made.  No database mutations are performed.

Usage::

    from app.modules.enquiries.policy_question_resolver import PolicyQuestionResolver

    result = PolicyQuestionResolver.resolve(
        db=db,
        policy_questions=[
            {"question_key": "candles_allowed", "raw_question": "Can we have candles?",
             "scope_hint": "unknown", "confidence": 0.9}
        ],
        restaurant_id=restaurant_id,
        room_id=room_id,  # optional
    )
    # result.answered_policy_questions      → list of AnsweredPolicyQuestion
    # result.review_required_policy_questions → list of extracted question dicts
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.restaurants.models import (
    ANSWER_POLICY_APPROVAL_REQUIRED,
    ANSWER_POLICY_UNKNOWN,
    RestaurantPolicyFAQ,
    RoomPolicyFAQ,
)

# Review trigger policies — questions with these policies go to human review
_REVIEW_POLICIES = {ANSWER_POLICY_APPROVAL_REQUIRED, ANSWER_POLICY_UNKNOWN}


# ── Output dataclasses ─────────────────────────────────────────────────────────


@dataclass
class AnsweredPolicyQuestion:
    """A policy question that was resolved to a known venue policy.

    Attributes:
        question_key:    The canonical question key.
        raw_question:    The verbatim question from the guest.
        answer_policy:   One of the ANSWER_POLICY_* constants.
        answer_text:     Human-readable answer text (may be None for approval_required).
        resolved_from:   "room" | "restaurant" — which table provided the answer.
        requires_human_review: True when answer_policy is approval_required.
    """

    question_key: str
    raw_question: str
    answer_policy: str
    answer_text: str | None
    resolved_from: str
    requires_human_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_key": self.question_key,
            "raw_question": self.raw_question,
            "answer_policy": self.answer_policy,
            "answer_text": self.answer_text,
            "resolved_from": self.resolved_from,
            "requires_human_review": self.requires_human_review,
        }


@dataclass
class PolicyQuestionResolverResult:
    """Result of PolicyQuestionResolver.resolve().

    Attributes:
        answered_policy_questions:        Questions resolved to a known policy.
        review_required_policy_questions: Questions requiring human review
                                          (unknown, approval_required, or not found).
        has_review_required:              True when at least one question needs review.
    """

    answered_policy_questions: list[AnsweredPolicyQuestion] = field(default_factory=list)
    review_required_policy_questions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_review_required(self) -> bool:
        return len(self.review_required_policy_questions) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "answered_policy_questions": [q.to_dict() for q in self.answered_policy_questions],
            "review_required_policy_questions": self.review_required_policy_questions,
            "has_review_required": self.has_review_required,
        }


# ── Service ────────────────────────────────────────────────────────────────────


class PolicyQuestionResolver:
    """Resolves extracted policy questions against restaurant/room FAQ data.

    All resolution is deterministic — no LLM calls are made.
    """

    @classmethod
    def resolve(
        cls,
        db: Session,
        policy_questions: list[dict[str, Any]],
        restaurant_id: uuid.UUID,
        room_id: uuid.UUID | None = None,
    ) -> PolicyQuestionResolverResult:
        """Resolve policy questions against stored FAQ data.

        Args:
            db:               SQLAlchemy session.
            policy_questions: List of extracted question dicts (from LLM1 normalized_json).
                              Each dict must have at minimum: question_key, raw_question.
            restaurant_id:    Restaurant to look up answers for.
            room_id:          Optional room for room-specific overrides.

        Returns:
            PolicyQuestionResolverResult with answered and review-required questions.
        """
        answered: list[AnsweredPolicyQuestion] = []
        review_required: list[dict[str, Any]] = []

        for pq in policy_questions:
            question_key = pq.get("question_key", "unknown")
            raw_question = pq.get("raw_question", "")

            # ── Step 1: room-specific answer ───────────────────────────────────
            if room_id and question_key != "unknown":
                room_faq = cls._lookup_room_faq(db, room_id, restaurant_id, question_key)
                if room_faq:
                    if room_faq.answer_policy in _REVIEW_POLICIES or room_faq.requires_human_review:
                        review_required.append(dict(pq))
                    else:
                        answered.append(AnsweredPolicyQuestion(
                            question_key=question_key,
                            raw_question=raw_question,
                            answer_policy=room_faq.answer_policy,
                            answer_text=room_faq.answer_text,
                            resolved_from="room",
                            requires_human_review=room_faq.requires_human_review,
                        ))
                    continue

            # ── Step 2: restaurant-level answer ───────────────────────────────
            if question_key != "unknown":
                restaurant_faq = cls._lookup_restaurant_faq(db, restaurant_id, question_key)
                if restaurant_faq:
                    if restaurant_faq.answer_policy in _REVIEW_POLICIES or restaurant_faq.requires_human_review:
                        review_required.append(dict(pq))
                    else:
                        answered.append(AnsweredPolicyQuestion(
                            question_key=question_key,
                            raw_question=raw_question,
                            answer_policy=restaurant_faq.answer_policy,
                            answer_text=restaurant_faq.answer_text,
                            resolved_from="restaurant",
                            requires_human_review=restaurant_faq.requires_human_review,
                        ))
                    continue

            # ── Step 3: no answer found → human review ─────────────────────────
            review_required.append(dict(pq))

        return PolicyQuestionResolverResult(
            answered_policy_questions=answered,
            review_required_policy_questions=review_required,
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _lookup_room_faq(
        db: Session,
        room_id: uuid.UUID,
        restaurant_id: uuid.UUID,
        question_key: str,
    ) -> RoomPolicyFAQ | None:
        return db.scalars(
            select(RoomPolicyFAQ)
            .where(RoomPolicyFAQ.room_id == room_id)
            .where(RoomPolicyFAQ.restaurant_id == restaurant_id)
            .where(RoomPolicyFAQ.question_key == question_key)
            .where(RoomPolicyFAQ.is_active.is_(True))
        ).first()

    @staticmethod
    def _lookup_restaurant_faq(
        db: Session,
        restaurant_id: uuid.UUID,
        question_key: str,
    ) -> RestaurantPolicyFAQ | None:
        return db.scalars(
            select(RestaurantPolicyFAQ)
            .where(RestaurantPolicyFAQ.restaurant_id == restaurant_id)
            .where(RestaurantPolicyFAQ.question_key == question_key)
            .where(RestaurantPolicyFAQ.is_active.is_(True))
        ).first()
