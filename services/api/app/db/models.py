"""Central model registry.

Import this module to ensure all SQLAlchemy models are registered
against Base.metadata before Alembic migrations or schema inspection.

Add a new import here whenever a new DATA-xxx issue adds a model.
"""

# ruff: noqa: F401

from app.modules.restaurants.models import Restaurant, Room, RoomAvailability
from app.modules.personas.models import Persona, RestaurantPersona
from app.modules.pricing.models import PricingRule
from app.modules.enquiries.models import (
    Enquiry,
    EnquiryMessage,
    EnquiryExtraction,
    EnquiryProcessingSnapshot,
    EnquiryDateRequest,
    EnquiryCandidateDate,
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

__all__ = [
    "Restaurant",
    "Room",
    "RoomAvailability",
    "Persona",
    "RestaurantPersona",
    "PricingRule",
    "Enquiry",
    "EnquiryMessage",
    "EnquiryExtraction",
    "EnquiryProcessingSnapshot",
    "EnquiryDateRequest",
    "EnquiryCandidateDate",
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
]
