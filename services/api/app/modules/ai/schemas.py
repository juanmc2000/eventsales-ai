"""Schemas for the AI draft generation module.

These schemas define the internal context object passed to the
draft generation service and the structured result returned to callers.

The raw prompts (system_prompt, user_message) are captured by the service
and included in AIContextOut for AI transparency reporting on the webform
response page. They are never stored in the database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel


@dataclass
class DraftContext:
    """All context needed to generate a persona-based draft response.

    Assembled from the enquiry, restaurant, persona, and pricing data.
    Never serialised or exposed via the API.
    """

    enquiry_id: uuid.UUID
    guest_first_name: str
    guest_last_name: str
    event_type: str | None
    event_date: str | None          # ISO date string, e.g. "2026-08-15"
    party_size: int | None
    guest_message: str | None       # Initial message body from the guest
    restaurant_name: str
    restaurant_description: str | None
    persona_name: str
    persona_tone: str               # e.g. "warm and formal"
    persona_style: str              # e.g. "concise"
    persona_system_prompt: str      # Base persona instruction
    recommended_minimum_spend: float | None
    # Restaurant venue context (added in AI-002)
    restaurant_address: str | None = field(default=None)
    # Room/PDR context — present when a suitable room has been matched
    room_name: str | None = field(default=None)
    room_type: str | None = field(default=None)
    room_seated_capacity: int | None = field(default=None)
    room_standing_capacity: int | None = field(default=None)
    room_layouts: list[str] | None = field(default=None)
    room_amenities: list[str] | None = field(default=None)
    room_suitability_notes: str | None = field(default=None)
    room_booking_url: str | None = field(default=None)
    room_is_private_dining: bool = field(default=False)
    # Sprint 7 enrichment — populated from processing snapshot when available (AI-011)
    # Deterministic availability from room_availability table
    availability_status: str | None = field(default=None)   # "available"|"booked"|"held"|"unavailable"|"unknown"
    availability_date: str | None = field(default=None)     # ISO date
    availability_meal_period: str | None = field(default=None)
    # Deterministic pricing from pricing rules
    confirmed_minimum_spend: float | None = field(default=None)
    pricing_explanation: str | None = field(default=None)
    # Missing fields to ask the guest about
    missing_questions: list[str] | None = field(default=None)
    # Recommended action from processing service
    recommended_action: str | None = field(default=None)


@dataclass
class AIContextOut:
    """AI transparency context returned with every draft response.

    Captures what data and prompts were used to generate the draft.
    system_prompt and user_message are None when the fallback provider was used
    (no LLM call was made).
    """

    model: str
    is_fallback: bool
    persona_name: str | None
    persona_tone: str | None
    persona_style: str | None
    guest_message_used: str | None
    room_name: str | None
    recommended_minimum_spend: float | None
    system_prompt: str | None       # Exact system prompt sent to Claude; None for fallback
    user_message: str | None        # Exact user message sent to Claude; None for fallback
    prompt_run_id: uuid.UUID | None = field(default=None)  # ai_prompt_runs.id for this call


@dataclass
class AIGatewayRequest:
    """Input to the AI Gateway for a single LLM call.

    input_payload contains the template variables to be rendered into the
    system and user prompt templates.  It must satisfy the required_variables
    of the selected PromptDefinition.
    """

    prompt_key: str
    input_payload: dict
    tenant_id: str | None = field(default=None)
    restaurant_id: uuid.UUID | None = field(default=None)
    persona_id: uuid.UUID | None = field(default=None)
    enquiry_id: uuid.UUID | None = field(default=None)
    trigger_type: str | None = field(default=None)
    trigger_source: str | None = field(default=None)
    triggered_by_user_id: str | None = field(default=None)
    # Optional: output schema class used for structured validation (AI-005)
    output_schema: type | None = field(default=None)


@dataclass
class AIGatewayResult:
    """Typed result returned by the AI Gateway after executing a prompt run.

    Every run — including fallback runs — produces a result.
    raw_response is None for fallback runs.
    """

    run_id: uuid.UUID
    prompt_key: str
    prompt_version: int
    model_name: str
    model_provider: str
    rendered_system_prompt: str | None
    rendered_user_prompt: str | None
    raw_response: str | None
    is_fallback: bool
    fallback_reason: str | None
    validation_status: str
    latency_ms: int
    status: str
    parsed_response: dict | None = field(default=None)
    validation_errors: list | None = field(default=None)
    error_message: str | None = field(default=None)


@dataclass
class DraftGenerationResult:
    """Structured output of the draft generation service.

    Returned to the caller (API-013 endpoint) for further handling.
    """

    enquiry_id: uuid.UUID
    message_id: uuid.UUID           # ID of the stored EnquiryMessage
    subject: str                    # Suggested email subject line
    body: str                       # Draft response body
    persona_name: str
    is_fallback: bool               # True when generated without an LLM call
    model: str                      # Model name or "fallback"
    ai_context: AIContextOut | None = field(default=None)


# ── API response schemas (Pydantic) ───────────────────────────────────────────


class PromptRunOut(BaseModel):
    """Summary of a single ai_prompt_run row, safe for list responses."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    prompt_key: str | None
    prompt_name: str | None
    prompt_goal: str | None
    prompt_version: int | None
    trigger_type: str | None
    restaurant_id: uuid.UUID | None
    enquiry_id: uuid.UUID | None
    persona_id: uuid.UUID | None
    model_provider: str | None
    model_name: str | None
    temperature: float | None
    top_p: float | None
    top_k: int | None
    max_tokens: int | None
    validation_status: str | None
    fallback_used: bool
    fallback_reason: str | None
    status: str
    latency_ms: int | None
    token_input_count: int | None
    token_output_count: int | None
    estimated_cost: str | None
    created_at: datetime


