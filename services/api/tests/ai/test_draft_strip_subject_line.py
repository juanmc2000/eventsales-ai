"""Tests for RESP-032/RESP-055 — subject-line stripping and compliance check.

Validates that:
- _strip_subject_line removes plain and markdown-bold subject lines
- DraftComplianceValidator catches residual subject-line leakage
- Existing response subject field is unaffected
"""

from __future__ import annotations

import pytest

from app.modules.ai.service import _strip_subject_line
from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext


def _ctx(**kwargs) -> ValidationContext:
    defaults = dict(
        availability_contract="NOT_CHECKED",
        response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
    )
    defaults.update(kwargs)
    return ValidationContext(**defaults)


# ── _strip_subject_line ────────────────────────────────────────────────────────


class TestStripSubjectLine:
    def test_strips_plain_subject_line(self) -> None:
        text = "Subject: Birthday dinner enquiry\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "Subject:" not in result
        assert "Dear Alice" in result

    def test_strips_bold_markdown_subject_line(self) -> None:
        text = "**Subject: Birthday dinner enquiry**\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "Subject:" not in result
        assert "Dear Alice" in result

    def test_strips_bold_without_closing_stars(self) -> None:
        text = "**Subject: Birthday dinner enquiry\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "Subject:" not in result
        assert "Dear Alice" in result

    def test_strips_subject_mid_body(self) -> None:
        text = "Dear Alice,\n\nSubject: Birthday\n\nThank you."
        result = _strip_subject_line(text)
        assert "Subject:" not in result
        assert "Thank you" in result

    def test_strips_case_insensitive(self) -> None:
        text = "SUBJECT: Birthday dinner\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "SUBJECT:" not in result

    def test_strips_with_leading_whitespace(self) -> None:
        text = "   Subject: Birthday dinner\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "Subject:" not in result
        assert "Dear Alice" in result

    def test_text_without_subject_unchanged(self) -> None:
        text = "Dear Alice,\n\nThank you for reaching out.\n\nKind regards, Eleanor"
        result = _strip_subject_line(text)
        assert result == text

    def test_empty_string_returns_empty(self) -> None:
        assert _strip_subject_line("") == ""

    def test_collapses_blank_lines_after_removal(self) -> None:
        text = "Subject: Birthday\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "\n\n\n" not in result

    def test_result_does_not_start_with_blank_line(self) -> None:
        text = "Subject: Birthday\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert not result.startswith("\n")

    def test_only_subject_line_returns_empty(self) -> None:
        result = _strip_subject_line("Subject: Birthday dinner enquiry")
        assert result == ""

    def test_preserves_re_in_subject_when_mid_sentence(self) -> None:
        # "subject" appearing mid-sentence should not be removed
        text = "The subject of this enquiry is a birthday.\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "The subject" in result


# ── DraftComplianceValidator: subject-line check ──────────────────────────────


class TestComplianceValidatorSubjectLine:
    def test_passes_when_no_subject_line(self) -> None:
        result = DraftComplianceValidator.validate(
            draft_text="Dear Alice, thank you for your enquiry. Kind regards, Eleanor",
            context=_ctx(),
        )
        # May have other violations but subject check should not fire
        subject_violations = [v for v in result.violations if "subject line" in v.lower()]
        assert subject_violations == []

    def test_fails_plain_subject_line(self) -> None:
        result = DraftComplianceValidator.validate(
            draft_text="Subject: Birthday dinner\n\nDear Alice,",
            context=_ctx(),
        )
        subject_violations = [v for v in result.violations if "subject line" in v.lower()]
        assert len(subject_violations) == 1

    def test_fails_bold_markdown_subject_line(self) -> None:
        result = DraftComplianceValidator.validate(
            draft_text="**Subject: Birthday dinner**\n\nDear Alice,",
            context=_ctx(),
        )
        subject_violations = [v for v in result.violations if "subject line" in v.lower()]
        assert len(subject_violations) == 1

    def test_violation_message_is_descriptive(self) -> None:
        result = DraftComplianceValidator.validate(
            draft_text="Subject: Enquiry\n\nDear Alice,",
            context=_ctx(),
        )
        subject_violations = [v for v in result.violations if "subject line" in v.lower()]
        assert subject_violations
        assert "subject" in subject_violations[0].lower()


# ── RESP-055: extended subject-line stripping (Re: / Email subject:) ──────────


class TestReSubjectLineStripping:
    """RESP-055: 'Re:' and 'Email subject:' lines stripped from ACKNOWLEDGE responses."""

    def test_strips_re_prefix(self) -> None:
        """email_26/53-style: 'Re: Birthday dinner enquiry' stripped (RESP-055)."""
        text = "Re: Birthday dinner enquiry\n\nDear Alice, thank you for your enquiry."
        result = _strip_subject_line(text)
        assert not result.strip().startswith("Re:")
        assert "Dear Alice" in result

    def test_strips_email_subject_prefix(self) -> None:
        """email_63-style: 'Email subject: ...' stripped (RESP-055)."""
        text = "Email subject: Birthday dinner enquiry\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "Email subject:" not in result
        assert "Dear Alice" in result

    def test_strips_bold_re_prefix(self) -> None:
        """email_80-style: '**Re: ...**' stripped (RESP-055)."""
        text = "**Re: Birthday dinner enquiry**\n\nDear Alice,"
        result = _strip_subject_line(text)
        assert "Re:" not in result
        assert "Dear Alice" in result

    def test_re_mid_sentence_not_stripped(self) -> None:
        """'Re:' appearing mid-sentence (not at line start) is preserved (RESP-055)."""
        text = "Dear Alice, regarding your enquiry, re: the date you mentioned."
        result = _strip_subject_line(text)
        # The 're:' here is not at the start of a line — should not be stripped
        # (The function strips lines where the entire line starts with Re:)
        assert "Dear Alice" in result

    def test_validator_catches_re_subject_line(self) -> None:
        """email_100-style: validator catches 'Re: ...' in draft body (RESP-055)."""
        result = DraftComplianceValidator.validate(
            draft_text="Re: Birthday dinner enquiry\n\nDear Alice, thank you.",
            context=_ctx(),
        )
        subject_violations = [v for v in result.violations if "subject line" in v.lower()]
        assert len(subject_violations) == 1

    def test_validator_catches_email_subject_line(self) -> None:
        """Validator catches 'Email subject: ...' in draft body (RESP-055)."""
        result = DraftComplianceValidator.validate(
            draft_text="Email subject: Birthday dinner\n\nDear Alice, thank you.",
            context=_ctx(),
        )
        subject_violations = [v for v in result.violations if "subject line" in v.lower()]
        assert len(subject_violations) == 1
