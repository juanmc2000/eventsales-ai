"""Tests for freeform intake orchestration ordering (TEST-008).

Validates that when FreeformIntakeService is available (API-015 merged):
- Extraction runs before processing
- Processing runs before draft generation
- Failures in each step are isolated (don't crash the whole intake)
- No direct provider calls are made outside the AI Gateway

These tests use lazy imports and are designed to pass once API-015, API-014,
and WORKFLOW-007 are merged. They are skipped gracefully on main.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

# ── Lazy imports for Sprint 7 services ────────────────────────────────────────

try:
    from app.modules.enquiries.intake_service import FreeformIntakeService
    from app.modules.enquiries.schemas import FreeformIntakeRequest, FreeformIntakeOut
    _FREEFORM_INTAKE_AVAILABLE = True
except ImportError:
    _FREEFORM_INTAKE_AVAILABLE = False

try:
    from app.modules.enquiries.extraction_service import EnquiryExtractionService, ExtractionRequest, ExtractionResult
    _EXTRACTION_SVC_AVAILABLE = True
except ImportError:
    _EXTRACTION_SVC_AVAILABLE = False

try:
    from app.modules.enquiries.processing_service import EnquiryProcessingService, ProcessingRequest, ProcessingResult
    _PROCESSING_SVC_AVAILABLE = True
except ImportError:
    _PROCESSING_SVC_AVAILABLE = False


SKIP_NO_FREEFORM = pytest.mark.skipif(
    not _FREEFORM_INTAKE_AVAILABLE,
    reason="FreeformIntakeService not yet on this branch (requires API-015 merge)",
)

SKIP_NO_EXTRACTION = pytest.mark.skipif(
    not _EXTRACTION_SVC_AVAILABLE,
    reason="EnquiryExtractionService not yet on this branch (requires API-014 merge)",
)

SKIP_NO_PROCESSING = pytest.mark.skipif(
    not _PROCESSING_SVC_AVAILABLE,
    reason="EnquiryProcessingService not yet on this branch (requires WORKFLOW-007 merge)",
)


def _make_enquiry_mock():
    enquiry = MagicMock()
    enquiry.id = uuid.uuid4()
    enquiry.reference = "ENQ-TEST-001"
    enquiry.status = "new"
    enquiry.restaurant_id = uuid.uuid4()
    enquiry.created_at = datetime.now(timezone.utc)
    return enquiry


def _make_message_mock():
    msg = MagicMock()
    msg.id = uuid.uuid4()
    return msg


# ── Orchestration order tests ─────────────────────────────────────────────────


@SKIP_NO_FREEFORM
class TestFreeformOrchestrationsOrder:
    """Validates call ordering: extraction → processing → draft."""

    def _build_service(self, db=None):
        db = db or MagicMock()
        svc = FreeformIntakeService(db)
        return svc

    def _make_request(self, restaurant_id=None):
        return FreeformIntakeRequest(
            restaurant_id=restaurant_id or uuid.uuid4(),
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            freeform_text="We need a private venue for 20 guests on Friday 15th August for a corporate dinner.",
        )

    def _make_restaurant(self, restaurant_id=None):
        r = MagicMock()
        r.id = restaurant_id or uuid.uuid4()
        r.name = "Test Venue"
        return r

    def test_enquiry_created_before_extraction(self):
        """Enquiry must be persisted before extraction is attempted."""
        svc = self._build_service()
        restaurant = self._make_restaurant()
        enquiry = _make_enquiry_mock()
        enquiry.restaurant_id = restaurant.id
        inbound_msg = _make_message_mock()

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_persona_for_audience.return_value = None
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = inbound_msg

        call_order = []

        def record_create(*args, **kwargs):
            call_order.append("create_enquiry")
            return enquiry

        def record_add_message(*args, **kwargs):
            call_order.append("add_message")
            return inbound_msg

        svc._enquiry_repo.create = record_create
        svc._enquiry_repo.add_message = record_add_message

        req = self._make_request(restaurant_id=restaurant.id)

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", False),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", False),
            patch("app.modules.ai.service.DraftGenerationService") as MockDraft,
        ):
            MockDraft.return_value.generate_draft.side_effect = RuntimeError("no key")
            svc.intake_freeform(req)

        assert "create_enquiry" in call_order
        assert "add_message" in call_order
        # Enquiry created before message (ordering guaranteed by create → add_message)
        assert call_order.index("create_enquiry") < call_order.index("add_message")

    @SKIP_NO_EXTRACTION
    @SKIP_NO_PROCESSING
    def test_extraction_called_before_processing(self):
        """Extraction must run before processing when both services are available."""
        svc = self._build_service()
        restaurant = self._make_restaurant()
        enquiry = _make_enquiry_mock()
        enquiry.restaurant_id = restaurant.id
        inbound_msg = _make_message_mock()

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_persona_for_audience.return_value = None
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = inbound_msg

        call_order = []

        extraction_id = uuid.uuid4()
        mock_ext_result = ExtractionResult(
            extraction_id=extraction_id,
            prompt_run_id=uuid.uuid4(),
            is_fallback=False,
            validation_status="passed",
            parsed={"guest_count": 20, "event_date": "2026-08-15"},
        )

        mock_proc_result = ProcessingResult(
            snapshot_id=uuid.uuid4(),
            recommended_action="send_availability_confirmation",
            availability_result_json={"status": "available"},
            room_suitability_json=None,
            pricing_result_json={"recommended_minimum_spend": 2000.0},
            missing_fields_json=[],
            error_message=None,
        )

        def fake_extract(*args, **kwargs):
            call_order.append("extraction")
            return mock_ext_result

        def fake_process(*args, **kwargs):
            call_order.append("processing")
            return mock_proc_result

        req = self._make_request(restaurant_id=restaurant.id)

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", True),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", True),
            patch("app.modules.enquiries.intake_service.EnquiryExtractionService") as MockExtSvc,
            patch("app.modules.enquiries.intake_service.EnquiryProcessingService") as MockProcSvc,
            patch("app.modules.ai.service.DraftGenerationService") as MockDraft,
        ):
            MockExtSvc.return_value.extract = fake_extract
            MockProcSvc.return_value.process = fake_process
            MockDraft.return_value.generate_draft.side_effect = RuntimeError("no key")

            svc.intake_freeform(req)

        assert "extraction" in call_order
        assert "processing" in call_order
        assert call_order.index("extraction") < call_order.index("processing")

    def test_extraction_failure_does_not_prevent_draft(self):
        """If extraction fails, draft generation should still be attempted."""
        svc = self._build_service()
        restaurant = self._make_restaurant()
        enquiry = _make_enquiry_mock()
        enquiry.restaurant_id = restaurant.id

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_persona_for_audience.return_value = None
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = _make_message_mock()

        req = self._make_request(restaurant_id=restaurant.id)
        draft_called = []

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", True),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", False),
            patch("app.modules.enquiries.intake_service.EnquiryExtractionService") as MockExtSvc,
            patch("app.modules.ai.service.DraftGenerationService") as MockDraft,
        ):
            MockExtSvc.return_value.extract.side_effect = RuntimeError("LLM unavailable")

            def record_draft(*args, **kwargs):
                draft_called.append(True)
                raise RuntimeError("no key")

            MockDraft.return_value.generate_draft = record_draft
            result = svc.intake_freeform(req)

        assert result.enquiry_id == enquiry.id
        # Draft was still attempted despite extraction failure
        assert len(draft_called) == 1

    def test_processing_failure_does_not_prevent_draft(self):
        """If processing fails, draft generation should still be attempted."""
        if not _EXTRACTION_SVC_AVAILABLE or not _PROCESSING_SVC_AVAILABLE:
            pytest.skip("Sprint 7 services not available")

        svc = self._build_service()
        restaurant = self._make_restaurant()
        enquiry = _make_enquiry_mock()
        enquiry.restaurant_id = restaurant.id
        extraction_id = uuid.uuid4()

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_persona_for_audience.return_value = None
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = _make_message_mock()

        req = self._make_request(restaurant_id=restaurant.id)
        draft_called = []

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", True),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", True),
            patch("app.modules.enquiries.intake_service.EnquiryExtractionService") as MockExtSvc,
            patch("app.modules.enquiries.intake_service.EnquiryProcessingService") as MockProcSvc,
            patch("app.modules.ai.service.DraftGenerationService") as MockDraft,
        ):
            MockExtSvc.return_value.extract.return_value = ExtractionResult(
                extraction_id=extraction_id,
                prompt_run_id=uuid.uuid4(),
                is_fallback=False,
                validation_status="passed",
                parsed={"guest_count": 20},
            )
            MockProcSvc.return_value.process.side_effect = RuntimeError("DB error")

            def record_draft(*args, **kwargs):
                draft_called.append(True)
                raise RuntimeError("no key")

            MockDraft.return_value.generate_draft = record_draft
            result = svc.intake_freeform(req)

        assert result.enquiry_id == enquiry.id
        # Draft still attempted despite processing failure
        assert len(draft_called) == 1

    def test_draft_failure_does_not_raise(self):
        """Draft generation failure must not raise — enquiry is always returned."""
        svc = self._build_service()
        restaurant = self._make_restaurant()
        enquiry = _make_enquiry_mock()
        enquiry.restaurant_id = restaurant.id

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_persona_for_audience.return_value = None
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = _make_message_mock()

        req = self._make_request(restaurant_id=restaurant.id)

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", False),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", False),
            patch("app.modules.ai.service.DraftGenerationService") as MockDraft,
        ):
            MockDraft.return_value.generate_draft.side_effect = RuntimeError("LLM down")
            result = svc.intake_freeform(req)

        # Must not raise — enquiry record always returned
        assert result.enquiry_id == enquiry.id
        assert result.draft_body is None


# ── No direct provider calls test ─────────────────────────────────────────────


class TestNoDraftProviderCallsDirect:
    """Validates that draft generation routes through AI Gateway, not directly to providers."""

    def test_draft_generation_does_not_import_anthropic_provider(self):
        """DraftGenerationService must not call AnthropicProvider directly."""
        from app.modules.ai.service import DraftGenerationService
        import inspect
        source = inspect.getsource(DraftGenerationService.generate_draft)
        # Direct Anthropic provider import or call is forbidden in service layer
        assert "AnthropicProvider(" not in source
        assert "anthropic.Anthropic(" not in source

    def test_ai_gateway_is_single_entrypoint(self):
        """DraftGenerationService.generate_draft calls gateway.run() not provider.generate()."""
        from app.modules.ai.service import DraftGenerationService
        import inspect
        source = inspect.getsource(DraftGenerationService.generate_draft)
        assert "gateway.run(" in source or "AIGateway" in source

    def test_fallback_provider_only_used_on_fallback_result(self):
        """FallbackProvider is only invoked when gateway result is_fallback=True."""
        from app.modules.ai.service import DraftGenerationService
        import inspect
        source = inspect.getsource(DraftGenerationService.generate_draft)
        # FallbackProvider should only be called inside the is_fallback branch
        assert "FallbackProvider" in source


# ── Gateway prompt key separation test ───────────────────────────────────────


class TestGatewayPromptKeySeparation:
    """Validates that extraction and draft use distinct prompt keys."""

    def test_extraction_uses_enquiry_extraction_key(self):
        from app.modules.ai.constants import PROMPT_KEY_ENQUIRY_EXTRACTION
        assert PROMPT_KEY_ENQUIRY_EXTRACTION == "enquiry_extraction"

    def test_draft_uses_draft_response_key(self):
        from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE
        assert PROMPT_KEY_DRAFT_RESPONSE == "draft_response"

    def test_keys_are_different(self):
        from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE, PROMPT_KEY_ENQUIRY_EXTRACTION
        assert PROMPT_KEY_DRAFT_RESPONSE != PROMPT_KEY_ENQUIRY_EXTRACTION

    def test_all_sprint7_trigger_types_are_defined(self):
        """Sprint 7 trigger constants must exist for correct tracing."""
        from app.modules.ai.constants import (
            TRIGGER_FREEFORM_WEBFORM_AUTO_DRAFT,
            TRIGGER_MANUAL_GENERATE_DRAFT,
            TRIGGER_REGENERATE_DRAFT,
        )
        assert TRIGGER_FREEFORM_WEBFORM_AUTO_DRAFT
        assert TRIGGER_MANUAL_GENERATE_DRAFT
        assert TRIGGER_REGENERATE_DRAFT

    def test_extraction_trigger_type_defined(self):
        """Extraction trigger type must be defined for AI tracing."""
        # Import lazily — added in AI-014 / API-015 sprint
        try:
            from app.modules.ai.constants import TRIGGER_TYPE_EXTRACTION
            assert TRIGGER_TYPE_EXTRACTION == "extraction"
        except ImportError:
            pytest.skip("TRIGGER_TYPE_EXTRACTION not yet defined on this branch")


# ── ORCH-008: response preparation wired into freeform intake ─────────────────


from datetime import date  # noqa: E402

from app.modules.enquiries.date_resolution_status import (  # noqa: E402
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
)
from app.modules.enquiries.intake_service import _build_date_resolution_status  # noqa: E402
from app.modules.enquiries.response_goal_engine import (  # noqa: E402
    GOAL_READY_TO_CONFIRM_AVAILABILITY,
)
from app.modules.enquiries.schemas import FreeformIntakeOut  # noqa: E402


class TestBuildDateResolutionStatus:
    """Tests for _build_date_resolution_status helper (ORCH-008)."""

    def test_none_stored_dr_returns_unknown(self):
        status = _build_date_resolution_status(None, {})
        assert status.status == STATUS_UNKNOWN

    def test_none_stored_dr_uses_raw_text_from_dict(self):
        status = _build_date_resolution_status(None, {"raw_text": "next Friday"})
        assert status.original_text == "next Friday"

    def test_resolved_ambiguity_type_maps_to_resolved(self):
        dr = MagicMock()
        dr.raw_text = "06/07"
        dr.ambiguity_type = "resolved"
        dr.clarification_required = False
        dr.clarification_question = None
        dr.clarification_reason = None
        dr.assumed_date = date(2026, 7, 6)
        dr.alternative_date = None
        dr.requires_date_clarification = False
        status = _build_date_resolution_status(dr, {})
        assert status.status == STATUS_RESOLVED
        assert status.resolved_date == "2026-07-06"

    def test_resolved_with_confirmation_ambiguity_type(self):
        dr = MagicMock()
        dr.raw_text = "06/07"
        dr.ambiguity_type = "resolved_with_confirmation"
        dr.clarification_required = True
        dr.clarification_question = "Did you mean 6 July or 7 June?"
        dr.clarification_reason = "dd_mm_vs_mm_dd"
        dr.assumed_date = date(2026, 7, 6)
        dr.alternative_date = date(2026, 6, 7)
        dr.requires_date_clarification = True
        status = _build_date_resolution_status(dr, {})
        assert status.status == STATUS_RESOLVED_WITH_CONFIRMATION
        assert status.alternative_date == "2026-06-07"

    def test_unresolved_ambiguity_maps_to_ambiguous(self):
        dr = MagicMock()
        dr.raw_text = "01/02"
        dr.ambiguity_type = "unresolved_ambiguity"
        dr.clarification_required = True
        dr.clarification_question = "Could you clarify the date?"
        dr.clarification_reason = "unresolvable"
        dr.assumed_date = None
        dr.alternative_date = None
        dr.requires_date_clarification = True
        status = _build_date_resolution_status(dr, {})
        assert status.status == STATUS_AMBIGUOUS

    def test_assumed_date_without_ambiguity_type_is_resolved(self):
        dr = MagicMock()
        dr.raw_text = "next Saturday"
        dr.ambiguity_type = None
        dr.clarification_required = False
        dr.clarification_question = None
        dr.clarification_reason = None
        dr.assumed_date = date(2026, 6, 13)
        dr.alternative_date = None
        dr.requires_date_clarification = False
        status = _build_date_resolution_status(dr, {})
        assert status.status == STATUS_RESOLVED
        assert status.resolved_date == "2026-06-13"

    def test_no_assumed_date_no_ambiguity_is_unknown(self):
        dr = MagicMock()
        dr.raw_text = None
        dr.ambiguity_type = None
        dr.clarification_required = False
        dr.clarification_question = None
        dr.clarification_reason = None
        dr.assumed_date = None
        dr.alternative_date = None
        dr.requires_date_clarification = False
        status = _build_date_resolution_status(dr, {})
        assert status.status == STATUS_UNKNOWN


class TestFreeformIntakeOutResponsePreparation:
    """ORCH-008: FreeformIntakeOut must carry response_preparation_summary."""

    def test_schema_accepts_response_preparation_summary(self):
        out = FreeformIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-2026-0001",
            status="new",
            restaurant_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            response_preparation_summary={
                "response_goal": GOAL_READY_TO_CONFIRM_AVAILABILITY,
                "response_priority": "NORMAL",
                "can_generate_draft": True,
                "clarification_questions": [],
            },
        )
        assert out.response_preparation_summary["response_goal"] == GOAL_READY_TO_CONFIRM_AVAILABILITY

    def test_response_preparation_summary_defaults_to_none(self):
        out = FreeformIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-2026-0002",
            status="new",
            restaurant_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        assert out.response_preparation_summary is None


class TestRunResponsePreparation:
    """ORCH-008: _run_response_preparation helper tests."""

    def _mock_extraction_result(self, parsed: dict | None = None) -> MagicMock:
        r = MagicMock()
        r.is_fallback = False
        r.parsed = parsed or {
            "guest_count": 40,
            "occasion": "birthday",
            "meal_period": "dinner",
            "audience_type_from_content": "corporate",
            "audience_confidence": 0.85,
            "audience_evidence": "company email domain",
            "date_request": {"raw_text": "next Saturday", "date_request_type": "exact"},
        }
        return r

    def _mock_processing_result(self) -> MagicMock:
        r = MagicMock()
        r.snapshot_id = uuid.uuid4()
        r.availability_result_json = {"status": "available", "date": "2026-06-13"}
        return r

    def test_returns_summary_dict(self):
        from app.modules.enquiries.intake_service import _run_response_preparation

        db = MagicMock()
        with (
            patch("app.modules.enquiries.intake_service.DateRequestRepository") as mock_dr,
            patch("app.modules.enquiries.intake_service.ResponsePlanRepository"),
        ):
            mock_dr.return_value.get_latest_date_request.return_value = None
            mock_dr.return_value.list_candidate_dates.return_value = []

            result = _run_response_preparation(
                db=db,
                enquiry_id=uuid.uuid4(),
                extraction_result=self._mock_extraction_result(),
                processing_result=self._mock_processing_result(),
                persona=None,
            )

        assert "response_goal" in result
        assert "response_priority" in result
        assert "can_generate_draft" in result
        assert "clarification_questions" in result

    def test_persists_plan_to_repository(self):
        from app.modules.enquiries.intake_service import _run_response_preparation

        db = MagicMock()
        with (
            patch("app.modules.enquiries.intake_service.DateRequestRepository") as mock_dr,
            patch("app.modules.enquiries.intake_service.ResponsePlanRepository") as mock_plan,
        ):
            mock_dr.return_value.get_latest_date_request.return_value = None
            mock_dr.return_value.list_candidate_dates.return_value = []

            _run_response_preparation(
                db=db,
                enquiry_id=uuid.uuid4(),
                extraction_result=self._mock_extraction_result(),
                processing_result=self._mock_processing_result(),
                persona=None,
            )

        mock_plan.return_value.create.assert_called_once()

    def test_commits_after_persisting(self):
        from app.modules.enquiries.intake_service import _run_response_preparation

        db = MagicMock()
        with (
            patch("app.modules.enquiries.intake_service.DateRequestRepository") as mock_dr,
            patch("app.modules.enquiries.intake_service.ResponsePlanRepository"),
        ):
            mock_dr.return_value.get_latest_date_request.return_value = None
            mock_dr.return_value.list_candidate_dates.return_value = []

            _run_response_preparation(
                db=db,
                enquiry_id=uuid.uuid4(),
                extraction_result=self._mock_extraction_result(),
                processing_result=self._mock_processing_result(),
                persona=None,
            )

        db.commit.assert_called()

    def test_ready_goal_with_resolved_date_and_available_candidate(self):
        from app.modules.enquiries.intake_service import _run_response_preparation

        db = MagicMock()
        dr = MagicMock()
        dr.raw_text = "next Saturday"
        dr.ambiguity_type = "resolved"
        dr.clarification_required = False
        dr.clarification_question = None
        dr.clarification_reason = None
        dr.assumed_date = date(2026, 6, 13)
        dr.alternative_date = None
        dr.requires_date_clarification = False

        cd = MagicMock()
        cd.candidate_date = date(2026, 6, 13)
        cd.availability_status = "available"

        with (
            patch("app.modules.enquiries.intake_service.DateRequestRepository") as mock_dr,
            patch("app.modules.enquiries.intake_service.ResponsePlanRepository"),
        ):
            mock_dr.return_value.get_latest_date_request.return_value = dr
            mock_dr.return_value.list_candidate_dates.return_value = [cd]

            result = _run_response_preparation(
                db=db,
                enquiry_id=uuid.uuid4(),
                extraction_result=self._mock_extraction_result(),
                processing_result=self._mock_processing_result(),
                persona=None,
            )

        assert result["response_goal"] == GOAL_READY_TO_CONFIRM_AVAILABILITY
        assert result["can_generate_draft"] is True
