"""Tests for prompt run quality review API endpoints (API-018).

All tests use mock service dependencies — no live DB required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai.router import get_review_service


# ── Helpers ──────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_review(
    review_id: uuid.UUID | None = None,
    prompt_run_id: uuid.UUID | None = None,
    accuracy_score: float | None = None,
    ready_to_send: bool | None = None,
) -> MagicMock:
    r = MagicMock()
    r.id = review_id or uuid.uuid4()
    r.prompt_run_id = prompt_run_id or uuid.uuid4()
    r.tenant_id = None
    r.reviewer_user_id = "admin"
    r.accuracy_score = accuracy_score
    r.tone_fit_score = None
    r.persona_fit_score = None
    r.commercial_quality_score = None
    r.completeness_score = None
    r.hallucination_risk_score = None
    r.ready_to_send = ready_to_send
    r.reviewer_notes = None
    r.created_at = _now()
    r.updated_at = _now()
    return r


def _mock_service() -> MagicMock:
    return MagicMock()


# ── Create review ─────────────────────────────────────────────────────────────


class TestCreateReview:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_create_returns_201(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        svc.create_review.return_value = _mock_review(prompt_run_id=run_id)
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-runs/{run_id}/reviews",
                json={"prompt_run_id": str(run_id), "accuracy_score": 4.0},
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    def test_create_response_has_required_fields(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        review = _mock_review(prompt_run_id=run_id, accuracy_score=3.5, ready_to_send=True)
        svc.create_review.return_value = review
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-runs/{run_id}/reviews",
                json={"prompt_run_id": str(run_id)},
            )
            data = response.json()
            assert "id" in data
            assert "prompt_run_id" in data
            assert "accuracy_score" in data
            assert "ready_to_send" in data
            assert "created_at" in data
        finally:
            app.dependency_overrides.clear()

    def test_create_missing_run_returns_404(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        svc.create_review.side_effect = ValueError(f"Prompt run {run_id} not found.")
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-runs/{run_id}/reviews",
                json={"prompt_run_id": str(run_id)},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_create_invalid_score_returns_422(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        svc.create_review.side_effect = ValueError("accuracy_score must be between 0.0 and 5.0, got 9.0.")
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-runs/{run_id}/reviews",
                json={"prompt_run_id": str(run_id), "accuracy_score": 9.0},
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_create_without_scores_accepted(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        svc.create_review.return_value = _mock_review(prompt_run_id=run_id)
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-runs/{run_id}/reviews",
                json={"prompt_run_id": str(run_id)},
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    def test_create_ready_to_send_stored(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        review = _mock_review(prompt_run_id=run_id, ready_to_send=True)
        svc.create_review.return_value = review
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.post(
                f"/api/v1/ai/prompt-runs/{run_id}/reviews",
                json={"prompt_run_id": str(run_id), "ready_to_send": True},
            )
            assert response.json()["ready_to_send"] is True
        finally:
            app.dependency_overrides.clear()


# ── List reviews ──────────────────────────────────────────────────────────────


class TestListReviews:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_list_returns_200(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        svc.list_reviews.return_value = ([_mock_review(prompt_run_id=run_id)], 1)
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{run_id}/reviews")
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_list_returns_items_and_total(self) -> None:
        run_id = uuid.uuid4()
        reviews = [_mock_review(prompt_run_id=run_id) for _ in range(2)]
        svc = _mock_service()
        svc.list_reviews.return_value = (reviews, 2)
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{run_id}/reviews")
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.clear()

    def test_list_empty_returns_zero_total(self) -> None:
        run_id = uuid.uuid4()
        svc = _mock_service()
        svc.list_reviews.return_value = ([], 0)
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.get(f"/api/v1/ai/prompt-runs/{run_id}/reviews")
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []
        finally:
            app.dependency_overrides.clear()


# ── Update review ─────────────────────────────────────────────────────────────


class TestUpdateReview:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_patch_returns_200(self) -> None:
        review_id = uuid.uuid4()
        svc = _mock_service()
        updated = _mock_review(review_id=review_id, accuracy_score=4.5, ready_to_send=True)
        svc.update_review.return_value = updated
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.patch(
                f"/api/v1/ai/prompt-run-reviews/{review_id}",
                json={"accuracy_score": 4.5, "ready_to_send": True},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_patch_updates_score_and_notes(self) -> None:
        review_id = uuid.uuid4()
        svc = _mock_service()
        updated = _mock_review(review_id=review_id, accuracy_score=5.0)
        updated.reviewer_notes = "Excellent draft."
        svc.update_review.return_value = updated
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.patch(
                f"/api/v1/ai/prompt-run-reviews/{review_id}",
                json={"accuracy_score": 5.0, "reviewer_notes": "Excellent draft."},
            )
            data = response.json()
            assert data["accuracy_score"] == 5.0
            assert data["reviewer_notes"] == "Excellent draft."
        finally:
            app.dependency_overrides.clear()

    def test_patch_not_found_returns_404(self) -> None:
        review_id = uuid.uuid4()
        svc = _mock_service()
        svc.update_review.side_effect = ValueError(f"AIPromptRunReview {review_id} not found")
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            response = self.client.patch(
                f"/api/v1/ai/prompt-run-reviews/{review_id}",
                json={"ready_to_send": True},
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_patch_does_not_allow_prompt_run_id_change(self) -> None:
        """Verify update_review is called with only safe fields."""
        review_id = uuid.uuid4()
        svc = _mock_service()
        updated = _mock_review(review_id=review_id)
        svc.update_review.return_value = updated
        app.dependency_overrides[get_review_service] = lambda: svc
        try:
            self.client.patch(
                f"/api/v1/ai/prompt-run-reviews/{review_id}",
                json={"ready_to_send": False},
            )
            call_updates = svc.update_review.call_args[0][1]
            assert "prompt_run_id" not in call_updates
        finally:
            app.dependency_overrides.clear()
