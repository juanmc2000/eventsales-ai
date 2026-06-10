"""Phrase Resolution Service (RESP-044).

Resolves the correct phrase for a response block using a five-level
override hierarchy.  The most specific match wins.

Resolution order (first match wins):
  1. restaurant + persona  (most specific override)
  2. restaurant default    (no persona restriction)
  3. tenant + persona      (persona preference across restaurant)
  4. tenant default        (tenant-wide default, no persona)
  5. system default        (active ResponsePhraseVersion in DB, or hard-coded fallback)

All checks are deterministic.  No LLM calls are made.

Usage::

    from app.modules.phrases.phrase_resolution_service import PhraseResolutionService

    result = PhraseResolutionService.resolve(
        db=db,
        phrase_key="availability_unavailable_no_alternatives",
        tenant_id="default",
        restaurant_id=restaurant_id,
        persona_id=persona_id,
    )
    # result.phrase_text   → "Unfortunately, we are fully booked..."
    # result.resolved_from → "system_default"
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.phrases.models import ResponsePhraseAssignment, ResponsePhraseVersion, ResponsePhraseTemplate

# Resolution level labels — used in resolved_from for traceability
LEVEL_RESTAURANT_PERSONA = "restaurant_persona"
LEVEL_RESTAURANT_DEFAULT = "restaurant_default"
LEVEL_TENANT_PERSONA = "tenant_persona"
LEVEL_TENANT_DEFAULT = "tenant_default"
LEVEL_SYSTEM_DEFAULT = "system_default"
LEVEL_NOT_FOUND = "not_found"


# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class PhraseResolutionResult:
    """Result of PhraseResolutionService.resolve().

    Attributes:
        phrase_key:     The requested phrase key.
        phrase_text:    The resolved phrase text (may contain {variable} placeholders).
        resolved_from:  One of the LEVEL_* constants indicating how the phrase was found.
        found:          False only when no phrase exists at any level (phrase_key unknown).
    """

    phrase_key: str
    phrase_text: str
    resolved_from: str
    found: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "phrase_key": self.phrase_key,
            "phrase_text": self.phrase_text,
            "resolved_from": self.resolved_from,
            "found": self.found,
        }


# ── Service ────────────────────────────────────────────────────────────────────


class PhraseResolutionService:
    """Resolves phrase text using the five-level override hierarchy.

    All checks query the database synchronously.  No LLM calls are made.
    """

    @classmethod
    def resolve(
        cls,
        db: Session,
        phrase_key: str,
        tenant_id: str = "default",
        restaurant_id: uuid.UUID | None = None,
        persona_id: uuid.UUID | None = None,
        audience_type: str | None = None,
    ) -> PhraseResolutionResult:
        """Resolve phrase_key to phrase text using the five-level hierarchy.

        Args:
            db:            SQLAlchemy session.
            phrase_key:    The logical phrase identifier (e.g. "availability_confirmed").
            tenant_id:     Tenant scope for the resolution.
            restaurant_id: Specific restaurant to check first.
            persona_id:    Specific persona to check first.
            audience_type: Optional audience type for additional filtering (informational).

        Returns:
            PhraseResolutionResult with resolved phrase text and level.
        """
        # ── Level 1: restaurant + persona ─────────────────────────────────────
        if restaurant_id and persona_id:
            text = cls._lookup_assignment(
                db, phrase_key, tenant_id,
                restaurant_id=restaurant_id, persona_id=persona_id,
            )
            if text is not None:
                return PhraseResolutionResult(
                    phrase_key=phrase_key,
                    phrase_text=text,
                    resolved_from=LEVEL_RESTAURANT_PERSONA,
                )

        # ── Level 2: restaurant default (no persona) ──────────────────────────
        if restaurant_id:
            text = cls._lookup_assignment(
                db, phrase_key, tenant_id,
                restaurant_id=restaurant_id, persona_id=None,
            )
            if text is not None:
                return PhraseResolutionResult(
                    phrase_key=phrase_key,
                    phrase_text=text,
                    resolved_from=LEVEL_RESTAURANT_DEFAULT,
                )

        # ── Level 3: tenant + persona ──────────────────────────────────────────
        if persona_id:
            text = cls._lookup_assignment(
                db, phrase_key, tenant_id,
                restaurant_id=None, persona_id=persona_id,
            )
            if text is not None:
                return PhraseResolutionResult(
                    phrase_key=phrase_key,
                    phrase_text=text,
                    resolved_from=LEVEL_TENANT_PERSONA,
                )

        # ── Level 4: tenant default ────────────────────────────────────────────
        text = cls._lookup_assignment(
            db, phrase_key, tenant_id,
            restaurant_id=None, persona_id=None,
        )
        if text is not None:
            return PhraseResolutionResult(
                phrase_key=phrase_key,
                phrase_text=text,
                resolved_from=LEVEL_TENANT_DEFAULT,
            )

        # ── Level 5: system default (active version in DB) ────────────────────
        text = cls._lookup_system_default(db, phrase_key)
        if text is not None:
            return PhraseResolutionResult(
                phrase_key=phrase_key,
                phrase_text=text,
                resolved_from=LEVEL_SYSTEM_DEFAULT,
            )

        # Phrase key is completely unknown
        return PhraseResolutionResult(
            phrase_key=phrase_key,
            phrase_text="",
            resolved_from=LEVEL_NOT_FOUND,
            found=False,
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _lookup_assignment(
        db: Session,
        phrase_key: str,
        tenant_id: str,
        restaurant_id: uuid.UUID | None,
        persona_id: uuid.UUID | None,
    ) -> str | None:
        """Query response_phrase_assignments for a matching active override."""
        stmt = (
            select(ResponsePhraseAssignment.phrase_text)
            .where(ResponsePhraseAssignment.phrase_key == phrase_key)
            .where(ResponsePhraseAssignment.tenant_id == tenant_id)
            .where(ResponsePhraseAssignment.is_active.is_(True))
        )
        if restaurant_id is not None:
            stmt = stmt.where(ResponsePhraseAssignment.restaurant_id == restaurant_id)
        else:
            stmt = stmt.where(ResponsePhraseAssignment.restaurant_id.is_(None))

        if persona_id is not None:
            stmt = stmt.where(ResponsePhraseAssignment.persona_id == persona_id)
        else:
            stmt = stmt.where(ResponsePhraseAssignment.persona_id.is_(None))

        return db.scalars(stmt).first()

    @staticmethod
    def _lookup_system_default(db: Session, phrase_key: str) -> str | None:
        """Return the active system-default phrase text for phrase_key."""
        stmt = (
            select(ResponsePhraseVersion.phrase_text)
            .join(
                ResponsePhraseTemplate,
                ResponsePhraseVersion.template_id == ResponsePhraseTemplate.id,
            )
            .where(ResponsePhraseTemplate.phrase_key == phrase_key)
            .where(ResponsePhraseTemplate.is_active.is_(True))
            .where(ResponsePhraseVersion.status == "active")
            .order_by(ResponsePhraseVersion.version.desc())
            .limit(1)
        )
        return db.scalars(stmt).first()
