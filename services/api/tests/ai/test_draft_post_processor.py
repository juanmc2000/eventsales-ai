"""Tests for DraftPostProcessor (RESP-061)."""

from __future__ import annotations

import pytest

from app.modules.ai.draft_post_processor import DraftPostProcessor, PostProcessingResult


class TestPostProcessingResult:
    def test_any_stripped_false_when_nothing_removed(self) -> None:
        result = PostProcessingResult(cleaned_body="Hello world")
        assert result.any_stripped is False

    def test_any_stripped_true_when_subject_stripped(self) -> None:
        result = PostProcessingResult(
            cleaned_body="Hello world",
            stripped_subject_lines=["Subject: Test"],
        )
        assert result.any_stripped is True

    def test_any_stripped_true_when_label_stripped(self) -> None:
        result = PostProcessingResult(
            cleaned_body="Hello world",
            stripped_section_labels=["**Opening**"],
        )
        assert result.any_stripped is True

    def test_to_dict_keys(self) -> None:
        result = PostProcessingResult(cleaned_body="Hello")
        d = result.to_dict()
        assert set(d.keys()) == {"cleaned_body", "stripped_subject_lines", "stripped_section_labels", "any_stripped"}


class TestStripSubjectLines:
    """RESP-061: Subject-line leakage is stripped before persistence."""

    def test_plain_subject_stripped(self) -> None:
        raw = "Subject: Re: Engagement Party Enquiry\n\nDear Alice, thank you for your enquiry."
        result = DraftPostProcessor.process(raw)
        assert "Subject:" not in result.cleaned_body
        assert len(result.stripped_subject_lines) == 1
        assert "Subject: Re: Engagement Party Enquiry" in result.stripped_subject_lines[0]

    def test_re_prefix_stripped(self) -> None:
        raw = "Re: Birthday Dinner Enquiry\n\nDear Bob, we have availability."
        result = DraftPostProcessor.process(raw)
        assert result.cleaned_body.startswith("Dear Bob")
        assert len(result.stripped_subject_lines) == 1

    def test_email_subject_prefix_stripped(self) -> None:
        raw = "Email subject: Group Booking Enquiry\n\nDear Chris, thank you."
        result = DraftPostProcessor.process(raw)
        assert "Email subject" not in result.cleaned_body
        assert len(result.stripped_subject_lines) == 1

    def test_bold_subject_stripped(self) -> None:
        raw = "**Subject: Corporate Dinner**\n\nDear David, I'm pleased to confirm."
        result = DraftPostProcessor.process(raw)
        assert "Subject:" not in result.cleaned_body
        assert len(result.stripped_subject_lines) == 1

    def test_subject_mid_body_stripped(self) -> None:
        """Subject line anywhere in body must be removed (email_71 pattern)."""
        raw = (
            "Dear Eve, thank you for your enquiry.\n"
            "\n"
            "Subject: Re: Engagement Party Enquiry\n"
            "\n"
            "We have availability for dinner on 12th June."
        )
        result = DraftPostProcessor.process(raw)
        assert "Subject:" not in result.cleaned_body
        assert "Dear Eve" in result.cleaned_body
        assert "We have availability" in result.cleaned_body

    def test_clean_body_unchanged(self) -> None:
        raw = "Dear Alice, I'm pleased to confirm availability for dinner. Warm regards, Sophie."
        result = DraftPostProcessor.process(raw)
        assert result.cleaned_body == raw
        assert result.stripped_subject_lines == []

    def test_no_legitimate_content_removed(self) -> None:
        """Lines that mention 'subject' in the body (not as prefix) must not be removed."""
        raw = (
            "Dear Alice, thank you for your enquiry about your event.\n"
            "The subject of your booking is dinner for 20 guests.\n"
            "Warm regards, Sophie."
        )
        result = DraftPostProcessor.process(raw)
        assert "The subject of your booking" in result.cleaned_body
        assert result.stripped_subject_lines == []

    def test_case_insensitive_stripping(self) -> None:
        raw = "SUBJECT: Test enquiry\n\nDear Frank, we have availability."
        result = DraftPostProcessor.process(raw)
        assert "SUBJECT:" not in result.cleaned_body
        assert len(result.stripped_subject_lines) == 1


class TestStripSectionLabels:
    """RESP-031: Standalone section labels are stripped."""

    def test_opening_label_stripped(self) -> None:
        raw = "**Opening**\n\nDear Alice, thank you for your enquiry."
        result = DraftPostProcessor.process(raw)
        assert "**Opening**" not in result.cleaned_body
        assert len(result.stripped_section_labels) == 1

    def test_sign_off_label_stripped(self) -> None:
        raw = "Dear Alice, we have availability.\n\n**Sign-off**\n\nWarm regards, Sophie."
        result = DraftPostProcessor.process(raw)
        assert "**Sign-off**" not in result.cleaned_body

    def test_bold_in_paragraph_not_stripped(self) -> None:
        """Bold text inside a sentence must not be removed."""
        raw = "Dear Alice, **The Grand Pavilion** is available for your event."
        result = DraftPostProcessor.process(raw)
        assert "**The Grand Pavilion**" in result.cleaned_body
        assert result.stripped_section_labels == []

    def test_multiple_labels_stripped(self) -> None:
        raw = (
            "**Opening**\n"
            "Dear Alice, thank you.\n"
            "**Availability confirmation**\n"
            "We are available on 12th June.\n"
            "**Sign-off**\n"
            "Warm regards, Sophie."
        )
        result = DraftPostProcessor.process(raw)
        assert "**Opening**" not in result.cleaned_body
        assert "**Availability confirmation**" not in result.cleaned_body
        assert "**Sign-off**" not in result.cleaned_body
        assert "Dear Alice" in result.cleaned_body
        assert len(result.stripped_section_labels) == 3


class TestBlankLineCollapse:
    def test_multiple_blank_lines_collapsed(self) -> None:
        raw = "Para one.\n\n\n\nPara two."
        result = DraftPostProcessor.process(raw)
        # At most one blank line between paragraphs
        assert "\n\n\n" not in result.cleaned_body

    def test_single_blank_line_preserved(self) -> None:
        raw = "Para one.\n\nPara two."
        result = DraftPostProcessor.process(raw)
        assert "\n\nPara two." in result.cleaned_body


class TestCombinedProcessing:
    def test_subject_and_label_both_stripped(self) -> None:
        raw = (
            "**Opening**\n"
            "Subject: Group Dinner Enquiry\n"
            "\n"
            "Dear Alice, we have availability for dinner on Friday, 12 June 2026.\n"
            "\n"
            "**Sign-off**\n"
            "Warm regards, Sophie."
        )
        result = DraftPostProcessor.process(raw)
        assert "Subject:" not in result.cleaned_body
        assert "**Opening**" not in result.cleaned_body
        assert "**Sign-off**" not in result.cleaned_body
        assert "Dear Alice" in result.cleaned_body
        assert "Warm regards, Sophie." in result.cleaned_body
        assert len(result.stripped_subject_lines) == 1
        assert len(result.stripped_section_labels) == 2

    def test_idempotent(self) -> None:
        """Running process() twice returns the same result as running it once."""
        raw = "Subject: Test\n\n**Opening**\nDear Alice, availability confirmed."
        first = DraftPostProcessor.process(raw)
        second = DraftPostProcessor.process(first.cleaned_body)
        assert first.cleaned_body == second.cleaned_body
