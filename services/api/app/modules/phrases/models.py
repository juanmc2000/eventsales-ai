"""Phrase Library models (DATA-020).

Database-backed phrase library for approved deterministic response blocks.
Supports tenant, restaurant, and persona overrides via a resolution hierarchy.

Tables:
  response_phrase_templates  — catalogue of known phrase keys and their goals
  response_phrase_versions   — versioned phrase text for each template
  response_phrase_assignments — tenant/restaurant/persona override assignments
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResponsePhraseTemplate(Base):
    """Catalogue entry for a known phrase key.

    A phrase key (e.g. ``availability_unavailable_no_alternatives``) maps to a
    response goal so consumers can look up the correct phrase without coupling
    to goal logic.
    """

    __tablename__ = "response_phrase_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default", index=True
    )
    phrase_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    response_goal: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    versions: Mapped[list["ResponsePhraseVersion"]] = relationship(
        "ResponsePhraseVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ResponsePhraseVersion.version",
    )


class ResponsePhraseVersion(Base):
    """Versioned phrase text for a phrase template.

    The active version (status='active') is the one used by PhraseResolutionService
    as the system default.  Previous versions are archived for audit purposes.
    """

    __tablename__ = "response_phrase_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("response_phrase_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # phrase_text may contain {variable} placeholders for runtime interpolation
    phrase_text: Mapped[str] = mapped_column(Text, nullable=False)
    # active | archived | draft
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    template: Mapped["ResponsePhraseTemplate"] = relationship(
        "ResponsePhraseTemplate", back_populates="versions"
    )


class ResponsePhraseAssignment(Base):
    """Tenant/restaurant/persona override for a phrase key.

    Resolution order evaluated by PhraseResolutionService:
      1. restaurant_id + persona_id (most specific)
      2. restaurant_id only
      3. tenant (no restaurant) + persona_id
      4. tenant only
      5. System default (ResponsePhraseVersion with status='active')
    """

    __tablename__ = "response_phrase_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default", index=True
    )
    restaurant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # audience_type: "social" | "corporate" | "agency" | None
    audience_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    phrase_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Override phrase text — may contain {variable} placeholders
    phrase_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
