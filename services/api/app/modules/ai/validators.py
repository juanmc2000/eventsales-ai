"""Structured output validation for AI Gateway responses.

Provides:
- Pydantic output schemas for known prompt types
- A validation helper that parses raw LLM responses and validates them
- A registry mapping schema names to Pydantic models
- Serializable error representation

Validation never raises — failures are captured and returned with a status
code so the gateway can log them and degrade gracefully.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Type

from pydantic import BaseModel, Field, field_validator

from app.modules.ai.constants import (
    SCHEMA_DRAFT_EMAIL_OUTPUT,
    SCHEMA_ENQUIRY_EXTRACTION_OUTPUT,
    VALIDATION_FALLBACK_INVALID,
    VALIDATION_FALLBACK_VALID,
    VALIDATION_FAILED,
    VALIDATION_PARSE_ERROR,
    VALIDATION_PASSED,
    VALIDATION_SKIPPED,
)

logger = logging.getLogger(__name__)


# ── Output schemas ────────────────────────────────────────────────────────────


class DraftEmailOutput(BaseModel):
    """Expected structured output for the draft_response prompt.

    The LLM should return a JSON object with subject and body.
    If the LLM returns plain text, the gateway wraps it with subject="" and
    body=<raw text> before validation, so validation_status becomes invalid.
    """

    subject: str = Field(min_length=0)
    body: str = Field(min_length=1)


class ExtractionBudget(BaseModel):
    """Budget details extracted from freeform enquiry text."""

    amount: float | None = None
    currency: str | None = None
    budget_type: str | None = None  # "total" | "per_head" | null


class ExtractionSpecialRequirements(BaseModel):
    """Special facility requirements extracted from freeform enquiry text."""

    children: bool | None = None
    pets: bool | None = None
    disabled_access: bool | None = None
    music: bool | None = None
    microphone: bool | None = None
    screen_or_tv: bool | None = None


class EnquiryExtractionOutput(BaseModel):
    """Expected structured output for the enquiry_extraction prompt (V2 — freeform).

    All fields are nullable.  Fields the model could not extract must be listed
    in missing_fields.  Confidence is a per-field decimal (0.0–1.0).
    """

    occasion: str | None = None
    guest_count: int | None = None
    event_date: str | None = None  # ISO 8601 date or null
    event_time: str | None = None  # HH:MM or null
    event_type: str | None = None
    budget: ExtractionBudget | None = None
    allergens: list[str] | None = None
    special_requirements: ExtractionSpecialRequirements | None = None
    freeform_notes: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("guest_count", mode="before")
    @classmethod
    def coerce_guest_count(cls, v: Any) -> int | None:
        """Accept numeric strings from the LLM (e.g. "10" → 10)."""
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None


# ── Schema registry ───────────────────────────────────────────────────────────

_SCHEMA_REGISTRY: dict[str, Type[BaseModel]] = {
    SCHEMA_DRAFT_EMAIL_OUTPUT: DraftEmailOutput,
    SCHEMA_ENQUIRY_EXTRACTION_OUTPUT: EnquiryExtractionOutput,
}


def get_schema(schema_name: str) -> Type[BaseModel] | None:
    """Return the Pydantic model class for the given schema name, or None."""
    return _SCHEMA_REGISTRY.get(schema_name)


# ── Validation result ─────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Outcome of validating a single LLM response.

    Always produced — even for parse errors or skipped runs.
    """

    status: str
    parsed: dict | None = field(default=None)
    errors: list[dict] | None = field(default=None)


# ── Validator ─────────────────────────────────────────────────────────────────


class OutputValidator:
    """Validates a raw LLM response against a declared output schema.

    Usage::

        validator = OutputValidator()
        result = validator.validate(
            raw_response="Dear Alice...",
            schema_name="DraftEmailOutput",
            is_fallback=False,
        )
        # result.status == "parse_error" if not JSON, "valid" if passes schema
    """

    def validate(
        self,
        raw_response: str | None,
        schema_name: str | None,
        is_fallback: bool = False,
    ) -> ValidationResult:
        """Validate raw_response against the named schema.

        Returns:
            ValidationResult with status, parsed dict, and errors.
        """
        # ── Fallback: no LLM response to validate ──────────────────────────
        if is_fallback or raw_response is None:
            return ValidationResult(status=VALIDATION_SKIPPED)

        # ── No schema declared: skip validation ───────────────────────────
        if not schema_name:
            return ValidationResult(status=VALIDATION_SKIPPED)

        schema_cls = get_schema(schema_name)
        if schema_cls is None:
            logger.warning("Unknown output schema: %s", schema_name)
            return ValidationResult(status=VALIDATION_SKIPPED)

        # ── Parse JSON ────────────────────────────────────────────────────
        try:
            parsed = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.debug("JSON parse failed for schema %s: %s", schema_name, exc)
            return ValidationResult(
                status=VALIDATION_PARSE_ERROR,
                errors=[{"type": "json_parse_error", "msg": str(exc)}],
            )

        if not isinstance(parsed, dict):
            return ValidationResult(
                status=VALIDATION_PARSE_ERROR,
                errors=[{"type": "json_parse_error", "msg": "Expected a JSON object"}],
            )

        # ── Validate with Pydantic ────────────────────────────────────────
        try:
            schema_cls.model_validate(parsed)
            status = VALIDATION_FALLBACK_VALID if is_fallback else VALIDATION_PASSED
            return ValidationResult(status=status, parsed=parsed)
        except Exception as exc:  # noqa: BLE001
            errors = _serialize_pydantic_error(exc)
            status = VALIDATION_FALLBACK_INVALID if is_fallback else VALIDATION_FAILED
            return ValidationResult(status=status, parsed=parsed, errors=errors)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _serialize_pydantic_error(exc: Exception) -> list[dict]:
    """Convert a Pydantic ValidationError to a serializable list of dicts."""
    try:
        # Pydantic v2 ValidationError
        return [
            {"type": e.get("type", "error"), "loc": list(e.get("loc", [])), "msg": e.get("msg", "")}
            for e in exc.errors()  # type: ignore[attr-defined]
        ]
    except AttributeError:
        return [{"type": "validation_error", "msg": str(exc)}]
