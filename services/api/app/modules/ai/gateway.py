"""AI Gateway — the single backend entry point for all LLM calls.

All modules that need an LLM response must go through AIGateway.run().
No module should call AnthropicProvider or FallbackProvider directly.

Responsibilities:
1. Resolve the active prompt definition for the requested key.
2. Render system and user prompts from the definition and input payload.
3. Compute a deterministic input hash.
4. Create a pending ai_prompt_run record.
5. Call the provider (or skip if fallback mode is active).
6. Record raw response, latency, and status.
7. Return a typed AIGatewayResult.

The draft generation migration (AI-006) wires this gateway into the
DraftGenerationService.  Until then, the gateway is available but not
called by existing services.
"""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.modules.ai.constants import (
    MODEL_PROVIDER_ANTHROPIC,
    MODEL_PROVIDER_FALLBACK,
    RUN_STATUS_ERROR,
    RUN_STATUS_FALLBACK,
    RUN_STATUS_SUCCESS,
    TRIGGER_SOURCE_API,
    VALIDATION_SKIPPED,
)
from app.modules.ai.validators import OutputValidator
from app.modules.ai.prompt_registry import PromptRegistry
from app.modules.ai.prompt_renderer import MissingPromptVariables, PromptRenderer
from app.modules.ai.provider import make_provider
from app.modules.ai.repository import AIPromptRunRepository
from app.modules.ai.schemas import AIGatewayRequest, AIGatewayResult

logger = logging.getLogger(__name__)

# Module-level singletons — constructed once per process
_registry = PromptRegistry()
_renderer = PromptRenderer()
_validator = OutputValidator()


