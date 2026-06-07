"""Tests for AutoSendDryRunService and AutoSendDryRunResult (AUTO-003).

Covers:
  - AutoSendDryRunResult dataclass: field defaults, decision_summary, to_dict()
  - AutoSendDryRunService.simulate(): no-draft path, missing enquiry, correct
    gate outcomes, SMTP never called
  - Endpoint: POST /api/v1/enquiries/{enquiry_id}/auto-send/dry-run
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.db.models  # noqa: F401 — registers all SQLAlchemy models

from app.main import app
from app.modules.ai.auto_send_dry_run import AutoSendDryRunResult, AutoSendDryRunService


# ── AutoSendDryRunResult ─────────────────────────────────────────────────────


class TestAutoSendDryRunResult:
    def _result(self, **overrides) -> AutoSendDryRunResult:
        defaults = dict(
            enquiry_id=uuid.uuid4(),
            simulated_at=datetime.now(tz=timezone.utc),
            draft_message_id=uuid.uuid4(),
            draft_subject="Test subject",
            draft_body="Dear Alice, thank you.",
            draft_to_address="alice@example.com",
            compliance_passed=True,
            compliance_violations=[],
            integrity_passed=True,
            integrity_violations=[],
            auto_send_allowed=True,
            auto_send_blockers=[],
            response_goal="CONFIRM_AVAILABLE",
            availability_contract="CONFIRMED_AVAILABLE",
            date_status="resolved",
        )
        defaults.update(overrides)
        return AutoSendDryRunResult(**defaults)

    def test_allowed_decision_summary(self) -> None:
        r = self._result(auto_send_allowed=True)
        assert "WOULD SEND" in r.decision_summary

    def test_blocked_compliance_decision_summary(self) -> None:
        r = self._result(
            auto_send_allowed=False,
            compliance_passed=False,
            compliance_violations=["overclaim violation"],
        )
        assert "BLOCKED" in r.decision_summary
        assert "compliance" in r.decision_summary.lower()

    def test_blocked_integrity_decision_summary(self) -> None:
        r = self._result(
            auto_send_allowed=False,
            compliance_passed=True,
            integrity_passed=False,
            integrity_violations=["restaurant name mismatch"],
        )
        assert "BLOCKED" in r.decision_summary
        assert "integrity" in r.decision_summary.lower()

    def test_blocked_gate_decision_summary(self) -> None:
        r = self._result(
            auto_send_allowed=False,
            compliance_passed=True,
            integrity_passed=True,
            auto_send_blockers=["Goal REQUEST_MISSING_INFORMATION not in auto-send set"],
        )
        assert "BLOCKED" in r.decision_summary

    def test_to_dict_contains_required_keys(self) -> None:
        r = self._result()
        d = r.to_dict()
        required = {
            "enquiry_id", "simulated_at", "draft_message_id", "draft_subject",
            "draft_body", "draft_to_address", "compliance_passed", "compliance_violations",
            "integrity_passed", "integrity_violations", "auto_send_allowed",
            "auto_send_blockers", "response_goal", "availability_contract",
            "date_status", "decision_summary",
        }
        assert required <= set(d.keys())

    def test_to_dict_enquiry_id_is_string(self) -> None:
        r = self._result()
        assert isinstance(r.to_dict()["enquiry_id"], str)

    def test_to_dict_simulated_at_is_iso_string(self) -> None:
        r = self._result()
        ts = r.to_dict()["simulated_at"]
        assert isinstance(ts, str)
        # Verify parseable
        datetime.fromisoformat(ts)

    def test_no_draft_result_has_compliance_failure(self) -> None:
        r = self._result(
            draft_body=None,
            draft_message_id=None,
            auto_send_allowed=False,
            compliance_passed=False,
            compliance_violations=["No draft message found for this enquiry"],
        )
        assert not r.compliance_passed
        assert not r.auto_send_allowed


# ── AutoSendDryRunService ────────────────────────────────────────────────────


class TestAutoSendDryRunService:
    def _mock_db(self):
        return MagicMock()

    def _make_enquiry(self, enquiry_id: uuid.UUID) -> MagicMock:
        enquiry = MagicMock()
        enquiry.id = enquiry_id
        enquiry.restaurant_id = uuid.uuid4()
        enquiry.email = "guest@example.com"
        enquiry.persona_id = None
        return enquiry

    def _make_draft_message(self, body: str = "Dear Alice, I am pleased to confirm availability.") -> MagicMock:
        msg = MagicMock()
        msg.id = uuid.uuid4()
        msg.subject = "Re: Booking Enquiry"
        msg.body = body
        return msg

    def test_raises_value_error_for_missing_enquiry(self) -> None:
        db = self._mock_db()
        svc = AutoSendDryRunService(db)

        with patch("app.modules.enquiries.repository.EnquiryRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(ValueError, match="not found"):
                svc.simulate(uuid.uuid4())

    def test_simulate_no_draft_returns_blocked_result(self) -> None:
        enquiry_id = uuid.uuid4()
        db = self._mock_db()
        svc = AutoSendDryRunService(db)

        with (
            patch("app.modules.enquiries.repository.EnquiryRepository") as mock_repo_cls,
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.restaurants.repository.RestaurantRepository") as mock_rest_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = self._make_enquiry(enquiry_id)
            mock_repo.get_latest_draft_message.return_value = None
            mock_repo_cls.return_value = mock_repo

            mock_plan = MagicMock()
            mock_plan.get_latest.return_value = None
            mock_plan_cls.return_value = mock_plan

            mock_rest = MagicMock()
            mock_rest_instance = MagicMock()
            mock_rest_instance.name = "Test Restaurant"
            mock_rest.return_value = MagicMock(get_by_id=MagicMock(return_value=mock_rest_instance))
            mock_rest_cls.return_value = mock_rest.return_value

            result = svc.simulate(enquiry_id)

        assert result.draft_body is None
        assert result.compliance_passed is False
        assert result.auto_send_allowed is False
        assert "BLOCKED" in result.decision_summary

    def test_result_is_auto_send_dry_run_result_type(self) -> None:
        enquiry_id = uuid.uuid4()
        db = self._mock_db()
        svc = AutoSendDryRunService(db)

        with (
            patch("app.modules.enquiries.repository.EnquiryRepository") as mock_repo_cls,
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.restaurants.repository.RestaurantRepository") as mock_rest_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = self._make_enquiry(enquiry_id)
            mock_repo.get_latest_draft_message.return_value = None
            mock_repo_cls.return_value = mock_repo

            mock_plan = MagicMock()
            mock_plan.get_latest.return_value = None
            mock_plan_cls.return_value = mock_plan

            mock_rest = MagicMock()
            mock_rest.get_by_id.return_value = MagicMock(name="Test Restaurant")
            mock_rest_cls.return_value = mock_rest

            result = svc.simulate(enquiry_id)

        assert isinstance(result, AutoSendDryRunResult)

    def test_result_enquiry_id_matches(self) -> None:
        enquiry_id = uuid.uuid4()
        db = self._mock_db()
        svc = AutoSendDryRunService(db)

        with (
            patch("app.modules.enquiries.repository.EnquiryRepository") as mock_repo_cls,
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.restaurants.repository.RestaurantRepository") as mock_rest_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = self._make_enquiry(enquiry_id)
            mock_repo.get_latest_draft_message.return_value = None
            mock_repo_cls.return_value = mock_repo

            mock_plan = MagicMock()
            mock_plan.get_latest.return_value = None
            mock_plan_cls.return_value = mock_plan

            mock_rest = MagicMock()
            mock_rest.get_by_id.return_value = MagicMock(name="Test Restaurant")
            mock_rest_cls.return_value = mock_rest

            result = svc.simulate(enquiry_id)

        assert result.enquiry_id == enquiry_id

    def test_simulated_at_is_set(self) -> None:
        enquiry_id = uuid.uuid4()
        db = self._mock_db()
        svc = AutoSendDryRunService(db)

        with (
            patch("app.modules.enquiries.repository.EnquiryRepository") as mock_repo_cls,
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.restaurants.repository.RestaurantRepository") as mock_rest_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = self._make_enquiry(enquiry_id)
            mock_repo.get_latest_draft_message.return_value = None
            mock_repo_cls.return_value = mock_repo

            mock_plan = MagicMock()
            mock_plan.get_latest.return_value = None
            mock_plan_cls.return_value = mock_plan

            mock_rest = MagicMock()
            mock_rest.get_by_id.return_value = MagicMock(name="Test Restaurant")
            mock_rest_cls.return_value = mock_rest

            result = svc.simulate(enquiry_id)

        assert isinstance(result.simulated_at, datetime)
        assert result.simulated_at.tzinfo is not None

    def test_no_smtp_call_occurs(self) -> None:
        """Verify that no email send provider is called during dry run."""
        enquiry_id = uuid.uuid4()
        db = self._mock_db()
        svc = AutoSendDryRunService(db)

        with (
            patch("app.modules.enquiries.repository.EnquiryRepository") as mock_repo_cls,
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.restaurants.repository.RestaurantRepository") as mock_rest_cls,
            patch("app.modules.email.send_service.EmailSendService") as mock_email_svc,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = self._make_enquiry(enquiry_id)
            mock_repo.get_latest_draft_message.return_value = None
            mock_repo_cls.return_value = mock_repo

            mock_plan = MagicMock()
            mock_plan.get_latest.return_value = None
            mock_plan_cls.return_value = mock_plan

            mock_rest = MagicMock()
            mock_rest.get_by_id.return_value = MagicMock(name="Test Restaurant")
            mock_rest_cls.return_value = mock_rest

            svc.simulate(enquiry_id)

        mock_email_svc.assert_not_called()


# ── API endpoint ─────────────────────────────────────────────────────────────


class TestAutoSendDryRunEndpoint:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_endpoint_returns_404_for_missing_enquiry(self) -> None:
        fake_id = uuid.uuid4()
        with patch(
            "app.modules.ai.auto_send_dry_run.AutoSendDryRunService.simulate",
            side_effect=ValueError(f"Enquiry {fake_id} not found"),
        ):
            response = self.client.post(f"/api/v1/enquiries/{fake_id}/auto-send/dry-run")
        assert response.status_code == 404

    def test_endpoint_returns_200_with_result_keys(self) -> None:
        fake_id = uuid.uuid4()
        mock_result = AutoSendDryRunResult(
            enquiry_id=fake_id,
            simulated_at=datetime.now(tz=timezone.utc),
            draft_message_id=uuid.uuid4(),
            draft_subject="Test subject",
            draft_body="Dear guest.",
            draft_to_address="guest@example.com",
            compliance_passed=True,
            compliance_violations=[],
            integrity_passed=True,
            integrity_violations=[],
            auto_send_allowed=False,
            auto_send_blockers=["Goal REQUEST_MISSING_INFORMATION not in auto-send allowed set"],
            response_goal="REQUEST_MISSING_INFORMATION",
            availability_contract="NOT_CHECKED",
            date_status="unknown",
        )
        with patch(
            "app.modules.ai.auto_send_dry_run.AutoSendDryRunService.simulate",
            return_value=mock_result,
        ):
            response = self.client.post(f"/api/v1/enquiries/{fake_id}/auto-send/dry-run")
        assert response.status_code == 200
        data = response.json()
        assert "auto_send_allowed" in data
        assert "decision_summary" in data
        assert "compliance_passed" in data
        assert data["auto_send_allowed"] is False
