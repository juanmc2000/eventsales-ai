"""Response Context Integrity Gate (RESP-021).

Validates that the availability and room context used in the draft prompt matches
the restaurant and room context for the enquiry.  Prevents draft generation when
cross-restaurant or cross-room data contamination is detected.

All checks are deterministic — no LLM calls are made.

Rules:
  1. If both restaurant IDs are set, they must match.
  2. If restaurant IDs are unavailable, restaurant names must match (case-insensitive).
  3. If both room IDs are set, they must match.
  4. If room IDs are unavailable but both room names are set, names must match.

A failed check sets requires_review=True and should block LLM2 draft generation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


# ── Result ─────────────────────────────────────────────────────────────────────


@dataclass
class IntegrityCheckResult:
    """Result of a ResponseContextIntegrityGate.check() call.

    Attributes:
        passed:         True when no integrity violations were found.
        violations:     Human-readable descriptions of each violation.
        requires_review: True when the result should trigger manual review.
    """

    passed: bool
    violations: list[str] = field(default_factory=list)
    requires_review: bool = False

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "requires_review": self.requires_review,
        }


# ── Gate ───────────────────────────────────────────────────────────────────────


class ResponseContextIntegrityGate:
    """Validates that availability context matches restaurant/room context before LLM2.

    Usage::

        result = ResponseContextIntegrityGate.check(
            context_restaurant_name="The Ivy Tower Bridge",
            availability_restaurant_name="The Grand Ballroom",
        )
        if not result.passed:
            # block draft generation
            ...
    """

    @classmethod
    def check(
        cls,
        context_restaurant_name: str,
        context_room_name: str | None = None,
        availability_restaurant_name: str | None = None,
        availability_room_name: str | None = None,
        context_restaurant_id: uuid.UUID | None = None,
        availability_restaurant_id: uuid.UUID | None = None,
        context_room_id: uuid.UUID | None = None,
        availability_room_id: uuid.UUID | None = None,
    ) -> IntegrityCheckResult:
        """Run all integrity checks and return the combined result.

        Args:
            context_restaurant_name:  Restaurant name from the prompt context.
            context_room_name:        Room name from the prompt context (or None).
            availability_restaurant_name: Restaurant name from the availability record (or None).
            availability_room_name:   Room name from the availability record (or None).
            context_restaurant_id:    Restaurant UUID from the prompt context (or None).
            availability_restaurant_id: Restaurant UUID from the availability record (or None).
            context_room_id:          Room UUID from the prompt context (or None).
            availability_room_id:     Room UUID from the availability record (or None).

        Returns:
            IntegrityCheckResult with passed, violations, and requires_review.
        """
        violations: list[str] = []

        cls._check_restaurant(
            context_name=context_restaurant_name,
            availability_name=availability_restaurant_name,
            context_id=context_restaurant_id,
            availability_id=availability_restaurant_id,
            violations=violations,
        )

        cls._check_room(
            context_name=context_room_name,
            availability_name=availability_room_name,
            context_id=context_room_id,
            availability_id=availability_room_id,
            violations=violations,
        )

        passed = len(violations) == 0
        return IntegrityCheckResult(
            passed=passed,
            violations=violations,
            requires_review=not passed,
        )

    # ── Individual checks ─────────────────────────────────────────────────────

    @classmethod
    def _check_restaurant(
        cls,
        context_name: str,
        availability_name: str | None,
        context_id: uuid.UUID | None,
        availability_id: uuid.UUID | None,
        violations: list[str],
    ) -> None:
        """Fail if restaurant IDs or names differ between context and availability."""
        # ID comparison is authoritative when both IDs are present
        if context_id is not None and availability_id is not None:
            if str(context_id) != str(availability_id):
                violations.append(
                    f"Restaurant ID mismatch: prompt context references restaurant "
                    f"{context_id!r} but availability record references {availability_id!r}. "
                    "Draft generation blocked to prevent cross-restaurant contamination."
                )
            return  # ID check is definitive — skip name comparison

        # Fall back to name comparison when IDs are unavailable
        if availability_name is None:
            return  # Insufficient data to validate — pass

        if context_name.strip().lower() != availability_name.strip().lower():
            violations.append(
                f"Restaurant name mismatch: prompt context uses {context_name!r} "
                f"but availability record references {availability_name!r}. "
                "Draft generation blocked to prevent cross-restaurant contamination."
            )

    @classmethod
    def _check_room(
        cls,
        context_name: str | None,
        availability_name: str | None,
        context_id: uuid.UUID | None,
        availability_id: uuid.UUID | None,
        violations: list[str],
    ) -> None:
        """Fail if room IDs or names differ between context and availability."""
        # ID comparison is authoritative when both IDs are present
        if context_id is not None and availability_id is not None:
            if str(context_id) != str(availability_id):
                violations.append(
                    f"Room ID mismatch: prompt context references room {context_id!r} "
                    f"but availability record references room {availability_id!r}. "
                    "Draft generation blocked to prevent cross-room contamination."
                )
            return  # ID check is definitive — skip name comparison

        # Fall back to name comparison when IDs are unavailable
        if context_name is None or availability_name is None:
            return  # Insufficient data to validate — pass

        if context_name.strip().lower() != availability_name.strip().lower():
            violations.append(
                f"Room name mismatch: prompt context uses {context_name!r} "
                f"but availability record references {availability_name!r}. "
                "Draft generation blocked to prevent cross-room contamination."
            )
