"""Central model registry.

Import this module to ensure all SQLAlchemy models are registered
against Base.metadata before Alembic migrations or schema inspection.

Add a new import here whenever a new DATA-xxx issue adds a model.
"""

# ruff: noqa: F401

from app.modules.restaurants.models import (
    Restaurant,
    Room,
    RoomAvailability,
    RestaurantPolicyFAQ,
    RoomPolicyFAQ,
)
from app.modules.personas.models import Persona, RestaurantPersona
from app.modules.pricing.models import PricingRule
from app.modules.enquiries.models import (
    Enquiry,
    EnquiryMessage,
    EnquiryExtraction,
    EnquiryProcessingSnapshot,
    EnquiryDateRequest,
    EnquiryCandidateDate,
    EnquiryResponsePlan,
)
from app.modules.email.models import EmailEvent
from app.modules.calendar.models import CalendarEvent
from app.modules.insights.models import DemandEvent, InsightSnapshot
from app.modules.ai.models import (
    AIPromptTemplate,
    AIPromptVersion,
    TenantPromptConfig,
    AIPromptRun,
    AIPromptRunReview,
    AIPromptExperiment,
    AIPromptExperimentRun,
    AITrainingExample,
)
from app.modules.phrases.models import (
    ResponsePhraseTemplate,
    ResponsePhraseVersion,
    ResponsePhraseAssignment,
)

__all__ = [
    "Restaurant",
    "Room",
    "RoomAvailability",
    "RestaurantPolicyFAQ",
    "RoomPolicyFAQ",
    "Persona",
    "RestaurantPersona",
    "PricingRule",
    "Enquiry",
    "EnquiryMessage",
    "EnquiryExtraction",
    "EnquiryProcessingSnapshot",
    "EnquiryDateRequest",
    "EnquiryCandidateDate",
    "EnquiryResponsePlan",
    "EmailEvent",
    "CalendarEvent",
    "DemandEvent",
    "InsightSnapshot",
    "AIPromptTemplate",
    "AIPromptVersion",
    "TenantPromptConfig",
    "AIPromptRun",
    "AIPromptRunReview",
    "AIPromptExperiment",
    "AIPromptExperimentRun",
    "AITrainingExample",
    "ResponsePhraseTemplate",
    "ResponsePhraseVersion",
    "ResponsePhraseAssignment",
]
