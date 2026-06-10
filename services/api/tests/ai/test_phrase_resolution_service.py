"""Tests for PhraseResolutionService (RESP-044).

Validates all five resolution levels:
  1. restaurant + persona
  2. restaurant default
  3. tenant + persona
  4. tenant default
  5. system default
  And NOT_FOUND when no phrase exists at any level.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.phrases.phrase_resolution_service import (
    LEVEL_NOT_FOUND,
    LEVEL_RESTAURANT_DEFAULT,
    LEVEL_RESTAURANT_PERSONA,
    LEVEL_SYSTEM_DEFAULT,
    LEVEL_TENANT_DEFAULT,
    LEVEL_TENANT_PERSONA,
    PhraseResolutionResult,
    PhraseResolutionService,
)


TENANT_ID = "default"
RESTAURANT_ID = uuid.uuid4()
PERSONA_ID = uuid.uuid4()
PHRASE_KEY = "availability_confirmed"


# ── PhraseResolutionResult ─────────────────────────────────────────────────────


def test_result_to_dict():
    r = PhraseResolutionResult(
        phrase_key=PHRASE_KEY,
        phrase_text="Some phrase",
        resolved_from=LEVEL_SYSTEM_DEFAULT,
        found=True,
    )
    d = r.to_dict()
    assert d["phrase_key"] == PHRASE_KEY
    assert d["resolved_from"] == LEVEL_SYSTEM_DEFAULT
    assert d["found"] is True


def test_result_not_found():
    r = PhraseResolutionResult(
        phrase_key=PHRASE_KEY,
        phrase_text="",
        resolved_from=LEVEL_NOT_FOUND,
        found=False,
    )
    assert r.found is False


# ── Level 1: restaurant + persona ─────────────────────────────────────────────


def test_resolves_level_1_restaurant_persona():
    db = MagicMock()

    def _mock_assignment(db, phrase_key, tenant_id, restaurant_id, persona_id):
        if restaurant_id == RESTAURANT_ID and persona_id == PERSONA_ID:
            return "Level 1 phrase"
        return None

    with patch.object(PhraseResolutionService, "_lookup_assignment", side_effect=_mock_assignment):
        result = PhraseResolutionService.resolve(
            db=db,
            phrase_key=PHRASE_KEY,
            tenant_id=TENANT_ID,
            restaurant_id=RESTAURANT_ID,
            persona_id=PERSONA_ID,
        )

    assert result.resolved_from == LEVEL_RESTAURANT_PERSONA
    assert result.phrase_text == "Level 1 phrase"
    assert result.found is True


# ── Level 2: restaurant default ───────────────────────────────────────────────


def test_resolves_level_2_restaurant_default():
    db = MagicMock()

    def _mock_assignment(db, phrase_key, tenant_id, restaurant_id, persona_id):
        if restaurant_id == RESTAURANT_ID and persona_id is None:
            return "Level 2 phrase"
        return None

    with patch.object(PhraseResolutionService, "_lookup_assignment", side_effect=_mock_assignment):
        result = PhraseResolutionService.resolve(
            db=db,
            phrase_key=PHRASE_KEY,
            tenant_id=TENANT_ID,
            restaurant_id=RESTAURANT_ID,
            persona_id=PERSONA_ID,
        )

    assert result.resolved_from == LEVEL_RESTAURANT_DEFAULT
    assert result.phrase_text == "Level 2 phrase"


# ── Level 3: tenant + persona ─────────────────────────────────────────────────


def test_resolves_level_3_tenant_persona():
    db = MagicMock()
    calls = []

    def _mock_assignment(db, phrase_key, tenant_id, restaurant_id, persona_id):
        calls.append((restaurant_id, persona_id))
        if restaurant_id is None and persona_id == PERSONA_ID:
            return "Level 3 phrase"
        return None

    with patch.object(PhraseResolutionService, "_lookup_assignment", side_effect=_mock_assignment):
        result = PhraseResolutionService.resolve(
            db=db,
            phrase_key=PHRASE_KEY,
            tenant_id=TENANT_ID,
            restaurant_id=RESTAURANT_ID,
            persona_id=PERSONA_ID,
        )

    assert result.resolved_from == LEVEL_TENANT_PERSONA
    assert result.phrase_text == "Level 3 phrase"


# ── Level 4: tenant default ───────────────────────────────────────────────────


def test_resolves_level_4_tenant_default():
    db = MagicMock()

    def _mock_assignment(db, phrase_key, tenant_id, restaurant_id, persona_id):
        if restaurant_id is None and persona_id is None:
            return "Level 4 phrase"
        return None

    with patch.object(PhraseResolutionService, "_lookup_assignment", side_effect=_mock_assignment):
        result = PhraseResolutionService.resolve(
            db=db,
            phrase_key=PHRASE_KEY,
            tenant_id=TENANT_ID,
            restaurant_id=RESTAURANT_ID,
            persona_id=PERSONA_ID,
        )

    assert result.resolved_from == LEVEL_TENANT_DEFAULT
    assert result.phrase_text == "Level 4 phrase"


# ── Level 5: system default ───────────────────────────────────────────────────


def test_resolves_level_5_system_default():
    db = MagicMock()

    with patch.object(PhraseResolutionService, "_lookup_assignment", return_value=None), \
         patch.object(PhraseResolutionService, "_lookup_system_default", return_value="System default phrase"):
        result = PhraseResolutionService.resolve(
            db=db,
            phrase_key=PHRASE_KEY,
            tenant_id=TENANT_ID,
            restaurant_id=RESTAURANT_ID,
            persona_id=PERSONA_ID,
        )

    assert result.resolved_from == LEVEL_SYSTEM_DEFAULT
    assert result.phrase_text == "System default phrase"


# ── Not found ─────────────────────────────────────────────────────────────────


def test_not_found_when_all_levels_empty():
    db = MagicMock()

    with patch.object(PhraseResolutionService, "_lookup_assignment", return_value=None), \
         patch.object(PhraseResolutionService, "_lookup_system_default", return_value=None):
        result = PhraseResolutionService.resolve(
            db=db,
            phrase_key="completely_unknown_key",
            tenant_id=TENANT_ID,
        )

    assert result.found is False
    assert result.resolved_from == LEVEL_NOT_FOUND
    assert result.phrase_text == ""


# ── No restaurant/persona — skips levels 1-3 ──────────────────────────────────


def test_skips_restaurant_levels_when_no_restaurant():
    db = MagicMock()
    call_log: list[tuple] = []

    def _mock_assignment(db, phrase_key, tenant_id, restaurant_id, persona_id):
        call_log.append((restaurant_id, persona_id))
        return None

    with patch.object(PhraseResolutionService, "_lookup_assignment", side_effect=_mock_assignment), \
         patch.object(PhraseResolutionService, "_lookup_system_default", return_value=None):
        PhraseResolutionService.resolve(
            db=db,
            phrase_key=PHRASE_KEY,
            tenant_id=TENANT_ID,
            restaurant_id=None,
            persona_id=None,
        )

    # Only tenant default check (restaurant=None, persona=None)
    assert len(call_log) == 1
    assert call_log[0] == (None, None)
