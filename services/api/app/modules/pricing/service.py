"""Deterministic pricing rule service.

Recommendation logic is purely rule-based — no ML, no external API calls.
The recommendation algorithm:
1. Collect all active rules for the restaurant.
2. Filter to rules that match the given day_of_week, meal_period, and party_size.
3. Select the rule with the highest minimum_spend (most restrictive wins).
4. Return an explanation of which rules were considered and applied.
"""

import uuid

from sqlalchemy.orm import Session

from app.modules.pricing.models import PricingRule
from app.modules.pricing.repository import PricingRuleRepository
from app.modules.pricing.schemas import (
    AppliedRule,
    PricingRecommendationOut,
    PricingRecommendationRequest,
    PricingRuleCreate,
    PricingRuleUpdate,
)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class PricingRuleService:
    def __init__(self, db: Session) -> None:
        self._repo = PricingRuleRepository(db)

    def list_rules(
        self,
        restaurant_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 200,
    ) -> tuple[list[PricingRule], int]:
        items = self._repo.list(restaurant_id=restaurant_id, skip=skip, limit=limit)
        total = self._repo.count(restaurant_id=restaurant_id)
        return items, total

    def get_rule(self, rule_id: uuid.UUID) -> PricingRule | None:
        return self._repo.get_by_id(rule_id)

    def create_rule(self, data: PricingRuleCreate) -> PricingRule:
        return self._repo.create(data.model_dump())

    def update_rule(self, rule_id: uuid.UUID, data: PricingRuleUpdate) -> PricingRule | None:
        rule = self._repo.get_by_id(rule_id)
        if not rule:
            return None
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return rule
        return self._repo.update(rule, updates)

    def deactivate_rule(self, rule_id: uuid.UUID) -> PricingRule | None:
        rule = self._repo.get_by_id(rule_id)
        if not rule:
            return None
        return self._repo.deactivate(rule)

    def calculate_recommendation(
        self, request: PricingRecommendationRequest
    ) -> PricingRecommendationOut:
        """Calculate a deterministic minimum spend recommendation.

        Matches rules by day_of_week (None = all days), meal_period ('all' = all periods),
        and minimum_covers (None = any party size).  The highest matching minimum_spend wins.
        """
        all_rules = self._repo.list_active_for_restaurant(request.restaurant_id)
        matching: list[PricingRule] = []

        for rule in all_rules:
            # day_of_week: None means "applies every day"
            if rule.day_of_week is not None and rule.day_of_week != request.day_of_week:
                continue
            # meal_period: 'all' means "applies every period"
            if rule.meal_period != "all" and rule.meal_period != request.meal_period:
                continue
            # minimum_covers: None means "applies to any party size"
            if rule.minimum_covers is not None and request.party_size is not None:
                if request.party_size < rule.minimum_covers:
                    continue
            matching.append(rule)

        if not matching:
            return PricingRecommendationOut(
                recommended_minimum_spend=0.0,
                applied_rules=[],
                explanation="No pricing rules matched the given criteria.",
                confidence=1.0,
            )

        # Most restrictive rule wins
        best_rule = max(matching, key=lambda r: float(r.minimum_spend))
        day_name = DAY_NAMES[request.day_of_week]

        applied = [
            AppliedRule(
                rule_id=r.id,
                rule_name=r.name,
                minimum_spend=float(r.minimum_spend),
                reason=(
                    f"Matches {day_name}, {request.meal_period}"
                    + (
                        f", {request.party_size} covers"
                        if request.party_size
                        else ""
                    )
                ),
            )
            for r in matching
        ]

        explanation = (
            f"{len(matching)} rule(s) matched for {day_name} {request.meal_period}"
            + (f" ({request.party_size} covers)" if request.party_size else "")
            + f". Highest minimum spend applied: £{float(best_rule.minimum_spend):,.2f} "
            f"from rule '{best_rule.name}'."
        )

        return PricingRecommendationOut(
            recommended_minimum_spend=float(best_rule.minimum_spend),
            applied_rules=applied,
            explanation=explanation,
            confidence=1.0,
        )
