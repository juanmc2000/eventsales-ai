"""Unavailable Response Regression Suite (TEST-020).

Evaluates 32 RESPOND_UNAVAILABLE scenarios using the full V6 governance stack:
  - DraftComplianceValidator  (deterministic checks)
  - ResponseContextIntegrityGate  (RESP-021)
  - AutoSendReadinessGate  (RESP-022, 5 rules)

All checks are deterministic — no LLM calls are made.

For RESPOND_UNAVAILABLE scenarios, the production-equivalent deterministic draft
is built via FirstResponseCopyLibrary (RESP-023). The fixture draft_text field
documents the expected response shape but is not used during validation.

Fixture: tests/fixtures/unavailable_response_regression.json (32 scenarios)

Coverage:
  no_alternatives                — no valid alternatives exist; response is clean unavailable
  no_alternatives_weekend        — weekend dinner/lunch/brunch enquiries with no alternatives
  one_alternative_available      — one confirmed future alternative date offered
  two_alternatives_available     — two confirmed future alternative dates offered
  past_alternative_rejected      — available slot is in the past (D-1 or D-2); not offered
  future_alternative_d_plus_1    — D+1 future alternative correctly offered
  requested_date_in_past         — the requested date itself is in the past
  capacity_unsuitable_alternative — party size exceeds all available room capacity

Acceptance criteria:
  - Fixture includes at least 30 unavailable cases
  - Past alternatives are rejected (alternatives_allowed=false for all-past-alt scenarios)
  - Alternatives are offered only when confirmed available (alternatives_allowed=true only for future alts)
  - Response copy remains deterministic (all compliance checks pass)
  - All scenarios are gate-blocked (RESPOND_UNAVAILABLE is never auto-sendable)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import app.db.models  # noqa: F401 — registers all SQLAlchemy models

from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext
from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
from app.modules.enquiries.response_context_integrity_gate import (
    ResponseContextIntegrityGate,
    IntegrityCheckResult,
)

# ── Paths ────────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "unavailable_response_regression.json"


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _load_fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text())


def _load_scenarios() -> list[dict[str, Any]]:
    return _load_fixture()["scenarios"]


def _build_deterministic_unavailable_text(scenario: dict[str, Any]) -> str:
    """Build the production-equivalent deterministic unavailable draft.

    Matches DraftGenerationService._generate_deterministic_unavailable_draft()
    production routing (RESP-023).
    """
    from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary

    ctx = scenario.get("context", {})
    meal_period = ctx.get("meal_period") or "dinner"
    event_date = ctx.get("event_date") or "the requested date"
    guest_name = ctx.get("guest_first_name") or "there"
    persona_name = ctx.get("persona_name") or "Events Team"

    opening = FirstResponseCopyLibrary.render(
        "availability_unavailable",
        {"meal_period": meal_period, "event_date": event_date},
    )
    signoff = FirstResponseCopyLibrary.render("signoff", {"persona_name": persona_name})
    return f"Dear {guest_name},\n\n{opening}\n\n{signoff}"


def _context_from_scenario(scenario: dict[str, Any]) -> ValidationContext:
    ctx = scenario.get("context", {})
    return ValidationContext(
        availability_contract=scenario.get("availability_contract", "NOT_CHECKED"),
        clarification_questions=ctx.get("clarification_questions", []),
        confirmed_minimum_spend=ctx.get("confirmed_minimum_spend"),
        party_size=ctx.get("party_size"),
        prohibited_times=ctx.get("prohibited_times", []),
        response_goal=scenario.get("response_goal", ""),
        alternatives_allowed=ctx.get("alternatives_allowed", False),
        allow_menu_discussion=ctx.get("allow_menu_discussion", False),
        allow_special_touches=ctx.get("allow_special_touches", False),
        allow_call_scheduling=ctx.get("allow_call_scheduling", False),
    )


def _integrity_from_scenario(scenario: dict[str, Any]) -> IntegrityCheckResult:
    return ResponseContextIntegrityGate.check(
        context_restaurant_name=scenario.get("context_restaurant_name", ""),
        context_room_name=scenario.get("context_room_name"),
        availability_restaurant_name=scenario.get("availability_restaurant_name"),
        availability_room_name=scenario.get("availability_room_name"),
    )


# ── Pytest fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def fixture_data() -> dict[str, Any]:
    assert _FIXTURE_PATH.exists(), f"Fixture not found: {_FIXTURE_PATH}"
    return _load_fixture()


@pytest.fixture(scope="module")
def scenarios(fixture_data: dict[str, Any]) -> list[dict[str, Any]]:
    return fixture_data["scenarios"]


# ── Fixture integrity ────────────────────────────────────────────────────────────


class TestFixtureIntegrity:
    def test_fixture_file_exists(self) -> None:
        assert _FIXTURE_PATH.exists()

    def test_fixture_loads_as_json(self) -> None:
        data = json.loads(_FIXTURE_PATH.read_text())
        assert "scenarios" in data
        assert "availability_records" in data

    def test_fixture_has_minimum_30_scenarios(self, scenarios: list[dict]) -> None:
        assert len(scenarios) >= 30, f"Expected ≥30 scenarios, got {len(scenarios)}"

    def test_all_scenarios_are_respond_unavailable(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert sc["response_goal"] == "RESPOND_UNAVAILABLE", (
                f"{sc['id']}: expected RESPOND_UNAVAILABLE, got {sc['response_goal']!r}"
            )

    def test_all_scenarios_have_confirmed_unavailable_contract(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert sc["availability_contract"] == "CONFIRMED_UNAVAILABLE", (
                f"{sc['id']}: expected CONFIRMED_UNAVAILABLE, got {sc['availability_contract']!r}"
            )

    def test_all_scenarios_have_required_fields(self, scenarios: list[dict]) -> None:
        required = {
            "id", "category", "description", "response_goal",
            "availability_contract", "draft_text", "expected",
        }
        for sc in scenarios:
            missing = required - sc.keys()
            assert not missing, f"{sc.get('id', '?')}: missing fields {missing}"

    def test_scenario_ids_are_unique(self, scenarios: list[dict]) -> None:
        ids = [sc["id"] for sc in scenarios]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_each_scenario_has_compliance_expectation(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert "compliance_passed" in sc["expected"], (
                f"{sc['id']}: missing expected.compliance_passed"
            )

    def test_each_scenario_has_auto_send_expectation(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert "ready_to_send_allowed" in sc["expected"], (
                f"{sc['id']}: missing expected.ready_to_send_allowed"
            )

    def test_all_scenarios_expect_gate_blocked(self, scenarios: list[dict]) -> None:
        """RESPOND_UNAVAILABLE is never auto-sendable."""
        for sc in scenarios:
            assert sc["expected"]["ready_to_send_allowed"] is False, (
                f"{sc['id']}: expected ready_to_send_allowed=false for RESPOND_UNAVAILABLE"
            )

    def test_all_scenarios_expect_compliance_passed(self, scenarios: list[dict]) -> None:
        """Deterministic text is always clean."""
        for sc in scenarios:
            assert sc["expected"]["compliance_passed"] is True, (
                f"{sc['id']}: expected compliance_passed=true (deterministic text)"
            )

    def test_customer_types_include_social_corporate_agency(self, scenarios: list[dict]) -> None:
        types = {sc.get("customer_type") for sc in scenarios if sc.get("customer_type")}
        assert "social" in types, "Missing social customer type coverage"
        assert "corporate" in types, "Missing corporate customer type coverage"
        assert "agency" in types, "Missing agency customer type coverage"

    def test_meal_periods_include_lunch_dinner_brunch(self, scenarios: list[dict]) -> None:
        periods = {sc.get("context", {}).get("meal_period") for sc in scenarios}
        assert "lunch" in periods, "Missing lunch meal period coverage"
        assert "dinner" in periods, "Missing dinner meal period coverage"
        assert "brunch" in periods, "Missing brunch meal period coverage"

    def test_categories_cover_required_coverage_dimensions(self, scenarios: list[dict]) -> None:
        categories = {sc["category"] for sc in scenarios}
        required = {
            "no_alternatives",
            "one_alternative_available",
            "two_alternatives_available",
            "past_alternative_rejected",
            "future_alternative_d_plus_1",
            "requested_date_in_past",
            "capacity_unsuitable_alternative",
        }
        missing = required - categories
        assert not missing, f"Missing required coverage categories: {missing}"

    def test_weekend_coverage_exists(self, scenarios: list[dict]) -> None:
        """At least some scenarios must use weekend dates (Saturday or Sunday)."""
        weekend_categories = {sc["category"] for sc in scenarios if "weekend" in sc["category"]}
        assert weekend_categories, "No weekend-category scenarios found"


# ── Past alternative rejection ────────────────────────────────────────────────────


class TestPastAlternativeRejection:
    """Verify that scenarios with only past alternatives set alternatives_allowed=false."""

    def test_past_alternative_scenarios_have_alternatives_not_allowed(
        self, scenarios: list[dict]
    ) -> None:
        past_alt_scenarios = [
            sc for sc in scenarios if sc["category"] == "past_alternative_rejected"
        ]
        assert past_alt_scenarios, "No past_alternative_rejected scenarios in fixture"
        for sc in past_alt_scenarios:
            ctx = sc.get("context", {})
            assert ctx.get("alternatives_allowed") is False, (
                f"{sc['id']}: past alternative scenario must have alternatives_allowed=false"
            )

    def test_past_alternative_scenarios_have_alt_rejection_reason(
        self, scenarios: list[dict]
    ) -> None:
        past_alt_scenarios = [
            sc for sc in scenarios if sc["category"] == "past_alternative_rejected"
        ]
        for sc in past_alt_scenarios:
            ctx = sc.get("context", {})
            assert ctx.get("alt_rejection_reason") == "all_alternatives_in_past", (
                f"{sc['id']}: expected alt_rejection_reason='all_alternatives_in_past'"
            )

    def test_past_alternative_scenarios_have_at_least_3_cases(
        self, scenarios: list[dict]
    ) -> None:
        count = sum(1 for sc in scenarios if sc["category"] == "past_alternative_rejected")
        assert count >= 3, f"Expected ≥3 past_alternative_rejected scenarios, got {count}"


# ── Future alternatives allowed ───────────────────────────────────────────────────


class TestFutureAlternativesAllowed:
    """Verify alternatives are offered only when confirmed available future dates exist."""

    def test_one_alt_scenarios_have_alternatives_allowed(self, scenarios: list[dict]) -> None:
        alt_scenarios = [
            sc for sc in scenarios if sc["category"] == "one_alternative_available"
        ]
        assert alt_scenarios, "No one_alternative_available scenarios found"
        for sc in alt_scenarios:
            ctx = sc.get("context", {})
            assert ctx.get("alternatives_allowed") is True, (
                f"{sc['id']}: one_alternative_available must have alternatives_allowed=true"
            )
            alts = ctx.get("alternative_dates", [])
            assert len(alts) == 1, (
                f"{sc['id']}: expected exactly 1 alternative_date, got {len(alts)}"
            )

    def test_two_alt_scenarios_have_alternatives_allowed(self, scenarios: list[dict]) -> None:
        alt_scenarios = [
            sc for sc in scenarios if sc["category"] == "two_alternatives_available"
        ]
        assert alt_scenarios, "No two_alternatives_available scenarios found"
        for sc in alt_scenarios:
            ctx = sc.get("context", {})
            assert ctx.get("alternatives_allowed") is True, (
                f"{sc['id']}: two_alternatives_available must have alternatives_allowed=true"
            )
            alts = ctx.get("alternative_dates", [])
            assert len(alts) == 2, (
                f"{sc['id']}: expected exactly 2 alternative_dates, got {len(alts)}"
            )

    def test_d_plus_1_scenarios_have_alternatives_allowed(self, scenarios: list[dict]) -> None:
        d1_scenarios = [
            sc for sc in scenarios if sc["category"] == "future_alternative_d_plus_1"
        ]
        assert d1_scenarios, "No future_alternative_d_plus_1 scenarios found"
        for sc in d1_scenarios:
            ctx = sc.get("context", {})
            assert ctx.get("alternatives_allowed") is True, (
                f"{sc['id']}: future_alternative_d_plus_1 must have alternatives_allowed=true"
            )

    def test_no_alternatives_scenarios_have_alternatives_not_allowed(
        self, scenarios: list[dict]
    ) -> None:
        no_alt_scenarios = [
            sc for sc in scenarios
            if sc["category"] in ("no_alternatives", "no_alternatives_weekend")
        ]
        assert no_alt_scenarios, "No no_alternatives scenarios found"
        for sc in no_alt_scenarios:
            ctx = sc.get("context", {})
            assert ctx.get("alternatives_allowed") is False, (
                f"{sc['id']}: no_alternatives scenario must have alternatives_allowed=false"
            )

    def test_capacity_unsuitable_scenarios_have_alternatives_not_allowed(
        self, scenarios: list[dict]
    ) -> None:
        cap_scenarios = [
            sc for sc in scenarios if sc["category"] == "capacity_unsuitable_alternative"
        ]
        assert cap_scenarios, "No capacity_unsuitable_alternative scenarios found"
        for sc in cap_scenarios:
            ctx = sc.get("context", {})
            assert ctx.get("alternatives_allowed") is False, (
                f"{sc['id']}: capacity_unsuitable must have alternatives_allowed=false"
            )
            assert ctx.get("alt_rejection_reason") == "capacity_unsuitable", (
                f"{sc['id']}: expected alt_rejection_reason='capacity_unsuitable'"
            )


# ── Deterministic text compliance ─────────────────────────────────────────────────


class TestDeterministicTextCompliance:
    """All RESPOND_UNAVAILABLE drafts must pass compliance when using deterministic text."""

    def test_all_scenarios_pass_compliance_with_deterministic_text(
        self, scenarios: list[dict]
    ) -> None:
        for sc in scenarios:
            draft_text = _build_deterministic_unavailable_text(sc)
            ctx = _context_from_scenario(sc)
            result = DraftComplianceValidator.validate(draft_text, ctx)
            assert result.passed, (
                f"{sc['id']}: deterministic text failed compliance — "
                f"violations: {result.violations}"
            )

    def test_deterministic_text_contains_no_availability_confirmation(
        self, scenarios: list[dict]
    ) -> None:
        """Deterministic unavailable text must not confirm availability."""
        for sc in scenarios:
            draft_text = _build_deterministic_unavailable_text(sc)
            assert "is available" not in draft_text.lower(), (
                f"{sc['id']}: deterministic text must not confirm availability"
            )
            assert "pleased to confirm" not in draft_text.lower(), (
                f"{sc['id']}: deterministic text must not use 'pleased to confirm'"
            )

    def test_deterministic_text_does_not_invent_minimum_spend(
        self, scenarios: list[dict]
    ) -> None:
        """Deterministic unavailable text must not mention minimum spend."""
        for sc in scenarios:
            draft_text = _build_deterministic_unavailable_text(sc)
            assert "minimum spend" not in draft_text.lower(), (
                f"{sc['id']}: deterministic text must not mention minimum spend"
            )

    def test_deterministic_text_addresses_guest_by_first_name(
        self, scenarios: list[dict]
    ) -> None:
        """Deterministic text must start with 'Dear {first_name}'."""
        for sc in scenarios:
            draft_text = _build_deterministic_unavailable_text(sc)
            ctx_data = sc.get("context", {})
            guest_name = ctx_data.get("guest_first_name", "there")
            assert draft_text.startswith(f"Dear {guest_name}"), (
                f"{sc['id']}: expected draft to start with 'Dear {guest_name}'"
            )


# ── Integrity gate ────────────────────────────────────────────────────────────────


class TestIntegrityGate:
    def test_all_scenarios_pass_integrity_gate(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            result = _integrity_from_scenario(sc)
            assert result.passed, (
                f"{sc['id']}: integrity gate failed — violations: {result.violations}"
            )


# ── Auto-send gate ────────────────────────────────────────────────────────────────


class TestAutoSendGate:
    def test_all_scenarios_are_gate_blocked(self, scenarios: list[dict]) -> None:
        """RESPOND_UNAVAILABLE must never be auto-sendable."""
        for sc in scenarios:
            draft_text = _build_deterministic_unavailable_text(sc)
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(draft_text, ctx)
            integrity = _integrity_from_scenario(sc)
            gate = AutoSendReadinessGate.evaluate(
                response_goal=sc["response_goal"],
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
                integrity_result=integrity,
            )
            assert not gate.auto_send_allowed, (
                f"{sc['id']}: RESPOND_UNAVAILABLE must be gate-blocked but was allowed"
            )

    def test_all_gate_blocked_scenarios_match_expected(self, scenarios: list[dict]) -> None:
        """All expected outcomes must match actual gate results."""
        for sc in scenarios:
            draft_text = _build_deterministic_unavailable_text(sc)
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(draft_text, ctx)
            integrity = _integrity_from_scenario(sc)
            gate = AutoSendReadinessGate.evaluate(
                response_goal=sc["response_goal"],
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
                integrity_result=integrity,
            )
            exp = sc["expected"]
            assert compliance.passed == exp["compliance_passed"], (
                f"{sc['id']}: compliance mismatch — "
                f"expected {exp['compliance_passed']}, got {compliance.passed}. "
                f"Violations: {compliance.violations}"
            )
            assert gate.auto_send_allowed == exp["ready_to_send_allowed"], (
                f"{sc['id']}: auto-send mismatch — "
                f"expected {exp['ready_to_send_allowed']}, got {gate.auto_send_allowed}"
            )


# ── Goal separation ────────────────────────────────────────────────────────────────


class TestGoalSeparation:
    """Regression report separates unavailable results from confirm/acknowledge results."""

    def test_all_scenarios_are_respond_unavailable_goal(self, scenarios: list[dict]) -> None:
        goals = {sc["response_goal"] for sc in scenarios}
        assert goals == {"RESPOND_UNAVAILABLE"}, (
            f"Fixture should contain only RESPOND_UNAVAILABLE scenarios, got: {goals}"
        )

    def test_no_confirm_available_scenarios_present(self, scenarios: list[dict]) -> None:
        confirm_scenarios = [sc for sc in scenarios if sc["response_goal"] == "CONFIRM_AVAILABLE"]
        assert not confirm_scenarios, (
            "CONFIRM_AVAILABLE scenarios must not appear in the unavailable regression fixture"
        )

    def test_no_acknowledge_scenarios_present(self, scenarios: list[dict]) -> None:
        ack_scenarios = [
            sc for sc in scenarios
            if sc["response_goal"] == "ACKNOWLEDGE_AND_CHECK_AVAILABILITY"
        ]
        assert not ack_scenarios, (
            "ACKNOWLEDGE_AND_CHECK_AVAILABILITY scenarios must not appear in unavailable fixture"
        )
