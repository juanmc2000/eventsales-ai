"""Deterministic Policy Answer Composer (RESP-046).

Composes approved copy blocks for resolved customer policy questions.
No LLM is required — all responses are built from deterministic templates
keyed by answer_policy.

For questions requiring human review, a safe holding phrase is generated.
Unknown questions are never answered directly.

Input:
  - answered_policy_questions:         List from PolicyQuestionResolver.
  - review_required_policy_questions:  List of unresolved question dicts.

Output (PolicyAnswerComposerResult):
  - approved_answers_block:   Formatted string of approved answers (may be empty).
  - review_required_block:    Formatted string for questions escalated to review.
  - has_approved_answers:     True when at least one answer was composed.
  - has_review_required:      True when at least one question needs review.

No LLM calls are made.

Usage::

    from app.modules.enquiries.deterministic_policy_answer_composer import (
        DeterministicPolicyAnswerComposer,
    )

    result = DeterministicPolicyAnswerComposer.compose(
        answered_policy_questions=resolver_result.answered_policy_questions,
        review_required_policy_questions=resolver_result.review_required_policy_questions,
    )
    # result.approved_answers_block → "Yes, birthday candles are permitted..."
    # result.review_required_block  → "I'll check this with the team..."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.enquiries.policy_question_resolver import AnsweredPolicyQuestion

from app.modules.restaurants.models import (
    ANSWER_POLICY_ALLOWED,
    ANSWER_POLICY_APPROVAL_REQUIRED,
    ANSWER_POLICY_INFORMATION_ONLY,
    ANSWER_POLICY_NOT_ALLOWED,
    ANSWER_POLICY_UNKNOWN,
)

# ── Copy template functions ────────────────────────────────────────────────────

# Safe holding phrase for questions requiring human review
_REVIEW_HOLDING_PHRASE = "I'll check this with the team and come back to you."


def _compose_allowed(answer_text: str | None, question_key: str) -> str:
    """Compose an "allowed" answer."""
    if answer_text:
        return answer_text
    # Fallback for allowed without explicit answer_text
    readable = question_key.replace("_", " ").replace("allowed", "").strip()
    return f"Yes, {readable} is permitted."


def _compose_not_allowed(answer_text: str | None, question_key: str) -> str:
    """Compose a "not allowed" answer."""
    if answer_text:
        return answer_text
    readable = question_key.replace("_", " ").replace("allowed", "").strip()
    return f"Unfortunately, we are unable to allow {readable}."


def _compose_information_only(answer_text: str | None, question_key: str) -> str:
    """Compose an information-only answer."""
    if answer_text:
        return answer_text
    return f"For information on {question_key.replace('_', ' ')}, please contact our events team."


def _compose_approval_required(_answer_text: str | None, _question_key: str) -> str:
    """Compose an approval-required holding answer."""
    return _REVIEW_HOLDING_PHRASE


def _compose_unknown(_answer_text: str | None, _question_key: str) -> str:
    """Compose a holding answer for unknown policy."""
    return _REVIEW_HOLDING_PHRASE


_COMPOSERS = {
    ANSWER_POLICY_ALLOWED: _compose_allowed,
    ANSWER_POLICY_NOT_ALLOWED: _compose_not_allowed,
    ANSWER_POLICY_INFORMATION_ONLY: _compose_information_only,
    ANSWER_POLICY_APPROVAL_REQUIRED: _compose_approval_required,
    ANSWER_POLICY_UNKNOWN: _compose_unknown,
}


# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class PolicyAnswerComposerResult:
    """Result of DeterministicPolicyAnswerComposer.compose().

    Attributes:
        approved_answers_block:  Composed text block for policy answers (may be "").
        review_required_block:   Holding phrase block for escalated questions (may be "").
        has_approved_answers:    True when at least one answer was composed.
        has_review_required:     True when at least one question needs review.
        answer_lines:            Individual composed answer strings (for downstream use).
        review_lines:            Individual holding phrase strings (for downstream use).
    """

    approved_answers_block: str = ""
    review_required_block: str = ""
    has_approved_answers: bool = False
    has_review_required: bool = False
    answer_lines: list[str] = field(default_factory=list)
    review_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved_answers_block": self.approved_answers_block,
            "review_required_block": self.review_required_block,
            "has_approved_answers": self.has_approved_answers,
            "has_review_required": self.has_review_required,
            "answer_lines": self.answer_lines,
            "review_lines": self.review_lines,
        }


# ── Composer ───────────────────────────────────────────────────────────────────


class DeterministicPolicyAnswerComposer:
    """Composes deterministic copy blocks for resolved policy questions.

    No LLM calls are made.  All copy is deterministic from answer_policy values.
    """

    @classmethod
    def compose(
        cls,
        answered_policy_questions: list["AnsweredPolicyQuestion"],
        review_required_policy_questions: list[dict[str, Any]],
    ) -> PolicyAnswerComposerResult:
        """Compose answer blocks from resolved policy question data.

        Args:
            answered_policy_questions:        Questions resolved to a known policy.
            review_required_policy_questions: Questions requiring human review.

        Returns:
            PolicyAnswerComposerResult with composed text blocks.
        """
        answer_lines: list[str] = []
        review_lines: list[str] = []

        # Compose approved answers
        for aq in answered_policy_questions:
            if aq.requires_human_review:
                # approval_required answers are escalated even when "answered"
                review_lines.append(_REVIEW_HOLDING_PHRASE)
                continue
            composer_fn = _COMPOSERS.get(aq.answer_policy, _compose_unknown)
            line = composer_fn(aq.answer_text, aq.question_key)
            answer_lines.append(line)

        # Holding phrase for review-required questions
        # Deduplicate: only one holding phrase even with multiple unknown questions
        if review_required_policy_questions:
            review_lines.append(_REVIEW_HOLDING_PHRASE)

        # Remove exact duplicates while preserving order
        seen: set[str] = set()
        unique_review: list[str] = []
        for line in review_lines:
            if line not in seen:
                unique_review.append(line)
                seen.add(line)
        review_lines = unique_review

        approved_block = "\n".join(answer_lines) if answer_lines else ""
        review_block = "\n".join(review_lines) if review_lines else ""

        return PolicyAnswerComposerResult(
            approved_answers_block=approved_block,
            review_required_block=review_block,
            has_approved_answers=bool(answer_lines),
            has_review_required=bool(review_lines),
            answer_lines=answer_lines,
            review_lines=review_lines,
        )
