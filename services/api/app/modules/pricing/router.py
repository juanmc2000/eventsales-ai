import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.pricing.schemas import (
    PricingRecommendationOut,
    PricingRecommendationRequest,
    PricingRuleCreate,
    PricingRuleListOut,
    PricingRuleOut,
    PricingRuleUpdate,
)
from app.modules.pricing.service import PricingRuleService

router = APIRouter(prefix="/api/v1/pricing-rules", tags=["pricing-rules"])


def get_service(db: Session = Depends(get_db)) -> PricingRuleService:
    return PricingRuleService(db)


@router.get("", response_model=PricingRuleListOut)
def list_pricing_rules(
    restaurant_id: uuid.UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
    service: PricingRuleService = Depends(get_service),
) -> PricingRuleListOut:
    items, total = service.list_rules(restaurant_id=restaurant_id, skip=skip, limit=limit)
    return PricingRuleListOut(items=items, total=total)


@router.get("/recommend", response_model=PricingRecommendationOut)
def get_recommendation(
    restaurant_id: uuid.UUID = Query(...),
    day_of_week: int = Query(..., ge=0, le=6, description="0=Monday … 6=Sunday"),
    meal_period: str = Query(..., description="breakfast / lunch / dinner"),
    party_size: int | None = Query(default=None, ge=1),
    service: PricingRuleService = Depends(get_service),
) -> PricingRecommendationOut:
    request = PricingRecommendationRequest(
        restaurant_id=restaurant_id,
        day_of_week=day_of_week,
        meal_period=meal_period,
        party_size=party_size,
    )
    return service.calculate_recommendation(request)


@router.get("/{rule_id}", response_model=PricingRuleOut)
def get_pricing_rule(
    rule_id: uuid.UUID,
    service: PricingRuleService = Depends(get_service),
) -> PricingRuleOut:
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    return rule


@router.post("", response_model=PricingRuleOut, status_code=201)
def create_pricing_rule(
    data: PricingRuleCreate,
    service: PricingRuleService = Depends(get_service),
) -> PricingRuleOut:
    return service.create_rule(data)


@router.patch("/{rule_id}", response_model=PricingRuleOut)
def update_pricing_rule(
    rule_id: uuid.UUID,
    data: PricingRuleUpdate,
    service: PricingRuleService = Depends(get_service),
) -> PricingRuleOut:
    rule = service.update_rule(rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    return rule


@router.delete("/{rule_id}", response_model=PricingRuleOut)
def deactivate_pricing_rule(
    rule_id: uuid.UUID,
    service: PricingRuleService = Depends(get_service),
) -> PricingRuleOut:
    rule = service.deactivate_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    return rule