class PromptRunDetailOut(PromptRunOut):
    """Full detail of a prompt run, including rendered prompts and raw response.

    Intended for backend/admin debugging only — not for the frontend.
    """

    rendered_system_prompt: str | None
    rendered_user_prompt: str | None
    raw_response: str | None
    parsed_response: dict[str, Any] | None
    validation_errors: list[dict[str, Any]] | None
    input_hash: str | None
    error_message: str | None


class PromptRunListOut(BaseModel):
    """Paginated list of prompt run summaries."""

    items: list[PromptRunOut]
    total: int
    skip: int
    limit: int


# ── Training example schemas ──────────────────────────────────────────────────


class TrainingExampleCreate(BaseModel):
    """Request body for creating a training example."""

    prompt_run_id: uuid.UUID
    corrected_output: dict[str, Any] | None = None
    correction_reason: str | None = None
    quality_rating: int | None = None  # 1–5
    approved_for_training: bool = False
    reviewed_by_user_id: str | None = None


class TrainingExampleOut(BaseModel):
    """Response body for a training example."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    prompt_run_id: uuid.UUID
    tenant_id: str | None
    prompt_key: str | None
    original_output: dict[str, Any] | None
    corrected_output: dict[str, Any] | None
    correction_reason: str | None
    reviewed_by_user_id: str | None
    quality_rating: int | None
    approved_for_training: bool
    created_at: datetime


class TrainingExampleListOut(BaseModel):
    """Paginated list of training examples."""

    items: list[TrainingExampleOut]
    total: int
    skip: int
    limit: int


# ── Prompt experiment schemas ──────────────────────────────────────────────────


class PromptExperimentCreate(BaseModel):
    """Request body for creating a prompt experiment."""

    prompt_key: str
    name: str
    goal: str | None = None
    baseline_prompt_version_id: uuid.UUID | None = None
    notes: str | None = None
    tenant_id: str | None = None


class PromptExperimentOut(BaseModel):
    """Summary of a single ai_prompt_experiment row."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: str | None
    prompt_key: str
    name: str
    goal: str | None
    baseline_prompt_version_id: uuid.UUID | None
    status: str
    notes: str | None
    created_at: datetime


class PromptExperimentRunCreate(BaseModel):
    """Request body for adding a run to an experiment."""

    prompt_run_id: uuid.UUID
    variant_name: str
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_tokens: int | None = None
    evaluator_score: int | None = None  # 1–5
    reviewer_notes: str | None = None
    selected_as_winner: bool = False


class PromptExperimentRunOut(BaseModel):
    """Summary of a single ai_prompt_experiment_run row."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    experiment_id: uuid.UUID
    prompt_run_id: uuid.UUID
    variant_name: str
    temperature: float | None
    top_p: float | None
    top_k: int | None
    max_tokens: int | None
    evaluator_score: int | None
    reviewer_notes: str | None
    selected_as_winner: bool
    created_at: datetime


class PromptExperimentListOut(BaseModel):
    """Paginated list of experiments."""

    items: list[PromptExperimentOut]
    total: int
    skip: int
    limit: int


class PromptExperimentRunUpdate(BaseModel):
    """Request body for updating an experiment run (PATCH)."""

    evaluator_score: int | None = None  # 1–5
    reviewer_notes: str | None = None
    selected_as_winner: bool | None = None
    variant_name: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_tokens: int | None = None


class PromptExperimentRunListOut(BaseModel):
    """Paginated list of experiment runs."""

    items: list[PromptExperimentRunOut]
    total: int
    skip: int
    limit: int
