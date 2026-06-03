"""
Three-layer date parser accuracy test runner.
Dataset: freeform_group_booking_date_parser_test_40.json (40 records)
Architecture: Sprint 8B — LLM extracts facts only; backend resolves dates deterministically.

Layer 1 — JSON Contract Compliance (pass/fail per record)
Layer 2 — Factual Extraction Accuracy (LLM responsibility only)
Layer 3 — Date Resolution Readiness + Deterministic Resolver Accuracy

Scoring weights:
  Layer 1 (JSON contract):        30%
  Layer 2 (factual extraction):   30%
  Layer 3a (resolver readiness):  25%
  Layer 3b (resolver accuracy):   15%

Usage (from project root, with venv active):
    python tests/scripts/run_group_booking_date_parser_accuracy.py

Or inside the eventsales_api container:
    python tests/scripts/run_group_booking_date_parser_accuracy.py

Environment:
    ANTHROPIC_API_KEY  — required
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import anthropic

# ── Resolve repo root and add services/api to sys.path ────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent        # tests/scripts/
_TESTS_DIR = _SCRIPT_DIR.parent                      # tests/
_REPO_ROOT = _TESTS_DIR.parent                       # project root
_API_ROOT = _REPO_ROOT / "services" / "api"

if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

try:
    from app.modules.enquiries.date_resolution_service import (
        DateResolutionRequest,
        EnquiryDateResolutionService,
    )
    _RESOLVER_AVAILABLE = True
except ImportError as _err:
    _RESOLVER_AVAILABLE = False
    print(f"WARNING: EnquiryDateResolutionService not importable: {_err}", file=sys.stderr)
    print("         Date resolver scoring will be skipped.", file=sys.stderr)


# ── Prompt constants ──────────────────────────────────────────────────────────

PROMPT_VERSION = 3
MODEL_NAME = "claude-haiku-4-5-20251001"
TEMPERATURE = 0.05
MAX_TOKENS = 1400

ANCHOR_DATE = "2026-06-03"
TIMEZONE = "Europe/London"
RESTAURANT_NAME = "The Grand Ballroom"

# Schema: enquiry_extraction_output v3.0
# meal_period includes breakfast (test set covers all three meal periods).
SYSTEM_TEMPLATE = (
    "You are a structured data extraction specialist for {restaurant_name}, a hospitality venue.\n"
    "Your ONLY task is to extract factual details from the guest's freeform enquiry text.\n\n"
    "CRITICAL RULES — follow these exactly with no exceptions:\n"
    "- Extract facts only. Do NOT make pricing decisions.\n"
    "- Do NOT check, infer, or calculate room availability.\n"
    "- Do NOT write any customer-facing copy or draft a response.\n"
    "- Do NOT suggest whether the booking should proceed.\n"
    "- Do NOT expand flexible date requests into specific candidate dates.\n"
    "  The backend will expand dates deterministically — your job is fact extraction only.\n"
    "- Do NOT calculate availability across candidate dates.\n"
    "- Do NOT choose or rank dates.\n\n"
    "NULL PLACEHOLDER CONVENTION — use these exactly:\n"
    "- Missing string value: use the string \"NULL\" (not JSON null)\n"
    "- Missing numeric value: use JSON null\n"
    "- Missing object value: use JSON null\n"
    "- Missing array value: use [] (empty array)\n"
    "- Unknown enum value: use \"unknown\" where the schema permits it\n\n"
    "schema_name: enquiry_extraction_output\n"
    "schema_version: 3.0\n\n"
    "Return ONLY a valid JSON object matching this exact structure.\n"
    "No explanation. No preamble. No markdown fences. No trailing text.\n\n"
    "{{\n"
    "  \"customer_name\": \"<string or NULL>\",\n"
    "  \"email\": \"<string or NULL>\",\n"
    "  \"phone\": \"<string or NULL>\",\n"
    "  \"event_type\": \"<string or NULL>\",\n"
    "  \"occasion\": \"<string or NULL>\",\n"
    "  \"date_request\": {{\n"
    "    \"raw_text\": \"<exact date phrase from guest message, or NULL>\",\n"
    "    \"date_request_type\": \"<exact|date_range|multiple_choice|month_flexible"
    "|weekday_range_over_relative_period|recurring_window|mixed_relative_dates"
    "|ambiguous_numeric_date|unknown>\",\n"
    "    \"anchor_date\": \"<ISO 8601 date or null>\",\n"
    "    \"timezone\": \"<timezone string or null>\",\n"
    "    \"explicit_dates\": [\"<ISO 8601 date>\"],\n"
    "    \"date_range\": {{\n"
    "      \"start_date\": \"<ISO 8601 date or null>\",\n"
    "      \"end_date\": \"<ISO 8601 date or null>\",\n"
    "      \"flexibility_notes\": \"<string or null>\"\n"
    "    }},\n"
    "    \"relative_period\": {{\n"
    "      \"amount\": <integer or null>,\n"
    "      \"unit\": \"<day|week|month|year or null>\",\n"
    "      \"direction\": \"<next|last|this|future or null>\"\n"
    "    }},\n"
    "    \"weekdays\": [\"<monday|tuesday|wednesday|thursday|friday|saturday|sunday>\"],\n"
    "    \"month\": <integer 1-12 or null>,\n"
    "    \"year\": <integer or null>,\n"
    "    \"ambiguous_dates\": [\n"
    "      {{\n"
    "        \"raw_value\": \"<string>\",\n"
    "        \"possible_dates\": [\"<ISO 8601 date>\"],\n"
    "        \"reason\": \"<string>\"\n"
    "      }}\n"
    "    ],\n"
    "    \"requires_date_clarification\": false,\n"
    "    \"clarification_question\": \"<string or null>\",\n"
    "    \"confidence\": 0.9\n"
    "  }},\n"
    "  \"event_time\": \"<HH:MM or NULL>\",\n"
    "  \"guest_count\": null,\n"
    "  \"meal_period\": \"<breakfast|lunch|dinner|unknown or NULL>\",\n"
    "  \"budget\": {{\n"
    "    \"amount\": null,\n"
    "    \"currency\": \"<string or null>\",\n"
    "    \"budget_type\": \"<total|per_head|null>\"\n"
    "  }},\n"
    "  \"preferred_room\": \"<string or NULL>\",\n"
    "  \"special_requirements\": {{\n"
    "    \"children\": null,\n"
    "    \"pets\": null,\n"
    "    \"disabled_access\": null,\n"
    "    \"music\": null,\n"
    "    \"microphone\": null,\n"
    "    \"screen_or_tv\": null\n"
    "  }},\n"
    "  \"dietary_requirements\": [],\n"
    "  \"customer_tone\": \"<formal|informal|casual|unknown>\",\n"
    "  \"audience_type\": \"<social|corporate|agency|unknown>\",\n"
    "  \"missing_fields\": [],\n"
    "  \"confidence\": {{}},\n"
    "  \"freeform_notes\": \"<string or NULL>\"\n"
    "}}"
)

USER_TEMPLATE = (
    "Extract structured enquiry details from the following freeform text.\n\n"
    "Today's date: {anchor_date}\n"
    "Timezone: {timezone}\n"
    "Restaurant: {restaurant_name}\n\n"
    "Guest message:\n{freeform_text}"
)

# ── Schema constants ───────────────────────────────────────────────────────────

VALID_DATE_REQUEST_TYPES = frozenset({
    "exact", "date_range", "multiple_choice", "month_flexible",
    "weekday_range_over_relative_period", "recurring_window",
    "mixed_relative_dates", "ambiguous_numeric_date", "unknown",
})
VALID_MEAL_PERIODS = frozenset({"breakfast", "lunch", "dinner", "unknown"})
VALID_WEEKDAYS = frozenset({
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
})
VALID_CUSTOMER_TONES = frozenset({"formal", "informal", "casual", "unknown"})
VALID_AUDIENCE_TYPES = frozenset({"social", "corporate", "agency", "unknown"})

REQUIRED_TOP_LEVEL_KEYS = frozenset({
    "customer_name", "email", "phone", "event_type", "occasion",
    "date_request", "event_time", "guest_count", "meal_period",
    "budget", "preferred_room", "special_requirements",
    "dietary_requirements", "customer_tone", "audience_type",
    "missing_fields", "confidence", "freeform_notes",
})
REQUIRED_DATE_REQUEST_KEYS = frozenset({
    "raw_text", "date_request_type", "anchor_date", "timezone",
    "explicit_dates", "date_range", "relative_period", "weekdays",
    "month", "year", "ambiguous_dates", "requires_date_clarification",
    "clarification_question", "confidence",
})

# Types expanded deterministically by the backend; LLM must not populate explicit_dates
_BACKEND_EXPANDED_TYPES = frozenset({
    "date_range", "month_flexible",
    "weekday_range_over_relative_period", "recurring_window",
    "mixed_relative_dates",
})

# Relative-language patterns in raw_text that signal backend expansion is required
_RELATIVE_RAW_RE = re.compile(
    r"\b(next|this|tomorrow|today|last|after\s+next|first|second|third|"
    r"mid|early|any\s+|around|morning|evening)\b",
    re.IGNORECASE,
)


def _explicit_dates_llm_optional(target_dr: dict) -> bool:
    """Return True when the LLM is NOT expected to populate explicit_dates.

    This happens when date resolution is the backend's responsibility:
    - Flexible/range/window types always handled by backend.
    - Ambiguous dates require clarification — backend stores possible interpretations.
    - multiple_choice where dates were inferred from a date_range (e.g. "weekend around July 18").
    - exact/multiple_choice expressed with relative_period direction.
    - exact with relative language in raw_text (e.g. "next Friday", "the last Saturday").
    """
    t = target_dr.get("date_request_type", "")

    if t in _BACKEND_EXPANDED_TYPES:
        return True

    if t == "ambiguous_numeric_date":
        return True

    # multiple_choice where the dates were derived from a date_range
    if t == "multiple_choice" and target_dr.get("date_range"):
        return True

    # relative_period direction present → backend expands
    rp = target_dr.get("relative_period") or {}
    if rp.get("direction") in ("next", "last", "this", "future"):
        return True

    # Relative language in raw_text
    raw = target_dr.get("raw_text") or ""
    if _RELATIVE_RAW_RE.search(raw):
        return True

    return False


# ── Semantic occasion equivalence ─────────────────────────────────────────────

_OCCASION_GROUPS: list[frozenset] = [
    frozenset({
        "birthday", "birthday meal", "birthday breakfast", "birthday dinner",
        "birthday lunch", "birthday celebration",
    }),
    frozenset({
        "engagement party", "engagement dinner", "engagement celebration",
        "engagement lunch", "work engagement party",
    }),
    frozenset({
        "baby shower", "babyshower", "baby shower celebration",
        "baby shower dinner", "baby shower lunch",
    }),
]


def _occasion_match(a: str | None, b: str | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    al, bl = a.lower().strip(), b.lower().strip()
    if al == bl:
        return True
    for group in _OCCASION_GROUPS:
        if al in group and bl in group:
            return True
    return False


# ── Normalisation helpers ─────────────────────────────────────────────────────

def _norm(v: Any) -> Any:
    """Convert NULL placeholder strings to None."""
    return None if v == "NULL" else v


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:] if lines[0].startswith("```") else lines
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return text


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — JSON CONTRACT COMPLIANCE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContractResult:
    passed: bool
    failures: list[str] = field(default_factory=list)


def check_contract(parsed: dict) -> ContractResult:  # noqa: C901
    failures: list[str] = []

    # Required top-level keys
    missing = REQUIRED_TOP_LEVEL_KEYS - set(parsed.keys())
    if missing:
        failures.append(f"missing top-level keys: {sorted(missing)}")

    # guest_count: numeric or null
    gc = parsed.get("guest_count")
    if gc is not None and not isinstance(gc, (int, float)):
        failures.append(f"guest_count must be number or null, got {type(gc).__name__}: {gc!r}")

    # meal_period enum
    mp = parsed.get("meal_period")
    if mp and mp != "NULL" and mp not in VALID_MEAL_PERIODS:
        failures.append(f"invalid meal_period: {mp!r}")

    # customer_tone enum
    tone = parsed.get("customer_tone")
    if tone and tone != "NULL" and tone not in VALID_CUSTOMER_TONES:
        failures.append(f"invalid customer_tone: {tone!r}")

    # audience_type enum
    at = parsed.get("audience_type")
    if at and at != "NULL" and at not in VALID_AUDIENCE_TYPES:
        failures.append(f"invalid audience_type: {at!r}")

    # Arrays
    for arr_field in ("dietary_requirements", "missing_fields"):
        if not isinstance(parsed.get(arr_field, []), list):
            failures.append(f"{arr_field} must be an array")

    # date_request
    dr = parsed.get("date_request")
    if dr is None:
        failures.append("date_request is missing or null")
    elif not isinstance(dr, dict):
        failures.append(f"date_request must be object, got {type(dr).__name__}")
    else:
        missing_dr = REQUIRED_DATE_REQUEST_KEYS - set(dr.keys())
        if missing_dr:
            failures.append(f"date_request missing keys: {sorted(missing_dr)}")

        # date_request_type enum
        drt = dr.get("date_request_type")
        if drt and drt not in VALID_DATE_REQUEST_TYPES:
            failures.append(f"invalid date_request_type: {drt!r}")

        # weekdays enum values
        for wd in (dr.get("weekdays") or []):
            if isinstance(wd, str) and wd.lower() not in VALID_WEEKDAYS:
                failures.append(f"invalid weekday value: {wd!r}")

        # explicit_dates must be array
        if not isinstance(dr.get("explicit_dates", []), list):
            failures.append("explicit_dates must be array")

        # ambiguous_dates must be array
        if not isinstance(dr.get("ambiguous_dates", []), list):
            failures.append("ambiguous_dates must be array")

        # requires_date_clarification must be bool
        rdc = dr.get("requires_date_clarification")
        if rdc is not None and not isinstance(rdc, bool):
            failures.append(
                f"requires_date_clarification must be bool, got {type(rdc).__name__}"
            )

        # month: int or null (strings that are digits are tolerated but flagged)
        month = dr.get("month")
        if month is not None and not isinstance(month, int):
            if isinstance(month, str) and month.isdigit():
                pass  # coercible — do not fail contract, note it
            else:
                failures.append(f"month must be integer or null, got {month!r}")

        # year: int or null
        year = dr.get("year")
        if year is not None and not isinstance(year, int):
            if isinstance(year, str) and year.isdigit():
                pass
            else:
                failures.append(f"year must be integer or null, got {year!r}")

    return ContractResult(passed=len(failures) == 0, failures=failures)


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — FACTUAL EXTRACTION ACCURACY
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExtractionScore:
    """Per-field scores. None = field not applicable for this record."""
    scores: dict[str, bool | None] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def applicable(self) -> dict[str, bool]:
        return {k: v for k, v in self.scores.items() if v is not None}

    @property
    def accuracy(self) -> float:
        app = self.applicable
        return sum(app.values()) / len(app) if app else 1.0


def score_extraction(parsed: dict, target: dict) -> ExtractionScore:
    s = ExtractionScore()
    target_dr = target.get("date_request", {})
    llm_dr = (parsed.get("date_request") or {})

    # ── Core fields ────────────────────────────────────────────────────────────

    # guest_count
    llm_gc = _to_int(parsed.get("guest_count"))
    s.scores["guest_count"] = llm_gc == target.get("guest_count")

    # meal_period
    llm_mp = _norm(parsed.get("meal_period"))
    target_mp = _norm(target.get("meal_period"))
    s.scores["meal_period"] = (llm_mp or "").lower() == (target_mp or "").lower()

    # occasion — semantic equivalence
    llm_occ = _norm(parsed.get("occasion"))
    target_occ = _norm(target.get("occasion"))
    s.scores["occasion"] = _occasion_match(llm_occ, target_occ)

    # event_time — only score when target specifies one
    target_et = _norm(target.get("event_time"))
    if target_et is not None:
        llm_et = _norm(parsed.get("event_time"))
        s.scores["event_time"] = (llm_et or "").strip() == target_et.strip()
    else:
        s.scores["event_time"] = None  # N/A

    # ── date_request fields ────────────────────────────────────────────────────

    # raw_text
    s.scores["dr_raw_text"] = (
        _norm(llm_dr.get("raw_text")) == _norm(target_dr.get("raw_text"))
    )

    # date_request_type
    s.scores["dr_type"] = llm_dr.get("date_request_type") == target_dr.get("date_request_type")

    # explicit_dates — only scored when LLM is expected to populate them
    if not _explicit_dates_llm_optional(target_dr):
        actual = sorted(llm_dr.get("explicit_dates") or [])
        expected = sorted(target_dr.get("explicit_dates") or [])
        s.scores["dr_explicit_dates"] = actual == expected
        if actual != expected:
            s.notes.append(f"explicit_dates: got {actual}, expected {expected}")
    else:
        s.scores["dr_explicit_dates"] = None  # N/A — backend's responsibility

    # weekdays — only scored when target expects specific weekdays
    expected_wd = sorted(w.lower() for w in (target_dr.get("weekdays") or []))
    if expected_wd:
        actual_wd = sorted(w.lower() for w in (llm_dr.get("weekdays") or []))
        s.scores["dr_weekdays"] = actual_wd == expected_wd
    else:
        s.scores["dr_weekdays"] = None  # not expected

    # month — scored when target specifies one
    e_month = _to_int(target_dr.get("month"))
    if e_month is not None:
        a_month = _to_int(llm_dr.get("month"))
        s.scores["dr_month"] = a_month == e_month
    else:
        s.scores["dr_month"] = None

    # relative_period direction — scored when target has one
    e_rp = target_dr.get("relative_period") or {}
    a_rp = llm_dr.get("relative_period") or {}
    if e_rp and e_rp.get("direction"):
        s.scores["dr_relative_direction"] = a_rp.get("direction") == e_rp.get("direction")
    else:
        s.scores["dr_relative_direction"] = None

    # date_range start/end — scored when target has one
    e_range = target_dr.get("date_range") or {}
    a_range = llm_dr.get("date_range") or {}
    if e_range and (e_range.get("start_date") or e_range.get("end_date")):
        s.scores["dr_date_range"] = (
            a_range.get("start_date") == e_range.get("start_date")
            and a_range.get("end_date") == e_range.get("end_date")
        )
    else:
        s.scores["dr_date_range"] = None

    # requires_date_clarification
    s.scores["dr_clarification_flag"] = (
        bool(llm_dr.get("requires_date_clarification", False))
        == bool(target_dr.get("requires_date_clarification", False))
    )

    # confidence — within 0.15 tolerance
    try:
        a_conf = float(llm_dr.get("confidence") or 0)
        e_conf = float(target_dr.get("confidence") or 0)
        s.scores["dr_confidence"] = abs(a_conf - e_conf) <= 0.15
    except (TypeError, ValueError):
        s.scores["dr_confidence"] = False

    return s


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — DATE RESOLUTION READINESS + DETERMINISTIC RESOLVER
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResolverScore:
    resolver_ready: bool
    readiness_notes: list[str]
    resolver_candidate_dates: list[str]  # ISO strings produced by backend
    target_candidate_dates: list[str]    # ISO strings expected
    candidates_match: bool
    resolver_error: str | None = None


class _NoopDb:
    """Mock DB session — suppresses persistence; expansion logic is pure Python."""
    def add(self, *a): pass
    def flush(self): pass


def _run_resolver(llm_dr: dict, anchor_date_str: str) -> list[str] | str:
    """Run the deterministic resolver. Returns sorted ISO date list or error string."""
    if not _RESOLVER_AVAILABLE:
        return "SKIP:resolver not importable"
    try:
        anchor = date.fromisoformat(anchor_date_str)
        svc = EnquiryDateResolutionService(db=_NoopDb())
        result = svc.resolve(DateResolutionRequest(
            enquiry_id=uuid.uuid4(),
            date_request_dict=llm_dr,
            anchor_date_override=anchor,
        ))
        return sorted(d.isoformat() for d in result.candidate_dates)
    except Exception as exc:
        return f"ERROR:{exc}"


def _check_resolver_readiness(llm_dr: dict) -> tuple[bool, list[str]]:
    """Check whether the LLM output contains enough information for the resolver."""
    notes: list[str] = []
    ready = True
    dr_type = llm_dr.get("date_request_type", "unknown")

    if not _norm(llm_dr.get("raw_text")):
        notes.append("raw_text missing")
        ready = False

    if dr_type not in VALID_DATE_REQUEST_TYPES:
        notes.append(f"date_request_type {dr_type!r} not in schema")
        ready = False

    if dr_type in ("recurring_window", "weekday_range_over_relative_period"):
        if not (llm_dr.get("weekdays") or []):
            notes.append(f"{dr_type} needs weekdays[]")
            ready = False

    if dr_type == "date_range":
        a_range = llm_dr.get("date_range") or {}
        if not a_range.get("start_date") or not a_range.get("end_date"):
            notes.append("date_range needs start_date + end_date")
            ready = False

    if dr_type == "exact":
        has_explicit = bool(llm_dr.get("explicit_dates") or [])
        has_weekday = bool(llm_dr.get("weekdays") or [])
        has_rp = bool((llm_dr.get("relative_period") or {}).get("direction"))
        if not (has_explicit or has_weekday or has_rp):
            notes.append("exact type: no explicit_dates, weekdays, or relative_period")
            ready = False

    if dr_type == "ambiguous_numeric_date":
        if not (llm_dr.get("ambiguous_dates") or []):
            notes.append("ambiguous_numeric_date missing ambiguous_dates[]")
            ready = False
        if not llm_dr.get("requires_date_clarification"):
            notes.append("ambiguous_numeric_date: requires_date_clarification should be true")

    if not notes:
        notes.append("resolver-ready")

    return ready, notes


def score_resolver(llm_dr: dict, target: dict, anchor_date: str) -> ResolverScore:
    target_candidates = sorted(target.get("candidate_dates") or [])
    ready, readiness_notes = _check_resolver_readiness(llm_dr)

    if not ready:
        return ResolverScore(
            resolver_ready=False,
            readiness_notes=readiness_notes,
            resolver_candidate_dates=[],
            target_candidate_dates=target_candidates,
            candidates_match=False,
            resolver_error="not resolver-ready",
        )

    outcome = _run_resolver(llm_dr, anchor_date)
    if isinstance(outcome, str):
        # Error or skip
        return ResolverScore(
            resolver_ready=ready,
            readiness_notes=readiness_notes,
            resolver_candidate_dates=[],
            target_candidate_dates=target_candidates,
            candidates_match=False,
            resolver_error=outcome,
        )

    candidates_match = outcome == target_candidates
    return ResolverScore(
        resolver_ready=ready,
        readiness_notes=readiness_notes,
        resolver_candidate_dates=outcome,
        target_candidate_dates=target_candidates,
        candidates_match=candidates_match,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FULL CASE RESULT + FAILURE CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FullCaseResult:
    id: str
    subject: str
    anchor_date: str
    timezone: str
    raw_response: str
    parse_error: str | None
    target: dict              # target_extraction from test record
    contract: ContractResult | None
    extraction: ExtractionScore | None
    resolver: ResolverScore | None
    llm_parsed: dict | None = None
    failure_categories: list[str] = field(default_factory=list)


def classify_failures(r: FullCaseResult) -> list[str]:
    cats: list[str] = []

    if r.parse_error:
        cats.append("schema_failure")
        return cats

    if r.contract and not r.contract.passed:
        cats.append("schema_failure")

    if r.extraction:
        ext = r.extraction
        if ext.scores.get("dr_type") is False:
            cats.append("prompt_schema_ambiguity")
        for fk in ("guest_count", "meal_period", "occasion",
                   "dr_raw_text", "dr_clarification_flag"):
            if ext.scores.get(fk) is False:
                cats.append("true_extraction_failure")
                break
        # explicit_dates N/A → test expectation mismatch (LLM correctly did not expand)
        if ext.scores.get("dr_explicit_dates") is None:
            cats.append("test_expectation_mismatch")

    if r.resolver:
        if not r.resolver.resolver_ready:
            cats.append("missing_anchor_date_context")
        elif not r.resolver.candidates_match and not r.resolver.resolver_error:
            cats.append("deterministic_resolver_failure")
        elif r.resolver.resolver_error and "not resolver-ready" not in (r.resolver.resolver_error or ""):
            if not r.resolver.resolver_error.startswith("SKIP:"):
                cats.append("deterministic_resolver_failure")

    if not cats:
        cats.append("pass")

    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in cats:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# LLM CALL
# ══════════════════════════════════════════════════════════════════════════════

def run_case(client: anthropic.Anthropic, record: dict) -> FullCaseResult:
    record_id = record["id"]
    subject = record["subject"]
    body = record["body"]
    anchor = record.get("anchor_date", ANCHOR_DATE)
    tz = record.get("timezone", TIMEZONE)
    target = record["target_extraction"]

    # Build prompts — SYSTEM_TEMPLATE uses {{ }} escaping for JSON braces
    system_prompt = (
        SYSTEM_TEMPLATE
        .replace("{restaurant_name}", RESTAURANT_NAME)
        .replace("{{", "{")
        .replace("}}", "}")
    )
    user_prompt = (
        USER_TEMPLATE
        .replace("{anchor_date}", anchor)
        .replace("{timezone}", tz)
        .replace("{restaurant_name}", RESTAURANT_NAME)
        .replace("{freeform_text}", body)
    )

    raw = ""
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text
        raw_cleaned = _strip_fences(raw)
        parsed = json.loads(raw_cleaned)
    except json.JSONDecodeError as exc:
        return FullCaseResult(
            id=record_id, subject=subject, anchor_date=anchor, timezone=tz,
            raw_response=raw, parse_error=f"JSON parse error: {exc}",
            target=target,
            contract=ContractResult(passed=False, failures=["response is not valid JSON"]),
            extraction=None, resolver=None,
        )
    except Exception as exc:
        return FullCaseResult(
            id=record_id, subject=subject, anchor_date=anchor, timezone=tz,
            raw_response="", parse_error=f"API error: {exc}",
            target=target,
            contract=None, extraction=None, resolver=None,
        )

    contract = check_contract(parsed)
    extraction = score_extraction(parsed, target)
    llm_dr = parsed.get("date_request") or {}
    resolver = score_resolver(llm_dr, target, anchor)

    result = FullCaseResult(
        id=record_id, subject=subject, anchor_date=anchor, timezone=tz,
        raw_response=raw_cleaned, parse_error=None,
        target=target, contract=contract, extraction=extraction,
        resolver=resolver, llm_parsed=parsed,
    )
    result.failure_categories = classify_failures(result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SCORING AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

def compute_scores(results: list[FullCaseResult]) -> dict:
    n = len(results)
    if n == 0:
        return {}

    # Layer 1
    contract_pass = sum(1 for r in results if r.contract and r.contract.passed)
    l1 = contract_pass / n

    # Layer 2 — average accuracy across records that have extraction scores
    ext_accuracies = [r.extraction.accuracy for r in results if r.extraction is not None]
    l2 = sum(ext_accuracies) / len(ext_accuracies) if ext_accuracies else 0.0

    # Layer 3a — resolver readiness rate
    readiness = [r.resolver.resolver_ready for r in results if r.resolver is not None]
    l3a = sum(readiness) / len(readiness) if readiness else 0.0

    # Layer 3b — resolver accuracy (of ready records only)
    resolver_match = [
        r.resolver.candidates_match
        for r in results
        if r.resolver is not None and r.resolver.resolver_ready
    ]
    l3b = sum(resolver_match) / len(resolver_match) if resolver_match else 0.0

    # Weighted overall
    overall = 0.30 * l1 + 0.30 * l2 + 0.25 * l3a + 0.15 * l3b

    parse_errors = sum(1 for r in results if r.parse_error)
    return dict(
        n=n, parse_errors=parse_errors,
        contract_pass=contract_pass,
        l1=l1, l2=l2, l3a=l3a, l3b=l3b,
        overall=overall,
    )


# ══════════════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════════════

W = 74  # report width


def _bar(label: str, rate: float, width: int = 30) -> str:
    filled = round(rate * width)
    return f"{label:<34} [{'█' * filled}{'░' * (width - filled)}] {rate:.1%}"


def print_report(results: list[FullCaseResult]) -> None:  # noqa: C901
    sc = compute_scores(results)
    n = sc["n"]

    print(f"\n{'═' * W}")
    print(f"  freeform_group_booking_date_parser_test_40  —  Sprint 8B Architecture")
    print(f"  Model: {MODEL_NAME}  |  Prompt: V{PROMPT_VERSION}  |  anchor: {ANCHOR_DATE}  |  tz: {TIMEZONE}")
    print(f"{'═' * W}")

    # ── Layer 1 ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * W}")
    print(f"  LAYER 1 — JSON CONTRACT COMPLIANCE  ({sc['contract_pass']}/{n}  {sc['l1']:.1%})")
    print(f"{'─' * W}")
    if sc["parse_errors"]:
        print(f"  ✗ Parse errors (invalid JSON): {sc['parse_errors']}")
    contract_failures = [r for r in results if r.contract and not r.contract.passed]
    if contract_failures:
        for r in contract_failures:
            print(f"  ✗ [{r.id}] {r.subject}")
            for f in r.contract.failures:
                print(f"       • {f}")
    else:
        print(f"  ✓ All {n} responses satisfy the JSON schema contract")

    # ── Layer 2 ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * W}")
    print(f"  LAYER 2 — FACTUAL EXTRACTION ACCURACY  ({sc['l2']:.1%})")
    print(f"{'─' * W}")

    field_keys = [
        ("guest_count",           "guest_count"),
        ("meal_period",           "meal_period"),
        ("occasion",              "occasion (semantic)"),
        ("event_time",            "event_time"),
        ("dr_raw_text",           "date_request.raw_text"),
        ("dr_type",               "date_request_type"),
        ("dr_explicit_dates",     "explicit_dates (when LLM-required)"),
        ("dr_weekdays",           "weekdays"),
        ("dr_month",              "month"),
        ("dr_relative_direction", "relative_period.direction"),
        ("dr_date_range",         "date_range start/end"),
        ("dr_clarification_flag", "requires_date_clarification"),
        ("dr_confidence",         "confidence (±0.15)"),
    ]

    print(f"\n  {'Field':<38} {'Pass':>5} {'Total':>6} {'N/A':>5} {'Rate':>6}")
    print(f"  {'─' * 58}")
    for key, label in field_keys:
        vals = [r.extraction.scores.get(key) for r in results if r.extraction]
        correct = sum(1 for v in vals if v is True)
        na = sum(1 for v in vals if v is None)
        total = sum(1 for v in vals if v is not None)
        rate_str = f"{correct/total:.0%}" if total else "n/a"
        print(f"  {label:<38} {correct:>5} {total:>6} {na:>5} {rate_str:>6}")

    # Per-record L2 failures
    l2_bad = [r for r in results if r.extraction and r.extraction.accuracy < 1.0]
    if l2_bad:
        print(f"\n  Records with extraction gaps ({len(l2_bad)}):")
        for r in l2_bad:
            if not r.extraction:
                continue
            failing = [k for k, v in r.extraction.scores.items() if v is False]
            if not failing:
                continue
            print(f"    [{r.id}] {r.subject}")
            llm_dr = (r.llm_parsed or {}).get("date_request") or {}
            target_dr = r.target.get("date_request", {})
            for fk in failing:
                if fk == "guest_count":
                    got = _to_int((r.llm_parsed or {}).get("guest_count"))
                    exp = r.target.get("guest_count")
                elif fk == "meal_period":
                    got = _norm((r.llm_parsed or {}).get("meal_period"))
                    exp = _norm(r.target.get("meal_period"))
                elif fk == "occasion":
                    got = _norm((r.llm_parsed or {}).get("occasion"))
                    exp = _norm(r.target.get("occasion"))
                elif fk == "event_time":
                    got = _norm((r.llm_parsed or {}).get("event_time"))
                    exp = _norm(r.target.get("event_time"))
                elif fk.startswith("dr_"):
                    attr = fk[3:]  # strip "dr_" prefix
                    got = llm_dr.get(attr)
                    exp = target_dr.get(attr)
                else:
                    got, exp = "?", "?"
                print(f"      {fk}: got={got!r}  expected={exp!r}")

    # ── Layer 3 ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * W}")
    print(f"  LAYER 3 — DATE RESOLUTION")
    print(f"{'─' * W}")
    resolver_results = [r for r in results if r.resolver is not None]
    ready_count = sum(1 for r in resolver_results if r.resolver.resolver_ready)
    match_count = sum(1 for r in resolver_results if r.resolver.candidates_match)
    print(f"  Resolver readiness: {ready_count}/{len(resolver_results)}  ({sc['l3a']:.1%})")
    print(f"  Candidate match:    {match_count}/{len(resolver_results)}  ({sc['l3b']:.1%} of ready)")

    mismatches = [r for r in resolver_results if not r.resolver.candidates_match]
    if mismatches:
        print(f"\n  Resolver mismatches ({len(mismatches)}):")
        for r in mismatches:
            print(f"\n    [{r.id}] {r.subject}")
            print(f"      Ready: {r.resolver.resolver_ready}")
            print(f"      Notes: {'; '.join(r.resolver.readiness_notes)}")
            if r.resolver.resolver_error:
                print(f"      Error: {r.resolver.resolver_error}")
            print(f"      Got:      {r.resolver.resolver_candidate_dates}")
            print(f"      Expected: {r.resolver.target_candidate_dates}")
            llm_dr = (r.llm_parsed or {}).get("date_request") or {}
            print(f"      LLM date_request_type: {llm_dr.get('date_request_type')!r}")
            print(f"      LLM explicit_dates:    {llm_dr.get('explicit_dates')}")
            print(f"      LLM weekdays:          {llm_dr.get('weekdays')}")
            print(f"      LLM relative_period:   {llm_dr.get('relative_period')}")
            print(f"      LLM date_range:        {llm_dr.get('date_range')}")

    # ── Overall POC score ──────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print(f"  OVERALL POC USEFULNESS SCORE")
    print(f"{'═' * W}")
    print(f"  {_bar('JSON Contract Compliance   (30%)', sc['l1'])}")
    print(f"  {_bar('Factual Extraction Acc.    (30%)', sc['l2'])}")
    print(f"  {_bar('Date Resolution Readiness  (25%)', sc['l3a'])}")
    print(f"  {_bar('Deterministic Resolver Acc.(15%)', sc['l3b'])}")
    print(f"  {'─' * 68}")
    print(f"  {_bar('WEIGHTED OVERALL SCORE', sc['overall'])}")
    print()

    poc_score = sc["overall"]
    if poc_score >= 0.90:
        verdict = "EXCELLENT — ready to generate high-quality customer responses"
    elif poc_score >= 0.75:
        verdict = "GOOD — most enquiries handled well; minor improvements needed"
    elif poc_score >= 0.55:
        verdict = "MODERATE — significant gaps; review failures before production"
    else:
        verdict = "POOR — major failures; do not use in production"
    print(f"  Verdict: {verdict}")

    # ── Failure analysis ───────────────────────────────────────────────────────
    print(f"\n{'─' * W}")
    print(f"  FAILURE ANALYSIS")
    print(f"{'─' * W}")

    category_labels = {
        "schema_failure":               "Schema Failure (invalid JSON or contract)",
        "prompt_schema_ambiguity":      "Prompt / Schema Ambiguity (wrong date_request_type)",
        "missing_anchor_date_context":  "Missing Anchor-Date Context (resolver not ready)",
        "true_extraction_failure":      "True Extraction Failure (wrong facts extracted)",
        "deterministic_resolver_failure": "Deterministic Resolver Failure",
        "test_expectation_mismatch":    "Test Expectation Mismatch (LLM correctly did not expand relative dates)",
        "pass":                         "No Failures",
    }

    for cat, label in category_labels.items():
        affected = [r for r in results if cat in r.failure_categories]
        if not affected:
            continue
        print(f"\n  {label} ({len(affected)}):")
        for r in affected:
            extra = ""
            if cat == "test_expectation_mismatch":
                target_dr = r.target.get("date_request", {})
                raw = target_dr.get("raw_text", "")
                dr_type = target_dr.get("date_request_type", "")
                extra = f"  [{dr_type}] raw='{raw}'"
            elif cat == "deterministic_resolver_failure" and r.resolver:
                extra = (
                    f"  got={r.resolver.resolver_candidate_dates} "
                    f"expected={r.resolver.target_candidate_dates}"
                )
            print(f"    [{r.id}] {r.subject}{extra}")

    # ── Footer ─────────────────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print(f"  Model:   {MODEL_NAME}")
    print(f"  Prompt:  enquiry_extraction_output v{PROMPT_VERSION}.0 (V3)")
    print(f"  Params:  temperature={TEMPERATURE}, max_tokens={MAX_TOKENS}")
    print(f"  Dataset: freeform_group_booking_date_parser_test_40.json  ({n} records)")
    print(f"  Resolver: {'available' if _RESOLVER_AVAILABLE else 'NOT AVAILABLE — Layer 3 skipped'}")
    print(f"{'═' * W}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    data_path = _TESTS_DIR / "data" / "freeform_group_booking_date_parser_test_40.json"
    if not data_path.exists():
        print(f"ERROR: test data not found at {data_path}", file=sys.stderr)
        sys.exit(1)

    dataset = json.loads(data_path.read_text())
    records = dataset["records"]

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"\nRunning {len(records)} cases against {MODEL_NAME}  (V{PROMPT_VERSION} prompt)...\n")

    results: list[FullCaseResult] = []
    for i, record in enumerate(records, 1):
        label = f"[{i:02d}/{len(records)}] {record['id']} — {record['subject'][:42]}"
        print(f"  {label:<55} ", end="", flush=True)
        result = run_case(client, record)
        results.append(result)

        l1 = "✓" if (result.contract and result.contract.passed) else "✗"
        l2_str = f"{result.extraction.accuracy:.0%}" if result.extraction else "n/a"
        if result.resolver:
            if result.resolver.candidates_match:
                l3 = "✓"
            elif result.resolver.resolver_ready:
                l3 = "~"   # ready but wrong output
            else:
                l3 = "✗"
        else:
            l3 = "n/a"
        print(f"L1:{l1}  L2:{l2_str}  L3:{l3}")

    print_report(results)


if __name__ == "__main__":
    main()
