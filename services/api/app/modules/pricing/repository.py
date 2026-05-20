import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pricing.models import PricingRule


class PricingRuleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list(
        self,
        restaurant_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 200,
        active_only: bool = True,
    ) -> list[PricingRule]:
        stmt = select(PricingRule)
        if active_only:
            stmt = stmt.where(PricingRule.is_active.is_(True))
        if restaurant_id:
            stmt = stmt.where(PricingRule.restaurant_id == restaurant_id)
        stmt = stmt.offset(skip).limit(limit).order_by(PricingRule.name)
        return list(self._db.scalars(stmt).all())

    def count(self, restaurant_id: uuid.UUID | None = None, active_only: bool = True) -> int:
        return len(self.list(restaurant_id=restaurant_id, skip=0, limit=10000, active_only=active_only))

    def get_by_id(self, rule_id: uuid.UUID) -> PricingRule | None:
        return self._db.get(PricingRule, rule_id)

    def create(self, data: dict[str, Any]) -> PricingRule:
        record = PricingRule(id=uuid.uuid4(), **data)
        self._db.add(record)
        self._db.flush()
        return record

    def update(self, rule: PricingRule, data: dict[str, Any]) -> PricingRule:
        for key, value in data.items():
            setattr(rule, key, value)
        self._db.flush()
        return rule

    def deactivate(self, rule: PricingRule) -> PricingRule:
        rule.is_active = False
        self._db.flush()
        return rule

    def list_active_for_restaurant(self, restaurant_id: uuid.UUID) -> list[PricingRule]:
        """Return all active rules for a restaurant, used for recommendation."""
        return self.list(restaurant_id=restaurant_id, skip=0, limit=1000, active_only=True)