class AIGateway:
    """Executes a prompt run and records the full trace.

    Instantiate with a database session and an optional API key.
    The API key controls whether a live provider or the fallback is used.

    Example::

        gateway = AIGateway(db=db, api_key=settings.anthropic_api_key)
        result = gateway.run(AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={"persona_name": "Eleanor", ...},
            enquiry_id=enquiry_id,
        ))
    """

    def __init__(self, db: Session, api_key: str = "") -> None:
        self._db = db
        self._repo = AIPromptRunRepository(db)
        self._provider, self._is_fallback = make_provider(api_key)

    def run(self, request: AIGatewayRequest) -> AIGatewayResult:
        """Execute a prompt run end-to-end and return the result.

        Always creates an ai_prompt_run record, even for fallback runs.
        Never raises — errors are captured in the run record and result.
        """
        # ── 1. Resolve prompt definition ──────────────────────────────────────
        try:
            defn = _registry.get(request.prompt_key)
        except KeyError as exc:
            return self._error_result(request, str(exc))

        # ── 2. Render prompts (skip for fallback) ─────────────────────────────
        rendered_system: str | None = None
        rendered_user: str | None = None
        input_hash: str | None = None

        if not self._is_fallback:
            try:
                rendered_system = _renderer.render_system(defn, request.input_payload)
                rendered_user = _renderer.render_user(defn, request.input_payload)
                input_hash = PromptRenderer.input_hash(rendered_system, rendered_user)
            except MissingPromptVariables as exc:
                logger.warning("Prompt render failed for %s: %s", request.prompt_key, exc)
                return self._error_result(request, str(exc))

        # ── 3. Create pending run record ──────────────────────────────────────
        run_data: dict = {
            "tenant_id": request.tenant_id,
            "restaurant_id": request.restaurant_id,
            "enquiry_id": request.enquiry_id,
            "persona_id": request.persona_id,
            "trigger_type": request.trigger_type,
            "trigger_source": request.trigger_source or TRIGGER_SOURCE_API,
            "triggered_by_user_id": request.triggered_by_user_id,
            "prompt_key": defn.key,
            "prompt_version": defn.version,
            "model_provider": MODEL_PROVIDER_FALLBACK if self._is_fallback else MODEL_PROVIDER_ANTHROPIC,
            "model_name": self._provider.model_name,
            "rendered_system_prompt": rendered_system,
            "rendered_user_prompt": rendered_user,
            "input_payload": request.input_payload,
            "input_hash": input_hash,
            "fallback_used": self._is_fallback,
            "fallback_reason": "no_api_key" if self._is_fallback else None,
            "validation_status": VALIDATION_SKIPPED,
            "status": RUN_STATUS_FALLBACK if self._is_fallback else RUN_STATUS_SUCCESS,
        }

        try:
            run = self._repo.create_run(run_data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to create ai_prompt_run: %s", exc)
            # Return a result without a persisted run ID
            return AIGatewayResult(
                run_id=uuid.uuid4(),
                prompt_key=defn.key,
                prompt_version=defn.version,
                model_name=self._provider.model_name,
                model_provider=MODEL_PROVIDER_FALLBACK if self._is_fallback else MODEL_PROVIDER_ANTHROPIC,
                rendered_system_prompt=rendered_system,
                rendered_user_prompt=rendered_user,
                raw_response=None,
                is_fallback=True,
                fallback_reason="db_error",
                validation_status=VALIDATION_SKIPPED,
                latency_ms=0,
                status=RUN_STATUS_ERROR,
                error_message=str(exc),
            )

        # ── 4. Fallback path: no provider call needed ─────────────────────────
        if self._is_fallback:
            return AIGatewayResult(
                run_id=run.id,
                prompt_key=defn.key,
                prompt_version=defn.version,
                model_name=self._provider.model_name,
                model_provider=MODEL_PROVIDER_FALLBACK,
                rendered_system_prompt=None,
                rendered_user_prompt=None,
                raw_response=None,
                is_fallback=True,
                fallback_reason="no_api_key",
                validation_status=VALIDATION_SKIPPED,
                latency_ms=0,
                status=RUN_STATUS_FALLBACK,
            )

        # ── 5. Call provider and measure latency ──────────────────────────────
        raw_response: str | None = None
        error_message: str | None = None
        run_status = RUN_STATUS_SUCCESS
        start = time.monotonic()

        try:
            raw_response = self._provider.generate_from_prompts(
                rendered_system,  # type: ignore[arg-type]
                rendered_user,    # type: ignore[arg-type]
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Provider call failed for %s: %s", request.prompt_key, exc)
            error_message = str(exc)
            run_status = RUN_STATUS_ERROR

        latency_ms = int((time.monotonic() - start) * 1000)

        # ── 6. Validate structured output ─────────────────────────────────────
        validation = _validator.validate(
            raw_response=raw_response,
            schema_name=defn.output_schema_name,
            is_fallback=False,
        )

        # ── 7. Update run record with result ──────────────────────────────────
        try:
            self._repo.update_run(run.id, {
                "raw_response": raw_response,
                "parsed_response": validation.parsed,
                "validation_status": validation.status,
                "validation_errors": validation.errors,
                "latency_ms": latency_ms,
                "status": run_status,
                "error_message": error_message,
            })
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to update ai_prompt_run %s: %s", run.id, exc)

        # ── 8. Return result ──────────────────────────────────────────────────
        return AIGatewayResult(
            run_id=run.id,
            prompt_key=defn.key,
            prompt_version=defn.version,
            model_name=self._provider.model_name,
            model_provider=MODEL_PROVIDER_ANTHROPIC,
            rendered_system_prompt=rendered_system,
            rendered_user_prompt=rendered_user,
            raw_response=raw_response,
            is_fallback=False,
            fallback_reason=None,
            validation_status=validation.status,
            parsed_response=validation.parsed,
            validation_errors=validation.errors,
            latency_ms=latency_ms,
            status=run_status,
            error_message=error_message,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _error_result(self, request: AIGatewayRequest, message: str) -> AIGatewayResult:
        """Return a result indicating a pre-call error (e.g. unknown prompt key)."""
        return AIGatewayResult(
            run_id=uuid.uuid4(),
            prompt_key=request.prompt_key,
            prompt_version=0,
            model_name="none",
            model_provider="none",
            rendered_system_prompt=None,
            rendered_user_prompt=None,
            raw_response=None,
            is_fallback=True,
            fallback_reason="configuration_error",
            validation_status=VALIDATION_SKIPPED,
            latency_ms=0,
            status=RUN_STATUS_ERROR,
            error_message=message,
        )
