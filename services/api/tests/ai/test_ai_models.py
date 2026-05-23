"""Model import and column tests for DATA-014 AI tables.

These tests do not require a live database — they verify that:
- all AI model classes import cleanly from app.modules.ai.models
- all expected AI tables appear in Base.metadata
- required columns exist on each model
"""


def test_ai_model_classes_importable() -> None:
    """All AI model classes can be imported."""
    from app.modules.ai.models import (  # noqa: F401
        AIPromptRun,
        AIPromptTemplate,
        AIPromptVersion,
        AITrainingExample,
        TenantPromptConfig,
    )


def test_ai_tables_in_metadata() -> None:
    """All five AI tables are registered in Base.metadata."""
    import app.db.models  # noqa: F401

    from app.db.base import Base

    ai_tables = {
        "ai_prompt_templates",
        "ai_prompt_versions",
        "tenant_prompt_configs",
        "ai_prompt_runs",
        "ai_training_examples",
    }
    actual = set(Base.metadata.tables.keys())
    missing = ai_tables - actual
    assert not missing, f"Missing AI tables: {missing}"


def test_ai_prompt_template_columns() -> None:
    """AIPromptTemplate has required columns."""
    from app.modules.ai.models import AIPromptTemplate

    cols = {c.name for c in AIPromptTemplate.__table__.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "key" in cols
    assert "is_system_default" in cols
    assert "is_active" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_ai_prompt_version_columns() -> None:
    """AIPromptVersion has required columns and is linked to templates."""
    from app.modules.ai.models import AIPromptVersion

    cols = {c.name for c in AIPromptVersion.__table__.columns}
    assert "id" in cols
    assert "prompt_template_id" in cols
    assert "version" in cols
    assert "status" in cols
    assert "system_prompt" in cols
    assert "user_prompt_template" in cols
    assert "model_provider" in cols
    assert "model_name" in cols


def test_tenant_prompt_config_columns() -> None:
    """TenantPromptConfig has required columns."""
    from app.modules.ai.models import TenantPromptConfig

    cols = {c.name for c in TenantPromptConfig.__table__.columns}
    assert "tenant_id" in cols
    assert "prompt_key" in cols
    assert "active_prompt_version_id" in cols
    assert "restaurant_id" in cols
    assert "persona_id" in cols
    assert "is_active" in cols


def test_ai_prompt_run_columns() -> None:
    """AIPromptRun has traceability columns including JSONB and fallback fields."""
    from app.modules.ai.models import AIPromptRun

    cols = {c.name for c in AIPromptRun.__table__.columns}
    assert "tenant_id" in cols
    assert "enquiry_id" in cols
    assert "prompt_version_id" in cols
    assert "rendered_system_prompt" in cols
    assert "rendered_user_prompt" in cols
    assert "input_payload" in cols
    assert "raw_response" in cols
    assert "parsed_response" in cols
    assert "validation_status" in cols
    assert "validation_errors" in cols
    assert "fallback_used" in cols
    assert "fallback_reason" in cols
    assert "latency_ms" in cols
    assert "status" in cols


def test_ai_training_example_columns() -> None:
    """AITrainingExample has required columns and links to prompt runs."""
    from app.modules.ai.models import AITrainingExample

    cols = {c.name for c in AITrainingExample.__table__.columns}
    assert "prompt_run_id" in cols
    assert "tenant_id" in cols
    assert "original_output" in cols
    assert "corrected_output" in cols
    assert "quality_rating" in cols
    assert "approved_for_training" in cols


def test_no_ml_fields_on_ai_models() -> None:
    """AI models do not contain ML pricing or scoring fields (POC guardrail)."""
    from app.modules.ai.models import AIPromptRun

    cols = {c.name for c in AIPromptRun.__table__.columns}
    assert "ml_score" not in cols
    assert "predicted_price" not in cols
