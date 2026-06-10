"""First Response Safety Regression Suite (TEST-011).

Evaluates 25 first-response scenarios using the full V6 governance stack:
  - DraftComplianceValidator  (10 deterministic checks)
  - ResponseContextIntegrityGate  (RESP-021)
  - AutoSendReadinessGate  (RESP-022, 5 rules)

All checks are deterministic — no LLM calls are made.

Fixture: tests/fixtures/first_response_safety_cases.json (25 scenarios, 6 availability records)

Coverage:
  compliance_pass          — clean drafts that satisfy every rule
  hallucinated_availability — overclaim when contract is NOT_CHECKED
  alternative_dates         — invented alternatives when CONFIRMED_UNAVAILABLE
  room_suitability_unavailable — suitability language when slot is unavailable
  spend_soft_language       — 'recommended' instead of mandatory minimum
  fake_url                  — placeholder booking form links
  unconfirmed_time          — guest-stated time confirmed as agreed
  hosting_language          — prohibited 'delighted to host' patterns
  invented_sla              — invented 24-hour response commitments
  invented_questions        — questions not in approved clarification list
  forbidden_topics_menu     — menu/dietary discussion at acknowledgement stage
  gate_blocked_goal         — compliance passes but goal not auto-sendable
  gate_blocked_date         — compliance passes but date status blocks auto-send
  context_mismatch          — integrity gate blocks on restaurant name mismatch
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

# ── Paths ───────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "first_response_safety_cases.json"


# ── Helpers ─────────────────────────────────────────────────────────────────────


_DETERMINISTIC_GOALS: frozenset[str] = frozenset({"RESPOND_UNAVAILABLE"})


def _load_scenarios() -> list[dict[str, Any]]:
    data = json.loads(_FIXTURE_PATH.read_text())
    return data["scenarios"]


def _get_production_draft_text(scenario: dict[str, Any]) -> str:
    """RESP-032: Return production-equivalent draft text for a scenario.

    For RESPOND_UNAVAILABLE, build the deterministic unavailable draft using
    FirstResponseCopyLibrary — matching production DraftGenerationService routing.
    For all other goals, use the fixture draft_text (LLM-generated test draft).
    """
    goal = scenario.get("response_goal", "")
    if goal in _DETERMINISTIC_GOALS:
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
    return scenario.get("draft_text", "")


def _context_from_scenario(scenario: dict[str, Any]) -> ValidationContext:
    ctx = scenario.get("context", {})
    return ValidationContext(
        availability_contract=scenario.get("availability_contract", "NOT_CHECKED"),
        clarification_questions=ctx.get("clarification_questions", []),
        confirmed_minimum_spend=ctx.get("confirmed_minimum_spend"),
        party_size=ctx.get("party_size"),
        prohibited_times=ctx.get("prohibited_times", []),
        response_goal=scenario.get("response_goal", ""),
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


def _categorise_violation(violation: str) -> str:
    v = violation.lower()
    if "contract" in v and "available" in v:
        return "hallucinated_availability"
    if "alternative" in v:
        return "alternative_dates"
    if "suitability" in v or "perfect for" in v or "ideal for" in v or "well-suited" in v:
        return "room_suitability_unavailable"
    if "spend" in v or "mandatory" in v:
        return "spend_soft_language"
    if "link" in v or "url" in v or "placeholder" in v:
        return "fake_url"
    if "time" in v and "confirmed" in v:
        return "unconfirmed_time"
    if "hosting" in v:
        return "hosting_language"
    if "sla" in v or "within" in v or "hours" in v or "commitment" in v:
        return "invented_sla"
    if "question" in v:
        return "invented_questions"
    if "menu" in v or "dietary" in v or "special touch" in v or "call" in v:
        return "forbidden_topics"
    return "other"


# ── Pytest fixture ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def scenarios() -> list[dict[str, Any]]:
    assert _FIXTURE_PATH.exists(), f"Fixture not found: {_FIXTURE_PATH}"
    return _load_scenarios()


# ── Fixture integrity ───────────────────────────────────────────────────────────


class TestFixtureIntegrity:
    def test_fixture_file_exists(self) -> None:
        assert _FIXTURE_PATH.exists()

    def test_fixture_loads_as_json(self) -> None:
        data = json.loads(_FIXTURE_PATH.read_text())
        assert "scenarios" in data
        assert "availability_records" in data

    def test_fixture_has_six_availability_records(self) -> None:
        data = json.loads(_FIXTURE_PATH.read_text())
        assert len(data["availability_records"]) == 6

    def test_fixture_has_minimum_25_scenarios(self, scenarios: list[dict]) -> None:
        assert len(scenarios) >= 25, f"Expected ≥25 scenarios, got {len(scenarios)}"

    def test_all_scenarios_have_required_fields(self, scenarios: list[dict]) -> None:
        required = {"id", "category", "description", "response_goal", "availability_contract", "draft_text", "expected"}
        for sc in scenarios:
            missing = required - sc.keys()
            assert not missing, f"{sc.get('id', '?')}: missing fields {missing}"

    def test_scenario_ids_are_unique(self, scenarios: list[dict]) -> None:
        ids = [sc["id"] for sc in scenarios]
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_each_scenario_has_compliance_expectation(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert "compliance_passed" in sc["expected"], f"{sc['id']}: missing expected.compliance_passed"

    def test_each_scenario_has_auto_send_expectation(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            assert "ready_to_send_allowed" in sc["expected"], f"{sc['id']}: missing expected.ready_to_send_allowed"

    def test_categories_cover_required_violation_types(self, scenarios: list[dict]) -> None:
        categories = {sc["category"] for sc in scenarios}
        required_categories = {
            "compliance_pass",
            "hallucinated_availability",
            "alternative_dates",
            "gate_blocked_goal",
            "gate_blocked_date",
            "context_mismatch",
        }
        missing = required_categories - categories
        assert not missing, f"Missing required categories: {missing}"

    def test_customer_types_include_social_corporate_agency(self, scenarios: list[dict]) -> None:
        types = {sc.get("customer_type") for sc in scenarios if sc.get("customer_type")}
        assert "social" in types
        assert "corporate" in types
        assert "agency" in types


# ── Compliance outcomes ─────────────────────────────────────────────────────────


class TestComplianceOutcomes:
    def test_expected_pass_scenarios_pass(self, scenarios: list[dict]) -> None:
        failures = []
        for sc in scenarios:
            if not sc["expected"].get("compliance_passed", True):
                continue
            ctx = _context_from_scenario(sc)
            # RESP-032: use production-equivalent draft text (deterministic for RESPOND_UNAVAILABLE)
            draft_text = _get_production_draft_text(sc)
            result = DraftComplianceValidator.validate(draft_text, ctx)
            if not result.passed:
                failures.append(
                    f"{sc['id']} ({sc['description']}): unexpected violations: "
                    + "; ".join(result.violations)
                )
        assert not failures, "Expected-pass scenarios had violations:\n" + "\n".join(failures)

    def test_expected_fail_scenarios_fail(self, scenarios: list[dict]) -> None:
        surprises = []
        for sc in scenarios:
            if sc["expected"].get("compliance_passed", True):
                continue
            ctx = _context_from_scenario(sc)
            # RESP-032: use production-equivalent draft text
            draft_text = _get_production_draft_text(sc)
            result = DraftComplianceValidator.validate(draft_text, ctx)
            if result.passed:
                surprises.append(f"{sc['id']} ({sc['description']}): expected violation but none found")
        assert not surprises, "Expected-fail scenarios passed unexpectedly:\n" + "\n".join(surprises)

    def test_validator_returns_valid_result_for_all_scenarios(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            ctx = _context_from_scenario(sc)
            # RESP-032: use production-equivalent draft text
            draft_text = _get_production_draft_text(sc)
            result = DraftComplianceValidator.validate(draft_text, ctx)
            assert isinstance(result.passed, bool), f"{sc['id']}: passed must be bool"
            assert isinstance(result.violations, list), f"{sc['id']}: violations must be list"
            assert result.unsafe_to_send == (not result.passed), f"{sc['id']}: unsafe_to_send mismatch"


# ── Integrity gate outcomes ─────────────────────────────────────────────────────


class TestIntegrityGateOutcomes:
    def test_expected_integrity_pass_scenarios_pass(self, scenarios: list[dict]) -> None:
        failures = []
        for sc in scenarios:
            if not sc["expected"].get("integrity_passed", True):
                continue
            result = _integrity_from_scenario(sc)
            if not result.passed:
                failures.append(
                    f"{sc['id']}: expected integrity pass but got violations: "
                    + "; ".join(result.violations)
                )
        assert not failures, "Expected-integrity-pass scenarios failed:\n" + "\n".join(failures)

    def test_expected_integrity_fail_scenarios_fail(self, scenarios: list[dict]) -> None:
        surprises = []
        for sc in scenarios:
            if sc["expected"].get("integrity_passed", True):
                continue
            result = _integrity_from_scenario(sc)
            if result.passed:
                surprises.append(f"{sc['id']} ({sc['description']}): expected integrity failure but passed")
        assert not surprises, "Expected-integrity-fail scenarios passed unexpectedly:\n" + "\n".join(surprises)

    def test_integrity_gate_returns_valid_result_for_all_scenarios(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            result = _integrity_from_scenario(sc)
            assert isinstance(result.passed, bool), f"{sc['id']}: passed must be bool"
            assert isinstance(result.violations, list), f"{sc['id']}: violations must be list"
            assert isinstance(result.requires_review, bool), f"{sc['id']}: requires_review must be bool"

    def test_context_mismatch_scenario_fails_integrity(self, scenarios: list[dict]) -> None:
        mismatch = next(sc for sc in scenarios if sc["category"] == "context_mismatch")
        result = _integrity_from_scenario(mismatch)
        assert result.passed is False
        assert result.requires_review is True
        assert len(result.violations) >= 1


# ── Auto-send gate outcomes ─────────────────────────────────────────────────────


class TestAutoSendGateOutcomes:
    def _evaluate(self, sc: dict[str, Any]):
        ctx = _context_from_scenario(sc)
        compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)
        integrity = _integrity_from_scenario(sc)
        return AutoSendReadinessGate.evaluate(
            response_goal=sc.get("response_goal", ""),
            draft_compliance_result=compliance,
            date_status=sc.get("date_status", "resolved"),
            integrity_result=integrity,
        )

    def test_expected_allowed_scenarios_pass_gate(self, scenarios: list[dict]) -> None:
        failures = []
        for sc in scenarios:
            if not sc["expected"].get("ready_to_send_allowed", False):
                continue
            gate = self._evaluate(sc)
            if not gate.auto_send_allowed:
                failures.append(
                    f"{sc['id']}: expected auto-send allowed but blocked: "
                    + "; ".join(gate.auto_send_blockers)
                )
        assert not failures, "Expected-allowed scenarios were blocked:\n" + "\n".join(failures)

    def test_expected_blocked_scenarios_fail_gate(self, scenarios: list[dict]) -> None:
        surprises = []
        for sc in scenarios:
            if sc["expected"].get("ready_to_send_allowed", True):
                continue
            gate = self._evaluate(sc)
            if gate.auto_send_allowed:
                surprises.append(f"{sc['id']} ({sc['description']}): expected gate blocked but auto-send allowed")
        assert not surprises, "Expected-blocked scenarios passed gate unexpectedly:\n" + "\n".join(surprises)

    def test_gate_returns_valid_result_for_all_scenarios(self, scenarios: list[dict]) -> None:
        for sc in scenarios:
            gate = self._evaluate(sc)
            assert isinstance(gate.auto_send_allowed, bool), f"{sc['id']}: auto_send_allowed must be bool"
            assert isinstance(gate.auto_send_blockers, list), f"{sc['id']}: auto_send_blockers must be list"
            assert isinstance(gate.review_required_reason, str), f"{sc['id']}: review_required_reason must be str"


# ── Category-specific coverage ──────────────────────────────────────────────────


class TestViolationCategories:
    def _compliance(self, sc: dict) -> Any:
        return DraftComplianceValidator.validate(sc["draft_text"], _context_from_scenario(sc))

    def test_hallucinated_availability_scenarios_fail_compliance(self, scenarios: list[dict]) -> None:
        affected = [sc for sc in scenarios if sc["category"] == "hallucinated_availability"]
        assert len(affected) >= 2, "Expected ≥2 hallucinated_availability scenarios"
        for sc in affected:
            result = self._compliance(sc)
            assert result.passed is False, f"{sc['id']}: expected compliance failure"
            assert any("contract" in v.lower() or "available" in v.lower() for v in result.violations)

    def test_alternative_dates_scenarios_fail_compliance(self, scenarios: list[dict]) -> None:
        affected = [sc for sc in scenarios if sc["category"] == "alternative_dates"]
        assert len(affected) >= 2, "Expected ≥2 alternative_dates scenarios"
        for sc in affected:
            result = self._compliance(sc)
            assert result.passed is False, f"{sc['id']}: expected compliance failure"
            assert any("alternative" in v.lower() for v in result.violations)

    def test_room_suitability_unavailable_fails_compliance(self, scenarios: list[dict]) -> None:
        affected = [sc for sc in scenarios if sc["category"] == "room_suitability_unavailable"]
        assert len(affected) >= 1, "Expected ≥1 room_suitability_unavailable scenario"
        for sc in affected:
            result = self._compliance(sc)
            assert result.passed is False, f"{sc['id']}: expected compliance failure"

    def test_spend_soft_language_fails_compliance(self, scenarios: list[dict]) -> None:
        sc = next(s for s in scenarios if s["category"] == "spend_soft_language")
        result = self._compliance(sc)
        assert result.passed is False
        assert any("spend" in v.lower() or "mandatory" in v.lower() for v in result.violations)

    def test_fake_url_fails_compliance(self, scenarios: list[dict]) -> None:
        sc = next(s for s in scenarios if s["category"] == "fake_url")
        result = self._compliance(sc)
        assert result.passed is False
        assert any("link" in v.lower() or "url" in v.lower() or "placeholder" in v.lower() for v in result.violations)

    def test_unconfirmed_time_fails_compliance(self, scenarios: list[dict]) -> None:
        sc = next(s for s in scenarios if s["category"] == "unconfirmed_time")
        result = self._compliance(sc)
        assert result.passed is False
        assert any("time" in v.lower() for v in result.violations)

    def test_hosting_language_fails_compliance(self, scenarios: list[dict]) -> None:
        sc = next(s for s in scenarios if s["category"] == "hosting_language")
        result = self._compliance(sc)
        assert result.passed is False
        assert any("hosting" in v.lower() for v in result.violations)

    def test_invented_sla_fails_compliance(self, scenarios: list[dict]) -> None:
        sc = next(s for s in scenarios if s["category"] == "invented_sla")
        result = self._compliance(sc)
        assert result.passed is False

    def test_invented_questions_fails_compliance(self, scenarios: list[dict]) -> None:
        sc = next(s for s in scenarios if s["category"] == "invented_questions")
        result = self._compliance(sc)
        assert result.passed is False
        assert any("question" in v.lower() for v in result.violations)

    def test_forbidden_topics_menu_fails_compliance(self, scenarios: list[dict]) -> None:
        sc = next(s for s in scenarios if s["category"] == "forbidden_topics_menu")
        result = self._compliance(sc)
        assert result.passed is False
        assert any("menu" in v.lower() or "dietary" in v.lower() for v in result.violations)

    def test_gate_blocked_goal_scenarios_pass_compliance(self, scenarios: list[dict]) -> None:
        affected = [sc for sc in scenarios if sc["category"] == "gate_blocked_goal"]
        assert len(affected) >= 4, "Expected ≥4 gate_blocked_goal scenarios"
        for sc in affected:
            result = self._compliance(sc)
            assert result.passed is True, f"{sc['id']}: expected compliance pass, got violations: {result.violations}"

    def test_gate_blocked_date_scenarios_pass_compliance(self, scenarios: list[dict]) -> None:
        affected = [sc for sc in scenarios if sc["category"] == "gate_blocked_date"]
        assert len(affected) >= 2, "Expected ≥2 gate_blocked_date scenarios"
        for sc in affected:
            result = self._compliance(sc)
            assert result.passed is True, f"{sc['id']}: expected compliance pass, got violations: {result.violations}"


# ── Regression summary ──────────────────────────────────────────────────────────


class TestSafetyRegressionSummary:
    """Runs every scenario and prints a structured summary.

    This test never fails on its own — regressions are caught by the
    outcome tests above. The summary is printed for CI visibility.
    """

    def test_print_full_summary(self, scenarios: list[dict], capsys) -> None:
        total = len(scenarios)
        compliance_passed_count = 0
        auto_send_allowed_count = 0
        integrity_passed_count = 0
        violation_category_counts: dict[str, int] = {}
        auto_send_blocked_reasons: dict[str, int] = {}

        for sc in scenarios:
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)
            integrity = _integrity_from_scenario(sc)
            gate = AutoSendReadinessGate.evaluate(
                response_goal=sc.get("response_goal", ""),
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
                integrity_result=integrity,
            )

            if compliance.passed:
                compliance_passed_count += 1
            if integrity.passed:
                integrity_passed_count += 1
            if gate.auto_send_allowed:
                auto_send_allowed_count += 1

            for v in compliance.violations:
                cat = _categorise_violation(v)
                violation_category_counts[cat] = violation_category_counts.get(cat, 0) + 1

            for b in gate.auto_send_blockers:
                b_lower = b.lower()
                if "compliance" in b_lower:
                    reason = "compliance_failure"
                elif "goal" in b_lower or "auto-send allowed set" in b_lower:
                    reason = "goal_not_auto_sendable"
                elif "date" in b_lower or "resolved" in b_lower:
                    reason = "date_status"
                elif "escalate" in b_lower or "human" in b_lower:
                    reason = "escalation"
                elif "integrity" in b_lower:
                    reason = "integrity_failure"
                else:
                    reason = "other"
                auto_send_blocked_reasons[reason] = auto_send_blocked_reasons.get(reason, 0) + 1

        compliance_rate = compliance_passed_count / total * 100
        integrity_rate = integrity_passed_count / total * 100
        auto_send_rate = auto_send_allowed_count / total * 100

        print(f"\n{'=' * 68}")
        print("FIRST RESPONSE SAFETY REGRESSION SUMMARY — TEST-011")
        print(f"{'=' * 68}")
        print(f"Fixture:               {_FIXTURE_PATH.name}  |  Scenarios: {total}")
        print(f"{'─' * 68}")
        print(f"Compliance pass rate:  {compliance_rate:.1f}%  ({compliance_passed_count}/{total})")
        print(f"Integrity pass rate:   {integrity_rate:.1f}%  ({integrity_passed_count}/{total})")
        print(f"Auto-send rate:        {auto_send_rate:.1f}%  ({auto_send_allowed_count}/{total})")

        if violation_category_counts:
            print(f"\nCompliance violation breakdown:")
            for cat, count in sorted(violation_category_counts.items(), key=lambda x: -x[1]):
                bar = "\u2588" * count
                print(f"  {cat:<30}  {count:2d}  {bar}")

        if auto_send_blocked_reasons:
            print(f"\nAuto-send block reason breakdown:")
            for reason, count in sorted(auto_send_blocked_reasons.items(), key=lambda x: -x[1]):
                bar = "\u2588" * count
                print(f"  {reason:<30}  {count:2d}  {bar}")

        print(f"{'=' * 68}")

        # Structural assertions — ensure expected rates are in reasonable range
        assert compliance_rate >= 40.0, f"Compliance pass rate {compliance_rate:.1f}% below 40% floor"
        assert integrity_rate >= 95.0, f"Integrity pass rate {integrity_rate:.1f}% unexpectedly low"
        assert auto_send_rate >= 10.0, f"Auto-send rate {auto_send_rate:.1f}% unexpectedly low"
        assert auto_send_rate <= 50.0, f"Auto-send rate {auto_send_rate:.1f}% unexpectedly high — gate may be too permissive"


# ── RESP-032: Generation path ──────────────────────────────────────────────────


class TestGenerationPath:
    """RESP-032: production-equivalent generation routing."""

    def test_all_scenarios_have_generation_path_field(self, scenarios: list[dict]) -> None:
        missing = [sc["id"] for sc in scenarios if "generation_path" not in sc]
        assert not missing, f"Scenarios missing generation_path: {missing}"

    def test_respond_unavailable_scenarios_are_deterministic(self, scenarios: list[dict]) -> None:
        unavailable = [sc for sc in scenarios if sc.get("response_goal") == "RESPOND_UNAVAILABLE"]
        assert len(unavailable) > 0, "No RESPOND_UNAVAILABLE scenarios in fixture"
        for sc in unavailable:
            assert sc["generation_path"] == "deterministic", (
                f"{sc['id']}: RESPOND_UNAVAILABLE must have generation_path='deterministic'"
            )

    def test_non_unavailable_scenarios_are_llm(self, scenarios: list[dict]) -> None:
        non_unavailable = [sc for sc in scenarios if sc.get("response_goal") != "RESPOND_UNAVAILABLE"]
        for sc in non_unavailable:
            assert sc["generation_path"] == "llm", (
                f"{sc['id']}: non-RESPOND_UNAVAILABLE must have generation_path='llm'"
            )

    def test_deterministic_unavailable_drafts_pass_compliance(self, scenarios: list[dict]) -> None:
        """RESP-032: deterministic unavailable drafts must always be compliant."""
        unavailable = [sc for sc in scenarios if sc.get("response_goal") == "RESPOND_UNAVAILABLE"]
        failures = []
        for sc in unavailable:
            draft_text = _get_production_draft_text(sc)
            ctx = _context_from_scenario(sc)
            result = DraftComplianceValidator.validate(draft_text, ctx)
            if not result.passed:
                failures.append(
                    f"{sc['id']}: deterministic draft failed compliance: "
                    + "; ".join(result.violations)
                )
        assert not failures, "Deterministic RESPOND_UNAVAILABLE drafts failed compliance:\n" + "\n".join(failures)

    def test_deterministic_unavailable_drafts_are_never_auto_sendable(self, scenarios: list[dict]) -> None:
        """RESPOND_UNAVAILABLE is not in the auto-send allowlist."""
        unavailable = [sc for sc in scenarios if sc.get("response_goal") == "RESPOND_UNAVAILABLE"]
        for sc in unavailable:
            draft_text = _get_production_draft_text(sc)
            ctx = _context_from_scenario(sc)
            compliance = DraftComplianceValidator.validate(draft_text, ctx)
            gate = AutoSendReadinessGate.evaluate(
                response_goal="RESPOND_UNAVAILABLE",
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
                integrity_result=_integrity_from_scenario(sc),
            )
            assert gate.auto_send_allowed is False, (
                f"{sc['id']}: RESPOND_UNAVAILABLE must never be auto-sendable"
            )

    def test_fixture_expected_compliance_matches_deterministic_routing(self, scenarios: list[dict]) -> None:
        """All fixture expected.compliance_passed values align with production routing."""
        mismatches = []
        for sc in scenarios:
            expected_pass = sc["expected"].get("compliance_passed")
            if expected_pass is None:
                continue
            draft_text = _get_production_draft_text(sc)
            ctx = _context_from_scenario(sc)
            result = DraftComplianceValidator.validate(draft_text, ctx)
            if result.passed != expected_pass:
                mismatches.append(
                    f"{sc['id']}: expected compliance_passed={expected_pass}, got {result.passed}"
                )
        assert not mismatches, "Fixture compliance expectations mismatch production:\n" + "\n".join(mismatches)
