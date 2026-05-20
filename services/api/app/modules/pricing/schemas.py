import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PricingRuleBase(BaseModel):
    name: str = Field(..., max_length=255)
    restaurant_id: uuid.UUID
    # day_of_week: 0=Mon … 6=Sun; None = applies every day
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    # breakfast / lunch / dinner / all
    meal_period: str = Field(default="all", max_length=20)
    minimum_spend: float = Field(default=0.0, ge=0)
    minimum_covers: int | None = Field(default=None, ge=1)
    notes: str | None = None


class PricingRuleCreate(PricingRuleBase):
    pass


class PricingRuleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    meal_period: str | None = Field(default=None, max_length=20)
    minimum_spend: float | None = Field(default=None, ge=0)
    minimum_covers: int | None = Field(default=None, ge=1)
    notes: str | None = None


class PricingRuleOut(PricingRuleBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PricingRuleListOut(BaseModel):
    items: list[PricingRuleOut]
    total: int


# ── Recommendation ────────────────────────────────────────────────────────────


class PricingRecommendationRequest(BaseModel):
    restaurant_id: uuid.UUID
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday … 6=Sunday")
    meal_period: str = Field(..., description="breakfast / lunch / dinner")
    party_size: int | None = Field(default=None, ge=1)


class AppliedRule(BaseModel):
    rule_id: uuid.UUID
    rule_name: str
    minimum_spend: float
    reason: str


class PricingRecommendationOut(BaseModel):
    recommended_minimum_spend: float
    applied_rules: list[AppliedRule]
    explanation: str
    # Placeholder for future confidence scoring — always 1.0 for deterministic rules
    confidence: float = 1.0
