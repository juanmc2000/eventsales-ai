"""Tests for the prompt run trace API endpoints (AI-007).

All tests use schema validation and mock repositories — no live DB required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai.repository import AIPromptRunRepository
from app.modules.ai.router import get_repo
from app.modules.ai.schemas import PromptRunDetailOut, PromptRunListOut, PromptRunOut


def _make_mock_run(
    run_id: uuid.UUID | None = None,
    prompt_key: str = "draft_response",
    enquiry_id: uuid.UUID | None = None,
    restaurant_id: uuid.UUID | None = None,
    status: str = "success",
    validation_status: str = "skipped",
    fallback_used: bool = False,
) -> MagicMock:
    run = MagicMock()
    run.id = run_id or uuid.uuid4()
    run.prompt_key = prompt_key
    run.prompt_version = 1
    run.trigger_type = "manual_generate_draft"
    run.restaurant_id = restaurant_id or uuid.uuid4()
    run.enquiry_id = enquiry_id or uuid.uuid4()
    run.persona_id = uuid.uuid4()
    run.model_provider = "anthropic"
    run.model_name = "claude-haiku-4-5-20251001"
    run.prompt_name = None
    run.prompt_goal = None
    run.temperature = None
    run.top_p = None
    run.top_k = None
    run.max_tokens = None
    run.validation_status = validation_status
    run.fallback_used = fallback_used
    run.fallback_reason = None
    run.status = status
    run.latency_ms = 150
    run.created_at = datetime.now(timezone.utc)
    run.rendered_system_prompt = "System prompt text"
    run.rendered_user_prompt = "User prompt text"
    run.raw_response = "Dear Alice, thank you."
    run.parsed_response = None
    run.validation_errors = None
    run.input_hash = "abc123"
    run.error_message = None
    return run


# ── Schema tests ───────────────────────────────────────────────────────────

class TestPromptRunSchemas:
    def test_prompt_run_out_from_orm(self) -> None:
        mock_run = _make_mock_run()
        out = PromptRunOut.model_validate(mock_run)
        assert out.prompt_key == "draft_response"
        assert out.status == "success"
        assert out.fallback_used is False

    def test_prompt_run_detail_out_includes_prompts(self) -> None:
        mock_run = _make_mock_run()
        detail = PromptRunDetailOut.model_validate(mock_run)
        assert detail.rendered_system_prompt == "System prompt text"
        assert detail.rendered_user_prompt == "User prompt text"
        assert detail.raw_response == "Dear Alice, thank you."

    def test_prompt_run_list_out_structure(self) -> None:
        items = [PromptRunOut.model_validate(_make_mock_run()) for _ in range(3)]
        list_out = PromptRunListOut(items=items, total=3, skip=0, limit=50)
        assert list_out.total == 3
        assert len(list_out.items) == 3


# ── Endpoint tests ─────────────────────────────────────────────────────────

class TestPromptRunListEndpoint:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def _mock_repo(self, runs: list, total: int = None) -> MagicMock:
        repo = MagicMock(spec=AIPromptRunRepository)
        repo.list_runs.return_value = (runs, total if total is not None else len(runs))
        return repo

    def test_list_returns_200(self) -> None:
        mock_repo = self._mock_repo([_make_mock_run()])
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get("/api/v1/ai/prompt-runs")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_list_returns_items_and_total(self) -> None:
        runs = [_make_mock_run() for _ in range(3)]
        mock_repo = self._mock_repo(runs, total=3)
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get("/api/v1/ai/prompt-runs")
            data = response.json()
            assert data["total"] == 3
            assert len(data["items"]) == 3
        finally:
            app.dependency_overrides.clear()

    def test_list_empty_returns_zero_total(self) -> None:
        mock_repo = self._mock_repo([], total=0)
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get("/api/v1/ai/prompt-runs")
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_enquiry_id_filter(self) -> None:
        enquiry_id = uuid.uuid4()
        mock_repo = self._mock_repo([])
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            self.client.get(f"/api/v1/ai/prompt-runs?enquiry_id={enquiry_id}")
            call_kwargs = mock_repo.list_runs.call_args.kwargs
            assert str(call_kwargs["enquiry_id"]) == str(enquiry_id)
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_prompt_key_filter(self) -> None:
        mock_repo = self._mock_repo([])
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            self.client.get("/api/v1/ai/prompt-runs?prompt_key=draft_response")
            call_kwargs = mock_repo.list_runs.call_args.kwargs
            assert call_kwargs["prompt_key"] == "draft_response"
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_validation_status_filter(self) -> None:
        mock_repo = self._mock_repo([])
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            self.client.get("/api/v1/ai/prompt-runs?validation_status=passed")
            call_kwargs = mock_repo.list_runs.call_args.kwargs
            assert call_kwargs["validation_status"] == "passed"
        finally:
            app.dependency_overrides.clear()

    def test_list_pagination_params_forwarded(self) -> None:
        mock_repo = self._mock_repo([])
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            self.client.get("/api/v1/ai/prompt-runs?skip=10&limit=25")
            call_kwargs = mock_repo.list_runs.call_args.kwargs
            assert call_kwargs["skip"] == 10
            assert call_kwargs["limit"] == 25
        finally:
            app.dependency_overrides.clear()

    def test_list_items_have_required_fields(self) -> None:
        mock_repo = self._mock_repo([_make_mock_run()])
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get("/api/v1/ai/prompt-runs")
            item = response.json()["items"][0]
            assert "id" in item
            assert "prompt_key" in item
            assert "fallback_used" in item
            assert "status" in item
            assert "created_at" in item
        finally:
            app.dependency_overrides.clear()


class TestPromptRunDetailEndpoint:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def _mock_repo(self, run) -> MagicMock:
        repo = MagicMock(spec=AIPromptRunRepository)
        repo.get_run.return_value = run
        return repo

    def test_detail_returns_200_for_existing_run(self) -> None:
        run = _make_mock_run()
        mock_repo = self._mock_repo(run)
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{run.id}")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_detail_returns_404_for_missing_run(self) -> None:
        mock_repo = self._mock_repo(None)
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{uuid.uuid4()}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_detail_includes_rendered_prompts(self) -> None:
        run = _make_mock_run()
        mock_repo = self._mock_repo(run)
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{run.id}")
            data = response.json()
            assert data["rendered_system_prompt"] == "System prompt text"
            assert data["rendered_user_prompt"] == "User prompt text"
            assert data["raw_response"] == "Dear Alice, thank you."
        finally:
            app.dependency_overrides.clear()

    def test_detail_includes_prompt_version(self) -> None:
        run = _make_mock_run()
        mock_repo = self._mock_repo(run)
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{run.id}")
            data = response.json()
            assert data["prompt_version"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_detail_fallback_run_shows_fallback_fields(self) -> None:
        run = _make_mock_run(fallback_used=True, status="fallback")
        run.fallback_reason = "no_api_key"
        mock_repo = self._mock_repo(run)
        app.dependency_overrides[get_repo] = lambda: mock_repo
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{run.id}")
            data = response.json()
            assert data["fallback_used"] is True
            assert data["fallback_reason"] == "no_api_key"
            assert data["status"] == "fallback"
        finally:
            app.dependency_overrides.clear()
