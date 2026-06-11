"""Tests for CustomerNameConsistencyValidator (RESP-062)."""

from __future__ import annotations

import pytest

from app.modules.ai.customer_name_validator import (
    CustomerNameConsistencyValidator,
    NameConsistencyResult,
)


class TestExtractGreetingName:
    def test_dear_first_name(self) -> None:
        draft = "Dear Alice, thank you for your enquiry."
        assert CustomerNameConsistencyValidator.extract_greeting_name(draft) == "Alice"

    def test_hi_first_name(self) -> None:
        draft = "Hi Bob, thank you for reaching out."
        assert CustomerNameConsistencyValidator.extract_greeting_name(draft) == "Bob"

    def test_hello_first_name(self) -> None:
        draft = "Hello Chris, I'm pleased to confirm availability."
        assert CustomerNameConsistencyValidator.extract_greeting_name(draft) == "Chris"

    def test_dear_name_mid_text(self) -> None:
        """Greeting can appear after some preamble."""
        draft = "Thank you for your enquiry.\n\nDear David, we have availability."
        assert CustomerNameConsistencyValidator.extract_greeting_name(draft) == "David"

    def test_no_greeting_returns_none(self) -> None:
        draft = "Thank you for your enquiry. We will get back to you."
        assert CustomerNameConsistencyValidator.extract_greeting_name(draft) is None

    def test_dear_extracts_first_word_only(self) -> None:
        draft = "Dear James Smith, thank you for your enquiry."
        assert CustomerNameConsistencyValidator.extract_greeting_name(draft) == "James"

    def test_dear_mr_extracts_title_word(self) -> None:
        """Title+surname greeting: validator takes the first word."""
        draft = "Dear Mr Brown, thank you for your enquiry."
        assert CustomerNameConsistencyValidator.extract_greeting_name(draft) == "Mr"


class TestValidate:
    def test_matching_name_passes(self) -> None:
        draft = "Dear Alice, we have availability for dinner on 12th June."
        result = CustomerNameConsistencyValidator.validate(draft, "Alice")
        assert result.passed is True
        assert result.violation is None

    def test_case_insensitive_match_passes(self) -> None:
        draft = "Dear alice, we have availability."
        result = CustomerNameConsistencyValidator.validate(draft, "Alice")
        assert result.passed is True

    def test_wrong_name_fails(self) -> None:
        """email_69/70-style: draft greets wrong customer name."""
        draft = "Dear Bob, thank you for your enquiry."
        result = CustomerNameConsistencyValidator.validate(draft, "Alice")
        assert result.passed is False
        assert result.violation is not None
        assert "Bob" in result.violation
        assert "Alice" in result.violation

    def test_unknown_customer_name_skips_check(self) -> None:
        """When expected name is None, check is skipped — no false positives."""
        draft = "Dear Bob, thank you for your enquiry."
        result = CustomerNameConsistencyValidator.validate(draft, None)
        assert result.passed is True
        assert result.violation is None

    def test_empty_expected_name_skips_check(self) -> None:
        draft = "Dear Bob, thank you for your enquiry."
        result = CustomerNameConsistencyValidator.validate(draft, "")
        assert result.passed is True

    def test_no_greeting_found_passes(self) -> None:
        """No greeting found — validator skips to avoid false positives."""
        draft = "Thank you for your enquiry. We will check availability."
        result = CustomerNameConsistencyValidator.validate(draft, "Alice")
        assert result.passed is True
        assert result.greeting_name is None

    def test_prefix_match_passes_alex_alexander(self) -> None:
        """Alex/Alexander: 'Alex' is a genuine prefix of 'Alexander'."""
        draft = "Dear Alex, we have availability for dinner on 12th June."
        result = CustomerNameConsistencyValidator.validate(draft, "Alexander")
        assert result.passed is True

    def test_prefix_match_passes_alexander_alex(self) -> None:
        """Alexander/Alex: 'Alexander' starts with 'Alex'."""
        draft = "Dear Alexander, we have availability."
        result = CustomerNameConsistencyValidator.validate(draft, "Alex")
        assert result.passed is True

    def test_completely_different_names_fail(self) -> None:
        draft = "Dear Sarah, we have availability."
        result = CustomerNameConsistencyValidator.validate(draft, "Michael")
        assert result.passed is False

    def test_result_fields_populated_on_failure(self) -> None:
        draft = "Dear Wrong, thank you for your enquiry."
        result = CustomerNameConsistencyValidator.validate(draft, "Right")
        assert result.passed is False
        assert result.greeting_name == "Wrong"
        assert result.expected_name == "Right"
        assert "Wrong" in result.violation
        assert "Right" in result.violation

    def test_result_fields_populated_on_success(self) -> None:
        draft = "Dear Alice, thank you for your enquiry."
        result = CustomerNameConsistencyValidator.validate(draft, "Alice")
        assert result.passed is True
        assert result.greeting_name == "Alice"
        assert result.expected_name == "Alice"
        assert result.violation is None

    def test_email_69_style_wrong_name(self) -> None:
        """email_69: draft uses a name not in the enquiry."""
        draft = (
            "Dear Emma, thank you for your enquiry about dinner on 12th June. "
            "I'm pleased to confirm we have availability. Warm regards, Sophie."
        )
        result = CustomerNameConsistencyValidator.validate(draft, "James")
        assert result.passed is False
        assert "Emma" in result.violation

    def test_email_70_style_wrong_name(self) -> None:
        """email_70: similar wrong-name pattern."""
        draft = (
            "Dear David, thank you for your group booking enquiry. "
            "We have availability for dinner on 19th June. Warm regards, Sophie."
        )
        result = CustomerNameConsistencyValidator.validate(draft, "Laura")
        assert result.passed is False
        assert "David" in result.violation


class TestDraftComplianceValidatorIntegration:
    """RESP-062 integration: wired into DraftComplianceValidator."""

    def test_wrong_name_fails_validation(self) -> None:
        from app.modules.ai.draft_compliance_validator import (
            DraftComplianceValidator,
            ValidationContext,
        )

        draft = "Dear Bob, thank you for your enquiry. We have availability. Warm regards, Sophie."
        ctx = ValidationContext(
            availability_contract="CONFIRMED_AVAILABLE",
            response_goal="CONFIRM_AVAILABLE",
            expected_customer_name="Alice",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False
        assert any("Bob" in v and "Alice" in v for v in result.violations)

    def test_correct_name_passes_validation(self) -> None:
        from app.modules.ai.draft_compliance_validator import (
            DraftComplianceValidator,
            ValidationContext,
        )

        draft = (
            "Dear Alice, I'm delighted to confirm that we have availability for dinner on 12th June. "
            "Please reply to confirm. Warm regards, Sophie."
        )
        ctx = ValidationContext(
            availability_contract="CONFIRMED_AVAILABLE",
            response_goal="CONFIRM_AVAILABLE",
            expected_customer_name="Alice",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        name_violations = [v for v in result.violations if "customer name" in v.lower()]
        assert len(name_violations) == 0

    def test_no_expected_name_check_skipped(self) -> None:
        from app.modules.ai.draft_compliance_validator import (
            DraftComplianceValidator,
            ValidationContext,
        )

        draft = "Dear Bob, thank you for your enquiry. We have availability."
        ctx = ValidationContext(
            availability_contract="NOT_CHECKED",
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            expected_customer_name=None,
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        name_violations = [v for v in result.violations if "customer name" in v.lower()]
        assert len(name_violations) == 0
