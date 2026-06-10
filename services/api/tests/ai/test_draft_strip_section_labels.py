"""Tests for RESP-031 — _strip_section_labels post-processing.

Validates that standalone section header lines are removed from LLM output
while normal bold text inside paragraphs is preserved.
"""

from __future__ import annotations

import pytest

from app.modules.ai.service import _strip_section_labels


class TestStripSectionLabelsBasic:
    def test_strips_opening_label(self) -> None:
        text = "**Opening**\n\nDear Alice, thank you for your enquiry."
        result = _strip_section_labels(text)
        assert "**Opening**" not in result
        assert "Dear Alice" in result

    def test_strips_signoff_label(self) -> None:
        text = "Some text.\n\n**Sign-off**\n\nKind regards,\nEleanor"
        result = _strip_section_labels(text)
        assert "**Sign-off**" not in result
        assert "Kind regards" in result

    def test_strips_sign_off_hyphen_variant(self) -> None:
        text = "Hello.\n\n**Sign-off**\n\nEleanor"
        result = _strip_section_labels(text)
        assert "**Sign-off**" not in result

    def test_strips_enquiry_summary_label(self) -> None:
        text = "**Enquiry summary**\n\nParty of 10 for a birthday."
        result = _strip_section_labels(text)
        assert "**Enquiry summary**" not in result
        assert "Party of 10" in result

    def test_strips_availability_confirmation_label(self) -> None:
        text = "**Availability confirmation**\n\nWe are delighted to confirm."
        result = _strip_section_labels(text)
        assert "**Availability confirmation**" not in result

    def test_strips_booking_next_step_label(self) -> None:
        text = "**Booking next step**\n\nPlease reply to confirm."
        result = _strip_section_labels(text)
        assert "**Booking next step**" not in result

    def test_strips_next_steps_label(self) -> None:
        text = "**Next steps**\n\nWe will contact you shortly."
        result = _strip_section_labels(text)
        assert "**Next steps**" not in result

    def test_strips_closing_label(self) -> None:
        text = "**Closing**\n\nKind regards, Eleanor"
        result = _strip_section_labels(text)
        assert "**Closing**" not in result

    def test_strips_case_insensitive(self) -> None:
        text = "**opening**\n\nDear Alice,"
        result = _strip_section_labels(text)
        assert "**opening**" not in result

    def test_strips_label_with_surrounding_whitespace(self) -> None:
        text = "   **Opening**   \n\nDear Alice,"
        result = _strip_section_labels(text)
        assert "**Opening**" not in result
        assert "Dear Alice" in result


class TestStripSectionLabelsPreservation:
    def test_preserves_bold_venue_name_in_sentence(self) -> None:
        text = "We at **The Grand** would love to host your event."
        result = _strip_section_labels(text)
        assert "**The Grand**" in result

    def test_preserves_bold_word_mid_sentence(self) -> None:
        text = "We confirm **availability** for your requested date."
        result = _strip_section_labels(text)
        assert "**availability**" in result

    def test_preserves_bold_partial_line(self) -> None:
        text = "We are **delighted** to have you."
        result = _strip_section_labels(text)
        assert "**delighted**" in result

    def test_text_without_labels_unchanged(self) -> None:
        text = "Dear Alice,\n\nThank you for reaching out.\n\nKind regards,\nEleanor"
        result = _strip_section_labels(text)
        assert result == text

    def test_empty_string_returns_empty(self) -> None:
        assert _strip_section_labels("") == ""

    def test_only_label_returns_empty(self) -> None:
        result = _strip_section_labels("**Opening**")
        assert result == ""


class TestStripSectionLabelsBlankLines:
    def test_collapses_double_blank_after_removal(self) -> None:
        text = "Dear Alice,\n\n**Opening**\n\nThank you for your enquiry."
        result = _strip_section_labels(text)
        assert "\n\n\n" not in result

    def test_multiple_labels_all_stripped(self) -> None:
        text = (
            "**Opening**\n\n"
            "Dear Alice, thank you.\n\n"
            "**Enquiry summary**\n\n"
            "Party of 8.\n\n"
            "**Sign-off**\n\n"
            "Kind regards, Eleanor"
        )
        result = _strip_section_labels(text)
        assert "**Opening**" not in result
        assert "**Enquiry summary**" not in result
        assert "**Sign-off**" not in result
        assert "Dear Alice" in result
        assert "Party of 8" in result
        assert "Kind regards" in result

    def test_result_does_not_start_with_blank_line(self) -> None:
        text = "\n\n**Opening**\n\nDear Alice,"
        result = _strip_section_labels(text)
        assert not result.startswith("\n")

    def test_result_does_not_end_with_blank_line(self) -> None:
        text = "Dear Alice,\n\n**Sign-off**\n\n"
        result = _strip_section_labels(text)
        assert not result.endswith("\n")
