"""Tests for AUTO-004 — review_metadata column on EnquiryMessage.

Verifies that:
- review_metadata column exists on EnquiryMessage model and is nullable
- update_message_review_metadata returns None for unknown message_id
- update_message_review_metadata persists all expected fields on the message
- All six canonical fields are written: review_state, validation_status,
  validation_blockers, auto_send_allowed, auto_send_blockers, generation_path
- Both "llm" and "deterministic" generation_path values are accepted
- A second call overwrites (not merges) the previous value
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

import app.db.models  # noqa: F401 — registers all SQLAlchemy models

from app.modules.enquiries.repository import EnquiryRepository


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_repo() -> tuple[EnquiryRepository, MagicMock]:
    db = MagicMock()
    repo = EnquiryRepository(db)
    return repo, db


def _make_message(review_metadata: dict | None = None) -> MagicMock:
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.review_metadata = review_metadata
    return msg


def _llm_review_meta(
    *,
    review_state: str = "HUMAN_REVIEW_REQUIRED",
    validation_status: str = "passed",
    validation_blockers: list | None = None,
    auto_send_allowed: bool = False,
    auto_send_blockers: list | None = None,
    generation_path: str = "llm",
) -> dict:
    return {
        "review_state": review_state,
        "validation_status": validation_status,
        "validation_blockers": validation_blockers or [],
        "auto_send_allowed": auto_send_allowed,
        "auto_send_blockers": auto_send_blockers or [],
        "generation_path": generation_path,
    }


# ── Unit tests: update_message_review_metadata ────────────────────────────────


class TestUpdateMessageReviewMetadata:
    """EnquiryRepository.update_message_review_metadata — contract tests."""

    def test_returns_none_when_message_not_found(self) -> None:
        repo, db = _make_repo()
        db.get.return_value = None
        result = repo.update_message_review_metadata(uuid.uuid4(), _llm_review_meta())
        assert result is None

    def test_returns_message_when_found(self) -> None:
        repo, db = _make_repo()
        msg = _make_message()
        db.get.return_value = msg
        result = repo.update_message_review_metadata(msg.id, _llm_review_meta())
        assert result is msg

    def test_sets_review_metadata_on_message(self) -> None:
        repo, db = _make_repo()
        msg = _make_message()
        db.get.return_value = msg
        meta = _llm_review_meta()
        repo.update_message_review_metadata(msg.id, meta)
        assert msg.review_metadata == meta

    def test_calls_flush_after_update(self) -> None:
        repo, db = _make_repo()
        msg = _make_message()
        db.get.return_value = msg
        repo.update_message_review_metadata(msg.id, _llm_review_meta())
        db.flush.assert_called_once()

    def test_looks_up_message_by_correct_id(self) -> None:
        repo, db = _make_repo()
        from app.modules.enquiries.models import EnquiryMessage
        msg = _make_message()
        db.get.return_value = msg
        target_id = uuid.uuid4()
        repo.update_message_review_metadata(target_id, _llm_review_meta())
        db.get.assert_called_once_with(EnquiryMessage, target_id)

    def test_overwrites_previous_review_metadata(self) -> None:
        """A second call must replace the entire dict, not merge."""
        repo, db = _make_repo()
        msg = _make_message(review_metadata={"review_state": "old"})
        db.get.return_value = msg
        new_meta = _llm_review_meta(review_state="VALIDATION_FAILED")
        repo.update_message_review_metadata(msg.id, new_meta)
        assert msg.review_metadata == new_meta
        assert msg.review_metadata["review_state"] == "VALIDATION_FAILED"


# ── Field-level contract tests ────────────────────────────────────────────────


class TestReviewMetadataFields:
    """Verify all six canonical fields round-trip through the repository method."""

    def _persist_and_get(self, meta: dict) -> dict:
        repo, db = _make_repo()
        msg = _make_message()
        db.get.return_value = msg
        repo.update_message_review_metadata(msg.id, meta)
        return msg.review_metadata

    def test_review_state_field_persisted(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(review_state="AUTO_SEND_ELIGIBLE"))
        assert meta["review_state"] == "AUTO_SEND_ELIGIBLE"

    def test_validation_status_passed(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(validation_status="passed"))
        assert meta["validation_status"] == "passed"

    def test_validation_status_failed(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(validation_status="failed"))
        assert meta["validation_status"] == "failed"

    def test_validation_blockers_empty_list(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(validation_blockers=[]))
        assert meta["validation_blockers"] == []

    def test_validation_blockers_non_empty(self) -> None:
        blockers = ["missing_copy_block", "forbidden_topic"]
        meta = self._persist_and_get(_llm_review_meta(validation_blockers=blockers))
        assert meta["validation_blockers"] == blockers

    def test_auto_send_allowed_false(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(auto_send_allowed=False))
        assert meta["auto_send_allowed"] is False

    def test_auto_send_allowed_true(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(auto_send_allowed=True))
        assert meta["auto_send_allowed"] is True

    def test_auto_send_blockers_persisted(self) -> None:
        blockers = ["goal_not_in_allowlist"]
        meta = self._persist_and_get(_llm_review_meta(auto_send_blockers=blockers))
        assert meta["auto_send_blockers"] == blockers

    def test_generation_path_llm(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(generation_path="llm"))
        assert meta["generation_path"] == "llm"

    def test_generation_path_deterministic(self) -> None:
        meta = self._persist_and_get(_llm_review_meta(generation_path="deterministic"))
        assert meta["generation_path"] == "deterministic"


# ── Model attribute tests ─────────────────────────────────────────────────────


class TestEnquiryMessageReviewMetadataColumn:
    """Verify the review_metadata column exists and has nullable=True semantics."""

    def test_review_metadata_attribute_exists_on_model(self) -> None:
        from app.modules.enquiries.models import EnquiryMessage
        assert hasattr(EnquiryMessage, "review_metadata")

    def test_review_metadata_is_nullable(self) -> None:
        """Column must accept None — pre-AUTO-004 messages have no review metadata."""
        from app.modules.enquiries.models import EnquiryMessage
        col = EnquiryMessage.__table__.c["review_metadata"]
        assert col.nullable is True

    def test_review_metadata_column_type_is_json(self) -> None:
        """Column must be JSON to support arbitrary structured metadata dicts."""
        from app.modules.enquiries.models import EnquiryMessage
        from sqlalchemy.dialects.postgresql import JSON
        col = EnquiryMessage.__table__.c["review_metadata"]
        assert isinstance(col.type, JSON)
