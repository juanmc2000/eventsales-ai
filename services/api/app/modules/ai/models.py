"""SQLAlchemy models for AI prompt management and run tracing.

Tables:
  ai_prompt_templates     — logical prompt definitions (tenant-aware)
  ai_prompt_versions      — immutable versioned prompt snapshots
  tenant_prompt_configs   — per-tenant active version selection
  ai_prompt_runs          — full trace log of every LLM call
  ai_training_examples    — curated examples for future evaluation / fine-tuning
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    pass


class AIPromptTemplate(Base):
    """Logical prompt definition.  One template may have many versioned snapshots."""

    __tablename__ = "ai_prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable: None means system-wide default; set for tenant overrides
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # Stable identifier used by the gateway, e.g. "draft_response"
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # e.g. "draft_generation" / "intake_classification"
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_system_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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

    versions: Mapped[list["AIPromptVersion"]] = relationship(
        "AIPromptVersion", back_populates="template", cascade="all, delete-orphan"
    )


class AIPromptVersion(Base):
    """Immutable snapshot of a prompt at a given version number.

    Rows must never be updated after creation.  To change a prompt, insert a
    new version and deactivate the old one.
    """

    __tablename__ = "ai_prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prompt_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalised from template for fast querying without joins
    prompt_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    prompt_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Auto-incremented per template; assigned by the application on insert
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # "draft" | "active" | "archived"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # Jinja2 template strings
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional: logical name of the expected output schema, e.g. "DraftEmailOutput"
    output_schema_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    output_schema_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # e.g. "anthropic"
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g. "claude-sonnet-4-6"
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # LLM generation parameters (configured values for this version)
    temperature: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    top_p: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # User reference; nullable — system seed has no human author
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    template: Mapped["AIPromptTemplate"] = relationship(
        "AIPromptTemplate", back_populates="versions"
    )
    runs: Mapped[list["AIPromptRun"]] = relationship(
        "AIPromptRun", back_populates="prompt_version_rel"
    )


class TenantPromptConfig(Base):
    """Per-tenant (and optionally per-restaurant or per-persona) active version mapping."""

    __tablename__ = "tenant_prompt_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Logical key matching AIPromptTemplate.key
    prompt_key: Mapped[str] = mapped_column(String(100), nullable=False)
    active_prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Narrowing selectors — both nullable; None means "applies to all"
    restaurant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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

    active_prompt_version: Mapped["AIPromptVersion"] = relationship(
        "AIPromptVersion", foreign_keys=[active_prompt_version_id]
    )


class AIPromptRun(Base):
    """Full trace log of a single LLM call through the AI Gateway.

    Immutable after insert.  Every call — including fallback runs — is recorded.
    """

    __tablename__ = "ai_prompt_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Tenant-ready: nullable in POC, required in multi-tenant production
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    restaurant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )
    # e.g. "draft_generation" | "intake_classification"
    trigger_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g. "api" | "celery" | "webform"
    trigger_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    triggered_by_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Denormalised for fast querying without joins
    prompt_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    prompt_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Actual LLM runtime parameters used for this run
    temperature: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    top_p: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Exact strings sent to the LLM
    rendered_system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_user_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Full context variables passed to the renderer
    input_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # SHA-256 of rendered prompts; used for deduplication / caching in future
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Raw LLM output
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Parsed and validated structured output
    parsed_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # "passed" | "failed" | "skipped"
    validation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    validation_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fallback_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_input_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_output_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "success" | "fallback" | "error"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    prompt_version_rel: Mapped["AIPromptVersion | None"] = relationship(
        "AIPromptVersion", back_populates="runs", foreign_keys=[prompt_version_id]
    )
    training_example: Mapped["AITrainingExample | None"] = relationship(
        "AITrainingExample", back_populates="prompt_run", uselist=False
    )


class AIPromptExperiment(Base):
    """Groups a set of prompt run variants for comparison.

    An experiment targets a single prompt_key and compares different
    prompt versions or generation parameter settings.  Each variant
    run is recorded in ai_prompt_experiment_runs.
    """

    __tablename__ = "ai_prompt_experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # The prompt key being evaluated, e.g. "draft_response"
    prompt_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Optional reference to the version used as the control/baseline
    baseline_prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # "active" | "completed" | "archived"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    experiment_runs: Mapped[list["AIPromptExperimentRun"]] = relationship(
        "AIPromptExperimentRun", back_populates="experiment", cascade="all, delete-orphan"
    )


class AIPromptExperimentRun(Base):
    """A single variant run within a prompt experiment.

    Links an ai_prompt_run to an experiment and records which parameter
    variant was tested.  Does not duplicate the run's payload or response.
    """

    __tablename__ = "ai_prompt_experiment_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Human-readable label for this variant, e.g. "baseline", "temperature_0.3"
    variant_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Variant-specific LLM parameters (may differ from the run's actual values)
    temperature: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    top_p: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Manual quality evaluation (1–5); null until reviewed
    evaluator_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    selected_as_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    experiment: Mapped["AIPromptExperiment"] = relationship(
        "AIPromptExperiment", back_populates="experiment_runs"
    )


class AITrainingExample(Base):
    """Curated training / evaluation examples linked to prompt run traces.

    Rows are inserted automatically for every run.  Human review is required
    before approved_for_training is set to True.
    """

    __tablename__ = "ai_training_examples"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prompt_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    prompt_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    corrected_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 1–5 quality rating; null until reviewed
    quality_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_for_training: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    prompt_run: Mapped["AIPromptRun"] = relationship(
        "AIPromptRun", back_populates="training_example"
    )
