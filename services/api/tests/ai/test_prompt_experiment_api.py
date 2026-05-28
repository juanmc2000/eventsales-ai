"""Tests for prompt experiment API endpoints (API-017).

All tests use mock service dependencies — no live DB required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai.router import get_experiment_service
from app.modules.ai.schemas import (
    PromptExperimentOut,
    PromptExperimentRunOut,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_experiment(
    experiment_id: uuid.UUID | None = None,
    prompt_key: str = "draft_response",
    name: str = "Temperature Comparison",
    status: str = "active",
) -> MagicMock:
    exp = MagicMock()
    exp.id = experiment_id or uuid.uuid4()
    exp.tenant_id = None
    exp.prompt_key = prompt_key
    exp.name = name
    exp.goal = "Compare 0.3 vs 0.7 temperature."
    exp.baseline_prompt_version_id = None
    exp.status = status
    exp.notes = None
    exp.created_at = _now()
    return exp


def _mock_exp_run(
    run_id: uuid.UUID | None = None,
    experiment_id: uuid.UUID | None = None,
    variant_name: str = "baseline",
    selected_as_winner: bool = False,
) -> MagicMock:
    run = MagicMock()
    run.id = run_id or uuid.uuid4()
    run.experiment_id = experiment_id or uuid.uuid4()
    run.prompt_run_id = uuid.uuid4()
    run.variant_name = variant_name
    run.temperature = 0.7
    run.top_p = None
    run.top_k = None
    run.max_tokens = 800
    run.evaluator_score = None
    run.reviewer_notes = None
    run.selected_as_winner = selected_as_winner
    run.created_at = _now()
    return run


def _mock_service(
    experiments: list | None = None,
    exp_runs: list | None = None,
) -> MagicMock:
    svc = MagicMock()
    experiments = experiments or []
    exp_runs = exp_runs or []
    svc.list_experiments.return_value = (experiments, len(experiments))
    svc.list_runs.return_value = (exp_runs, len(exp_runs))
    return svc


# ── Create experiment ────────────────────────────────────────────────────────


class TestCreateExperiment:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_create_returns_201(self) -> None:
        mock_svc = _mock_service()
        mock_svc.create_experiment.return_value = _mock_experiment()
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.post(
                "/api/v1/ai/prompt-experiments",
                json={"prompt_key": "draft_response", "name": "Temperature Test"},
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    def test_create_response_has_required_fields(self) -> None:
        mock_svc = _mock_service()
        exp = _mock_experiment()
        mock_svc.create_experiment.return_value = exp
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.post(
                "/api/v1/ai/prompt-experiments",
                json={"prompt_key": "draft_response", "name": "Test Exp"},
            )
            data = response.json()
            assert "id" in data
            assert data["prompt_key"] == "draft_response"
            assert data["status"] == "active"
        finally:
            app.dependency_overrides.clear()

    def test_create_service_raises_returns_422(self) -> None:
        mock_svc = _mock_service()
        mock_svc.create_experiment.side_effect = ValueError("prompt_key is required.")
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.post(
                "/api/v1/ai/prompt-experiments",
                json={"prompt_key": "", "name": "Test"},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ── List experiments ─────────────────────────────────────────────────────────


class TestListExperiments:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_list_returns_200(self) -> None:
        mock_svc = _mock_service([_mock_experiment()])
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get("/api/v1/ai/prompt-experiments")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_list_returns_items_and_total(self) -> None:
        experiments = [_mock_experiment(), _mock_experiment()]
        mock_svc = _mock_service(experiments)
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get("/api/v1/ai/prompt-experiments")
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_prompt_key_filter(self) -> None:
        mock_svc = _mock_service()
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            self.client.get("/api/v1/ai/prompt-experiments?prompt_key=draft_response")
            call_kwargs = mock_svc.list_experiments.call_args.kwargs
            assert call_kwargs["prompt_key"] == "draft_response"
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_status_filter(self) -> None:
        mock_svc = _mock_service()
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            self.client.get("/api/v1/ai/prompt-experiments?status=completed")
            call_kwargs = mock_svc.list_experiments.call_args.kwargs
            assert call_kwargs["status"] == "completed"
        finally:
            app.dependency_overrides.clear()

    def test_empty_list_returns_zero_total(self) -> None:
        mock_svc = _mock_service([])
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get("/api/v1/ai/prompt-experiments")
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []
        finally:
            app.dependency_overrides.clear()


# ── Get experiment detail ────────────────────────────────────────────────────


class TestGetExperiment:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_get_returns_200_for_existing(self) -> None:
        exp = _mock_experiment()
        mock_svc = _mock_service()
        mock_svc.get_experiment.return_value = exp
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-experiments/{exp.id}")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_get_returns_404_for_missing(self) -> None:
        mock_svc = _mock_service()
        mock_svc.get_experiment.return_value = None
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-experiments/{uuid.uuid4()}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_returns_prompt_key(self) -> None:
        exp = _mock_experiment(prompt_key="enquiry_extraction")
        mock_svc = _mock_service()
        mock_svc.get_experiment.return_value = exp
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-experiments/{exp.id}")
            assert response.json()["prompt_key"] == "enquiry_extraction"
        finally:
            app.dependency_overrides.clear()


# ── Add experiment run ───────────────────────────────────────────────────────


class TestAddExperimentRun:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_add_run_returns_201(self) -> None:
        exp_id = uuid.uuid4()
        mock_svc = _mock_service()
        mock_svc.add_run.return_value = _mock_exp_run(experiment_id=exp_id)
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-experiments/{exp_id}/runs",
                json={
                    "prompt_run_id": str(uuid.uuid4()),
                    "variant_name": "temperature_0.3",
                    "temperature": 0.3,
                },
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    def test_add_run_response_has_variant_name(self) -> None:
        exp_id = uuid.uuid4()
        mock_svc = _mock_service()
        run = _mock_exp_run(experiment_id=exp_id, variant_name="temperature_0.3")
        mock_svc.add_run.return_value = run
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-experiments/{exp_id}/runs",
                json={
                    "prompt_run_id": str(uuid.uuid4()),
                    "variant_name": "temperature_0.3",
                },
            )
            assert response.json()["variant_name"] == "temperature_0.3"
        finally:
            app.dependency_overrides.clear()

    def test_add_run_missing_prompt_run_returns_404(self) -> None:
        exp_id = uuid.uuid4()
        mock_svc = _mock_service()
        mock_svc.add_run.side_effect = ValueError("Prompt run not found.")
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-experiments/{exp_id}/runs",
                json={
                    "prompt_run_id": str(uuid.uuid4()),
                    "variant_name": "baseline",
                },
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ── List experiment runs ─────────────────────────────────────────────────────


class TestListExperimentRuns:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_list_runs_returns_200(self) -> None:
        exp_id = uuid.uuid4()
        mock_svc = _mock_service(exp_runs=[_mock_exp_run(experiment_id=exp_id)])
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-experiments/{exp_id}/runs")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_list_runs_returns_items(self) -> None:
        exp_id = uuid.uuid4()
        runs = [_mock_exp_run(experiment_id=exp_id, variant_name=f"v{i}") for i in range(3)]
        mock_svc = _mock_service(exp_runs=runs)
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-experiments/{exp_id}/runs")
            data = response.json()
            assert data["total"] == 3
            assert len(data["items"]) == 3
        finally:
            app.dependency_overrides.clear()


# ── Update experiment run ────────────────────────────────────────────────────


class TestUpdateExperimentRun:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_patch_run_returns_200(self) -> None:
        exp_id = uuid.uuid4()
        run_id = uuid.uuid4()
        mock_svc = _mock_service()
        updated_run = _mock_exp_run(run_id=run_id, experiment_id=exp_id)
        updated_run.evaluator_score = 4
        updated_run.selected_as_winner = True
        mock_svc.update_run.return_value = updated_run
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.patch(
                f"/api/v1/ai/prompt-experiments/{exp_id}/runs/{run_id}",
                json={"evaluator_score": 4, "selected_as_winner": True},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_patch_run_updates_score_and_winner(self) -> None:
        exp_id = uuid.uuid4()
        run_id = uuid.uuid4()
        mock_svc = _mock_service()
        updated_run = _mock_exp_run(run_id=run_id, experiment_id=exp_id, selected_as_winner=True)
        updated_run.evaluator_score = 5
        updated_run.reviewer_notes = "Best result."
        mock_svc.update_run.return_value = updated_run
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.patch(
                f"/api/v1/ai/prompt-experiments/{exp_id}/runs/{run_id}",
                json={"evaluator_score": 5, "reviewer_notes": "Best result.", "selected_as_winner": True},
            )
            data = response.json()
            assert data["evaluator_score"] == 5
            assert data["reviewer_notes"] == "Best result."
            assert data["selected_as_winner"] is True
        finally:
            app.dependency_overrides.clear()

    def test_patch_run_not_found_returns_404(self) -> None:
        exp_id = uuid.uuid4()
        run_id = uuid.uuid4()
        mock_svc = _mock_service()
        mock_svc.update_run.side_effect = ValueError("Experiment run not found.")
        app.dependency_overrides[get_experiment_service] = lambda: mock_svc
        try:
            response = self.client.patch(
                f"/api/v1/ai/prompt-experiments/{exp_id}/runs/{run_id}",
                json={"evaluator_score": 3},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
