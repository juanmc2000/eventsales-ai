"""Draft Quality Regression Suite (RESP-015).

Evaluates draft quality cases using DraftComplianceValidator and
AutoSendReadinessGate. All checks are deterministic — no LLM calls.

Fixture: tests/fixtures/draft_quality_cases.json (25 scenarios)

Coverage (RESP-008 validator checks):
- availability_claim:  over-claim and clean-acknowledge patterns
- spend_wording:       recommended/optional/suggested spend violations
- alternative_dates:   invented alternatives when CONFIRMED_UNAVAILABLE (email_02/03)
- fake_url:            placeholder booking links
- unconfirmed_time:    guest preference stated as agreed
- auto_send_gate:      compliance-pass but gate-block scenarios
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.modules.ai.draft_compliance_validator import (
    DraftComplianceValidator,
    ValidationContext,
)

try:
    from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
    from app.modules.enquiries.response_context_integrity_gate import IntegrityCheckResult as _IntegrityCheckResult
    _GATE_AVAILABLE = True
except ImportError:
    AutoSendReadinessGate = None  # type: ignore[assignment,misc]
    _IntegrityCheckResult = None  # type: ignore[assignment,misc]
    _GATE_AVAILABLE = False


def _passing_integrity():
    return _IntegrityCheckResult(passed=True) if _IntegrityCheckResult else None

_requires_gate = pytest.mark.skipif(
    not _GATE_AVAILABLE,
    reason="AutoSendReadinessGate not available (RESP-014 not merged)",
)

# ── Paths ──────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "draft_quality_cases.json"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _load_scenarios() -> list[dict[str, Any]]:
    data = json.loads(_FIXTURE_PATH.read_text())
    return data["scenarios"]


def _context_from_scenario(scenario: dict[str, Any]) -> ValidationContext:
    ctx_data = scenario.get("context", {})
    return ValidationContext(
        availability_contract=scenario.get("availability_contract", "NOT_CHECKED"),
        clarification_questions=ctx_data.get("clarification_questions", []),
        confirmed_minimum_spend=ctx_data.get("confirmed_minimum_spend"),
        prohibited_times=ctx_data.get("prohibited_times", []),
        response_goal=scenario.get("response_goal", ""),
    )


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def scenarios() -> list[dict[str, Any]]:
    assert _FIXTURE_PATH.exists(), f"Fixture not found: {_FIXTURE_PATH}"
    return _load_scenarios()


# ── Fixture integrity ──────────────────────────────────────────────────────────


class TestFixtureIntegrity:
    def test_fixture_loads(self) -> None:
        assert _FIXTURE_PATH.exists()
        data = json.loads(_FIXTURE_PATH.read_text())
        assert "scenarios" in data

    def test_fixture_has_minimum_scenarios(self, scenarios: list[dict]) -> None:
        assert len(scenarios) >= 20, f"Expected ≥20 scenarios, got {len(scenarios)}"

    def test_all_scenarios_have_required_fields(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert "id" in sc, f"Missing 'id' in scenario"
            assert "draft_text" in sc, f"Missing 'draft_text' in {sc.get('id', '?')}"
            assert "response_goal" in sc, f"Missing 'response_goal' in {sc.get('id', '?')}"
            assert "availability_contract" in sc, f"Missing 'availability_contract' in {sc.get('id', '?')}"
            assert "expected" in sc, f"Missing 'expected' in {sc.get('id', '?')}"

    def test_scenario_ids_are_unique(self, scenarios: list[dict]) -> None:
        ids = [sc["id"] for sc in scenarios]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_each_scenario_has_compliance_expectation(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert "compliance_passed" in sc["expected"], (
                f"{sc['id']}: missing expected.compliance_passed"
            )


# ── Compliance: expected outcomes ─────────────────────────────────────────────


class TestComplianceExpectedOutcomes:
    def test_expected_pass_scenarios_pass(self, scenarios: list[dict]) -> None:
        """All scenarios marked expected.compliance_passed=true must pass."""
        failures = []
        for sc in scenarios:
            if not sc["expected"].get("compliance_passed", True):
                continue
            ctx = _context_from_scenario(sc)
            result = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            if not result.passed:
                failures.append(
                    f"{sc['id']} ({sc['description']}): unexpected violations: "
                    + "; ".join(result.violations)
                )
        assert not failures, (
            "Expected-pass scenarios had violations:\n" + "\n".join(failures)
        )

    def test_expected_fail_scenarios_fail(self, scenarios: list[dict]) -> None:
        """All scenarios marked expected.compliance_passed=false must fail."""
        surprises = []
        for sc in scenarios:
            if sc["expected"].get("compliance_passed", True):
                continue
            ctx = _context_from_scenario(sc)
            result = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            if result.passed:
                surprises.append(
                    f"{sc['id']} ({sc['description']}): expected violation but none found"
                )
        assert not surprises, (
            "Expected-fail scenarios passed unexpectedly:\n" + "\n".join(surprises)
        )

    def test_validator_runs_on_all_scenarios(self, scenarios: list[dict]) -> None:
        """Validator must return a valid ComplianceResult for every scenario."""
        for sc in scenarios:
            ctx = _context_from_scenario(sc)
            result = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            assert isinstance(result.passed, bool), f"{sc['id']}: passed must be bool"
            assert isinstance(result.violations, list), f"{sc['id']}: violations must be list"
            assert isinstance(result.unsafe_to_send, bool), f"{sc['id']}: unsafe_to_send must be bool"
            # unsafe_to_send must be the inverse of passed
            assert result.unsafe_to_send == (not result.passed), f"{sc['id']}: unsafe_to_send mismatch"


# ── Auto-send gate: expected outcomes ─────────────────────────────────────────


class TestAutoSendExpectedOutcomes:
    @_requires_gate
    def test_expected_auto_send_allowed_scenarios_pass_gate(self, scenarios: list[dict]) -> None:
        """All scenarios marked expected.ready_to_send_allowed=true must pass the gate."""
        failures = []
        for sc in scenarios:
            if not sc["expected"].get("ready_to_send_allowed", False):
                continue
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            gate = AutoSendReadinessGate.evaluate(
                response_goal=sc.get("response_goal", ""),
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
                integrity_result=_passing_integrity(),
            )
            if not gate.auto_send_allowed:
                failures.append(
                    f"{sc['id']}: expected auto-send allowed but blocked: "
                    + "; ".join(gate.auto_send_blockers)
                )
        assert not failures, (
            "Expected-allowed scenarios were blocked:\n" + "\n".join(failures)
        )

    @_requires_gate
    def test_expected_auto_send_blocked_scenarios_fail_gate(self, scenarios: list[dict]) -> None:
        """All scenarios marked expected.ready_to_send_allowed=false must fail the gate."""
        surprises = []
        for sc in scenarios:
            if sc["expected"].get("ready_to_send_allowed", True):
                continue
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            gate = AutoSendReadinessGate.evaluate(
                response_goal=sc.get("response_goal", ""),
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
                integrity_result=_passing_integrity(),
            )
            if gate.auto_send_allowed:
                surprises.append(
                    f"{sc['id']} ({sc['description']}): expected gate blocked but auto-send was allowed"
                )
        assert not surprises, (
            "Expected-blocked scenarios were auto-send allowed:\n" + "\n".join(surprises)
        )

    @_requires_gate
    def test_gate_runs_on_all_scenarios(self, scenarios: list[dict]) -> None:
        """Gate must return a valid result for every scenario."""
        for sc in scenarios:
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            gate = AutoSendReadinessGate.evaluate(
                response_goal=sc.get("response_goal", ""),
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
                integrity_result=_passing_integrity(),
            )
            assert isinstance(gate.auto_send_allowed, bool), f"{sc['id']}: auto_send_allowed must be bool"
            assert isinstance(gate.auto_send_blockers, list), f"{sc['id']}: auto_send_blockers must be list"


# ── Category-specific tests ────────────────────────────────────────────────────


class TestAvailabilityClaimCategory:
    def test_not_checked_availability_claim_blocked(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_006")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed
        assert any("NOT_CHECKED" in v or "availability" in v.lower() for v in result.violations)

    def test_confirmed_available_passes(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_001")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert result.passed

    def test_pending_date_confirmation_blocks_claim(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_009")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed


class TestAlternativeDatesCategory:
    def test_email_02_pattern_blocked(self, scenarios: list[dict]) -> None:
        """email_02 alternative-date hallucination pattern is caught."""
        tc = next(sc for sc in scenarios if sc["id"] == "tc_010")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed
        assert any("alternative" in v.lower() for v in result.violations)

    def test_email_03_pattern_blocked(self, scenarios: list[dict]) -> None:
        """email_03 'how about' alternative pattern is caught."""
        tc = next(sc for sc in scenarios if sc["id"] == "tc_011")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed

    def test_other_dates_pattern_blocked(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_012")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed

    def test_clean_decline_passes(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_013")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert result.passed


class TestSpendLanguageCategory:
    def test_recommended_spend_blocked(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_003")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed
        assert any("mandatory" in v.lower() or "recommended" in v.lower() for v in result.violations)

    def test_optional_spend_blocked(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_004")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed

    def test_mandatory_spend_passes(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_002")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert result.passed


class TestUnconfirmedTimeCategory:
    def test_confirmed_time_from_guest_blocked(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_016")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed
        assert any("7pm" in v or "time" in v.lower() for v in result.violations)

    def test_mentioned_not_confirmed_passes(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_017")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert result.passed


class TestFakeUrlCategory:
    def test_form_link_placeholder_blocked(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_014")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed

    def test_booking_form_url_placeholder_blocked(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_015")
        ctx = _context_from_scenario(tc)
        result = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert not result.passed


class TestAutoSendGateCategory:
    @_requires_gate
    def test_respond_unavailable_clean_passes_compliance_but_not_gate(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_013")
        ctx = _context_from_scenario(tc)
        compliance = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        assert compliance.passed
        gate = AutoSendReadinessGate.evaluate(
            response_goal=tc["response_goal"],
            draft_compliance_result=compliance,
            date_status=tc.get("date_status", "resolved"),
            integrity_result=_passing_integrity(),
        )
        assert not gate.auto_send_allowed

    @_requires_gate
    def test_ambiguous_date_blocks_gate(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_020")
        ctx = _context_from_scenario(tc)
        compliance = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        gate = AutoSendReadinessGate.evaluate(
            response_goal=tc["response_goal"],
            draft_compliance_result=compliance,
            date_status=tc.get("date_status", "resolved"),
            integrity_result=_passing_integrity(),
        )
        assert not gate.auto_send_allowed
        assert any("ambiguous" in b.lower() for b in gate.auto_send_blockers)

    @_requires_gate
    def test_escalate_to_human_blocks_gate(self, scenarios: list[dict]) -> None:
        tc = next(sc for sc in scenarios if sc["id"] == "tc_021")
        ctx = _context_from_scenario(tc)
        compliance = DraftComplianceValidator.validate(tc["draft_text"], ctx)
        gate = AutoSendReadinessGate.evaluate(
            response_goal=tc["response_goal"],
            draft_compliance_result=compliance,
            date_status=tc.get("date_status", "resolved"),
            integrity_result=_passing_integrity(),
        )
        assert not gate.auto_send_allowed


# ── Regression summary report ─────────────────────────────────────────────────


class TestRegressionSummary:
    """Runs the full suite and prints a summary.

    Never fails on its own — regressions are caught by the outcome tests above.
    Prints pass rate and top failure categories for CI visibility.
    """

    def test_print_full_summary(self, scenarios: list[dict], capsys) -> None:
        total = len(scenarios)
        compliance_passed_count = 0
        auto_send_allowed_count = 0
        violation_category_counts: dict[str, int] = {}

        for sc in scenarios:
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            if compliance.passed:
                compliance_passed_count += 1
            if _GATE_AVAILABLE:
                gate = AutoSendReadinessGate.evaluate(
                    response_goal=sc.get("response_goal", ""),
                    draft_compliance_result=compliance,
                    date_status=sc.get("date_status", "resolved"),
                    integrity_result=_passing_integrity(),
                )
                if gate.auto_send_allowed:
                    auto_send_allowed_count += 1
            for v in compliance.violations:
                v_lower = v.lower()
                if "contract" in v_lower:
                    cat = "availability_overclaim"
                elif "alternative" in v_lower:
                    cat = "alternative_dates"
                elif "mandatory" in v_lower or "recommended" in v_lower or "optional" in v_lower:
                    cat = "spend_soft_language"
                elif "link" in v_lower or "url" in v_lower or "placeholder" in v_lower:
                    cat = "fake_url"
                elif "time" in v_lower:
                    cat = "unconfirmed_time"
                else:
                    cat = "other"
                violation_category_counts[cat] = violation_category_counts.get(cat, 0) + 1

        compliance_rate = compliance_passed_count / total * 100
        auto_send_rate = auto_send_allowed_count / total * 100

        print(f"\n{'=' * 60}")
        print("DRAFT QUALITY REGRESSION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Scenarios:              {total}")
        print(f"Compliance pass rate:   {compliance_rate:.1f}%  ({compliance_passed_count}/{total})")
        print(f"Auto-send allowed rate: {auto_send_rate:.1f}%  ({auto_send_allowed_count}/{total})")
        if violation_category_counts:
            print("\nTop violation categories:")
            for cat, count in sorted(violation_category_counts.items(), key=lambda x: -x[1]):
                print(f"  {cat:<28}  {count}")
        print(f"{'=' * 60}")

        # The fixture is designed so ~13/25 scenarios pass compliance
        assert compliance_rate >= 40.0, f"Compliance pass rate {compliance_rate:.1f}% below expected minimum"
