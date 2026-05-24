"""Constants for the AI module.

Centralises prompt keys, model identifiers, schema names, and
other stable identifiers used across the AI Gateway.
"""

# ── Prompt keys ─────────────────────────────────────────────────────────────
# These are the stable logical identifiers used to look up prompts in the
# registry and in tenant_prompt_configs rows.

PROMPT_KEY_DRAFT_RESPONSE = "draft_response"
PROMPT_KEY_ENQUIRY_EXTRACTION = "enquiry_extraction"
PROMPT_KEY_MISSING_INFO_REQUEST = "missing_info_request"
PROMPT_KEY_FOLLOW_UP_RESPONSE = "follow_up_response"
PROMPT_KEY_AVAILABILITY_ALTERNATIVE = "availability_alternative_response"

ALL_PROMPT_KEYS = {
    PROMPT_KEY_DRAFT_RESPONSE,
    PROMPT_KEY_ENQUIRY_EXTRACTION,
    PROMPT_KEY_MISSING_INFO_REQUEST,
    PROMPT_KEY_FOLLOW_UP_RESPONSE,
    PROMPT_KEY_AVAILABILITY_ALTERNATIVE,
}

# ── Model identifiers ────────────────────────────────────────────────────────

MODEL_PROVIDER_ANTHROPIC = "anthropic"
MODEL_PROVIDER_FALLBACK = "fallback"

# Default model for draft generation — fast and cost-efficient for POC
MODEL_CLAUDE_HAIKU = "claude-haiku-4-5-20251001"
# Higher-capability model for complex or structured outputs
MODEL_CLAUDE_SONNET = "claude-sonnet-4-6"

DEFAULT_DRAFT_MODEL = MODEL_CLAUDE_HAIKU
DEFAULT_DRAFT_MAX_TOKENS = 800
DEFAULT_DRAFT_TEMPERATURE = "0.7"

# ── Output schema names ──────────────────────────────────────────────────────
# Logical names for declared output schemas.  Matched by the AI Gateway
# when validating parsed LLM responses.

SCHEMA_DRAFT_EMAIL_OUTPUT = "DraftEmailOutput"
SCHEMA_ENQUIRY_EXTRACTION_OUTPUT = "EnquiryExtractionOutput"

# ── Prompt categories ────────────────────────────────────────────────────────

CATEGORY_DRAFT_GENERATION = "draft_generation"
CATEGORY_INTAKE = "intake"
CATEGORY_FOLLOW_UP = "follow_up"

# ── Prompt version statuses ──────────────────────────────────────────────────

VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_ACTIVE = "active"
VERSION_STATUS_ARCHIVED = "archived"

# ── AI run statuses ──────────────────────────────────────────────────────────

RUN_STATUS_SUCCESS = "success"
RUN_STATUS_FALLBACK = "fallback"
RUN_STATUS_ERROR = "error"

# ── Validation statuses ──────────────────────────────────────────────────────

VALIDATION_PENDING = "pending"
VALIDATION_PASSED = "passed"          # JSON parsed + schema validated
VALIDATION_FAILED = "invalid"         # JSON parsed but schema validation failed
VALIDATION_PARSE_ERROR = "parse_error"  # Response could not be parsed as JSON
VALIDATION_SKIPPED = "skipped"        # No schema declared or fallback run
VALIDATION_FALLBACK_VALID = "fallback_valid"     # Fallback + schema OK
VALIDATION_FALLBACK_INVALID = "fallback_invalid"  # Fallback + schema failed

# ── Trigger types ────────────────────────────────────────────────────────────

TRIGGER_TYPE_DRAFT_GENERATION = "draft_generation"
TRIGGER_TYPE_INTAKE = "intake"
TRIGGER_TYPE_EXTRACTION = "extraction"

# Draft generation trigger sub-types
TRIGGER_MANUAL_GENERATE_DRAFT = "manual_generate_draft"
TRIGGER_REGENERATE_DRAFT = "regenerate_draft"
TRIGGER_WEBFORM_INTAKE_AUTO_DRAFT = "webform_intake_auto_draft"
TRIGGER_FREEFORM_WEBFORM_AUTO_DRAFT = "freeform_webform_auto_draft"

# Extraction trigger sub-types (API-014)
TRIGGER_FREEFORM_WEBFORM_SUBMITTED = "freeform_webform_submitted"
TRIGGER_INBOUND_EMAIL_RECEIVED = "inbound_email_received"
TRIGGER_MANUAL_REEXTRACT = "manual_reextract"

TRIGGER_SOURCE_API = "api"
TRIGGER_SOURCE_CELERY = "celery"
TRIGGER_SOURCE_WEBFORM = "webform"
