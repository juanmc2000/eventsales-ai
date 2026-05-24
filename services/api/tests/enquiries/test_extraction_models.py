"""Tests for EnquiryExtraction and EnquiryProcessingSnapshot models and schemas."""

import uuid
from datetime import datetime, timezone


def test_enquiry_extraction_model_importable() -> None:
    from app.modules.enquiries.models import EnquiryExtraction

    assert EnquiryExtraction.__tablename__ == "enquiry_extractions"


def test_enquiry_processing_snapshot_model_importable() -> None:
    from app.modules.enquiries.models import EnquiryProcessingSnapshot

    assert EnquiryProcessingSnapshot.__tablename__ == "enquiry_processing_snapshots"


def test_enquiry_extraction_columns() -> None:
    from app.modules.enquiries.models import EnquiryExtraction

    col_names = {c.name for c in EnquiryExtraction.__table__.columns}
    assert "id" in col_names
    assert "tenant_id" in col_names
    assert "enquiry_id" in col_names
    assert "source_message_id" in col_names
    assert "prompt_run_id" in col_names
    assert "extracted_json" in col_names
    assert "normalized_json" in col_names
    assert "missing_fields" in col_names
    assert "confidence_json" in col_names
    assert "created_at" in col_names


def test_enquiry_processing_snapshot_columns() -> None:
    from app.modules.enquiries.models import EnquiryProcessingSnapshot

    col_names = {c.name for c in EnquiryProcessingSnapshot.__table__.columns}
    assert "id" in col_names
    assert "tenant_id" in col_names
    assert "enquiry_id" in col_names
    assert "extraction_id" in col_names
    assert "pricing_rule_id" in col_names
    assert "availability_result_json" in col_names
    assert "room_suitability_json" in col_names
    assert "pricing_result_json" in col_names
    assert "missing_fields_json" in col_names
    assert "recommended_action" in col_names
    assert "created_at" in col_names


def test_enquiry_extraction_out_schema_valid() -> None:
    from app.modules.enquiries.schemas import EnquiryExtractionOut

    now = datetime.now(timezone.utc)
    obj = EnquiryExtractionOut(
        id=uuid.uuid4(),
        enquiry_id=uuid.uuid4(),
        source_message_id=None,
        prompt_run_id=None,
        extracted_json={"occasion": "birthday", "guest_count": 20},
        normalized_json={"occasion": "birthday", "guest_count": 20},
        missing_fields=["event_date"],
        confidence_json={"occasion": 0.95, "guest_count": 0.90},
        created_at=now,
    )
    assert obj.missing_fields == ["event_date"]
    assert obj.extracted_json["occasion"] == "birthday"


def test_enquiry_extraction_out_schema_nullable_fields() -> None:
    from app.modules.enquiries.schemas import EnquiryExtractionOut

    now = datetime.now(timezone.utc)
    obj = EnquiryExtractionOut(
        id=uuid.uuid4(),
        enquiry_id=uuid.uuid4(),
        created_at=now,
    )
    assert obj.source_message_id is None
    assert obj.prompt_run_id is None
    assert obj.extracted_json is None
    assert obj.missing_fields is None


def test_enquiry_processing_snapshot_out_schema_valid() -> None:
    from app.modules.enquiries.schemas import EnquiryProcessingSnapshotOut

    now = datetime.now(timezone.utc)
    extraction_id = uuid.uuid4()
    obj = EnquiryProcessingSnapshotOut(
        id=uuid.uuid4(),
        enquiry_id=uuid.uuid4(),
        extraction_id=extraction_id,
        pricing_rule_id=None,
        availability_result_json={"status": "available", "date": "2026-12-25"},
        room_suitability_json={"room_id": str(uuid.uuid4()), "room_name": "The Grand Ballroom"},
        pricing_result_json={"minimum_spend": 1500.0, "rule_name": "Weekend Evening"},
        missing_fields_json=[],
        recommended_action="send_draft",
        created_at=now,
    )
    assert obj.recommended_action == "send_draft"
    assert obj.extraction_id == extraction_id


def test_enquiry_processing_snapshot_out_schema_nullable_fields() -> None:
    from app.modules.enquiries.schemas import EnquiryProcessingSnapshotOut

    now = datetime.now(timezone.utc)
    obj = EnquiryProcessingSnapshotOut(
        id=uuid.uuid4(),
        enquiry_id=uuid.uuid4(),
        extraction_id=uuid.uuid4(),
        created_at=now,
    )
    assert obj.pricing_rule_id is None
    assert obj.availability_result_json is None
    assert obj.recommended_action is None


def test_recommended_action_values() -> None:
    """recommended_action must be one of the documented values when set."""
    from app.modules.enquiries.schemas import EnquiryProcessingSnapshotOut

    now = datetime.now(timezone.utc)
    valid_actions = ["send_draft", "request_more_info", "flag_for_review"]
    for action in valid_actions:
        obj = EnquiryProcessingSnapshotOut(
            id=uuid.uuid4(),
            enquiry_id=uuid.uuid4(),
            extraction_id=uuid.uuid4(),
            recommended_action=action,
            created_at=now,
        )
        assert obj.recommended_action == action


def test_extraction_registered_in_central_registry() -> None:
    from app.db.models import EnquiryExtraction, EnquiryProcessingSnapshot  # noqa: F401

    from app.db.base import Base

    assert "enquiry_extractions" in Base.metadata.tables
    assert "enquiry_processing_snapshots" in Base.metadata.tables
