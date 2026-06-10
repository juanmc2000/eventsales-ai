"""Alternative Date Strategy enum (RESP-050).

Defines the strategy used by AlternativeDateService to select candidate dates
when a requested booking date is unavailable.

Only ADJACENT_DATES is implemented in this sprint.  The remaining values are
future-ready stubs that reserve namespace for later sprints.

Usage::

    from app.modules.enquiries.alternative_date_strategy import AlternativeDateStrategy

    result = AlternativeDateService.find_alternatives(
        ...,
        strategy=AlternativeDateStrategy.ADJACENT_DATES,
    )
"""

from __future__ import annotations

from enum import Enum


class AlternativeDateStrategy(str, Enum):
    """Strategy for generating alternative-date candidates.

    Values:
        ADJACENT_DATES:         Check D-1 and D+1 (implemented).
        SAME_WEEKDAY:           Same weekday in adjacent weeks (future).
        EARLIEST_AVAILABLE:     First available date after requested date (future).
        ALL_AVAILABLE_IN_RANGE: All available dates within a search window (future).
        REVENUE_OPTIMISED:      Rank by revenue potential (future).
    """

    ADJACENT_DATES = "adjacent_dates"
    SAME_WEEKDAY = "same_weekday"
    EARLIEST_AVAILABLE = "earliest_available"
    ALL_AVAILABLE_IN_RANGE = "all_available_in_range"
    REVENUE_OPTIMISED = "revenue_optimised"
