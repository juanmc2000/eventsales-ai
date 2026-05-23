"""Tests for the training example capture feature (AI-008).

All tests use schema validation and mock repositories — no live DB required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai.router import get_training_service
from app.modules.ai.schemas import TrainingExampleCreate, TrainingExampleOut, TrainingExampleListOut


def _make_mock_example(
    example_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    prompt_key: str = "draft_response",
    approved: bool = False,
) -> MagicMock:
    ex = MagicMock()
    ex.id = example_id or uuid.uuid4()
    ex.prompt_run_id = run_id or uuid.uuid4()
    ex.tenant_id = "default"
    ex.prompt_key = prompt_key
    ex.original_output = {"subject": "Hello", "body": "Dear Alice..."}
    ex.corrected_output = None
    ex.correction_reason = None
    ex.reviewed_by_user_id = None
    ex.quality_rating = None
    ex.approved_for_training = approved
    ex.created_at = datetime.now(timezone.utc)
    return ex


def _mock_service(
    created: MagicMock | None = None,
    found: MagicMock | None = None,
    listed: list | None = None,
    total: int = 0,
) -> MagicMock:
    svc = MagicMock()
    svc.create.return_value = created or _make_mock_example()
    svc.get.return_value = found
    svc.list.return_value = (listed or [], total)
    return svc


# ── Schema tests ───────────────────────────────────────────────────────────

class TestTrainingExampleSchemas:
    def test_create_schema_requires_prompt_run_id(self) -> None:
        with pytest.raises(Exception):
            TrainingExampleCreate.model_validate({})

    def test_create_schema_accepts_minimal_input(self) -> None:
        run_id = uuid.uuid4()
        data = TrainingExampleCreate(prompt_run_id=run_id)
        assert data.prompt_run_id == run_id
        assert data.approved_for_training is False
        assert data.corrected_output is None

    def test_create_schema_accepts_full_input(self) -> None:
        data = TrainingExampleCreate(
            prompt_run_id=uuid.uuid4(),
            corrected_output={"subject": "Better subject", "body": "Better body"},
            correction_reason="Response was too formal",
            quality_rating=3,
            approved_for_training=True,
            reviewed_by_user_id="manager@example.com",
        )
        assert data.quality_rating == 3
        assert data.approved_for_training is True

    def test_out_schema_from_orm(self) -> None:
        mock = _make_mock_example()
        out = TrainingExampleOut.model_validate(mock)
        assert out.prompt_key == "draft_response"
        assert out.approved_for_training is False

    def test_list_out_structure(self) -> None:
        items = [TrainingExampleOut.model_validate(_make_mock_example()) for _ in range(2)]
        list_out = TrainingExampleListOut(items=items, total=2, skip=0, limit=50)
        assert list_out.total == 2


# ── Service tests ──────────────────────────────────────────────────────────

class TestTrainingExampleService:
    def test_create_raises_if_run_not_found(self) -> None:
        from app.modules.ai.service import TrainingExampleService

        db = MagicMock()
        service = TrainingExampleService(db)
        service._repo = MagicMock()
        service._repo.get_run.return_value = None

        with pytest.raises(ValueError, match="not found"):
            service.create({"prompt_run_id": uuid.uuid4()})

    def test_create_populates_original_output_from_run(self) -> None:
        from app.modules.ai.service import TrainingExampleService

        db = MagicMock()
        service = TrainingExampleService(db)
        run_id = uuid.uuid4()

        mock_run = MagicMock()
        mock_run.tenant_id = "default"
        mock_run.prompt_key = "draft_response"
        mock_run.parsed_response = {"subject": "Re: Enquiry", "body": "Dear Alice..."}

        service._repo = MagicMock()
        service._repo.get_run.return_value = mock_run
        mock_example = _make_mock_example(run_id=run_id)
        service._repo.create_training_example_from_data.return_value = mock_example

        service.create({"prompt_run_id": run_id})

        call_data = service._repo.create_training_example_from_data.call_args[0][0]
        assert call_data["original_output"] == {"subject": "Re: Enquiry", "body": "Dear Alice..."}
        assert call_data["prompt_key"] == "draft_response"

    def test_create_stores_corrected_output(self) -> None:
        from app.modules.ai.service import TrainingExampleService

        db = MagicMock()
        service = TrainingExampleService(db)
        run_id = uuid.uuid4()

        mock_run = MagicMock()
        mock_run.tenant_id = "default"
        mock_run.prompt_key = "draft_response"
        mock_run.parsed_response = None

        service._repo = MagicMock()
        service._repo.get_run.return_value = mock_run
        service._repo.create_training_example_from_data.return_value = _make_mock_example()

        corrected = {"subject": "Better subject", "body": "Better body"}
        service.create({
            "prompt_run_id": run_id,
            "corrected_output": corrected,
            "approved_for_training": True,
        })

        call_data = service._repo.create_training_example_from_data.call_args[0][0]
        assert call_data["corrected_output"] == corrected
        assert call_data["approved_for_training"] is True


# ── Endpoint tests ─────────────────────────────────────────────────────────

class TestTrainingExampleEndpoints:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_create_returns_201(self) -> None:
        run_id = uuid.uuid4()
        mock_svc = _mock_service(created=_make_mock_example(run_id=run_id))
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.post(
                "/api/v1/ai/training-examples",
                json={"prompt_run_id": str(run_id)},
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    def test_create_returns_404_when_run_missing(self) -> None:
        mock_svc = MagicMock()
        mock_svc.create.side_effect = ValueError("Prompt run not found.")
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.post(
                "/api/v1/ai/training-examples",
                json={"prompt_run_id": str(uuid.uuid4())},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_create_response_has_required_fields(self) -> None:
        run_id = uuid.uuid4()
        mock_svc = _mock_service(created=_make_mock_example(run_id=run_id))
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.post(
                "/api/v1/ai/training-examples",
                json={"prompt_run_id": str(run_id)},
            )
            data = response.json()
            assert "id" in data
            assert "prompt_run_id" in data
            assert "approved_for_training" in data
        finally:
            app.dependency_overrides.clear()

    def test_list_returns_200(self) -> None:
        mock_svc = _mock_service(listed=[_make_mock_example()], total=1)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.get("/api/v1/ai/training-examples")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_prompt_key_filter(self) -> None:
        mock_svc = _mock_service(listed=[], total=0)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            self.client.get("/api/v1/ai/training-examples?prompt_key=draft_response")
            call_kwargs = mock_svc.list.call_args.kwargs
            assert call_kwargs["prompt_key"] == "draft_response"
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_prompt_run_id_filter(self) -> None:
        run_id = uuid.uuid4()
        mock_svc = _mock_service(listed=[], total=0)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            self.client.get(f"/api/v1/ai/training-examples?prompt_run_id={run_id}")
            call_kwargs = mock_svc.list.call_args.kwargs
            assert str(call_kwargs["prompt_run_id"]) == str(run_id)
        finally:
            app.dependency_overrides.clear()

    def test_list_passes_approved_only_filter(self) -> None:
        mock_svc = _mock_service(listed=[], total=0)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            self.client.get("/api/v1/ai/training-examples?approved_only=true")
            call_kwargs = mock_svc.list.call_args.kwargs
            assert call_kwargs["approved_only"] is True
        finally:
            app.dependency_overrides.clear()

    def test_detail_returns_200_for_existing_example(self) -> None:
        example = _make_mock_example()
        mock_svc = _mock_service(found=example)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/training-examples/{example.id}")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_detail_returns_404_for_missing_example(self) -> None:
        mock_svc = _mock_service(found=None)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/training-examples/{uuid.uuid4()}")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_detail_includes_original_output(self) -> None:
        example = _make_mock_example()
        mock_svc = _mock_service(found=example)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/training-examples/{example.id}")
            data = response.json()
            assert data["original_output"] == {"subject": "Hello", "body": "Dear Alice..."}
        finally:
            app.dependency_overrides.clear()

    def test_detail_shows_approved_flag(self) -> None:
        example = _make_mock_example(approved=True)
        mock_svc = _mock_service(found=example)
        app.dependency_overrides[get_training_service] = lambda: mock_svc
        try:
            response = self.client.get(f"/api/v1/ai/training-examples/{example.id}")
            data = response.json()
            assert data["approved_for_training"] is True
        finally:
            app.dependency_overrides.clear()
