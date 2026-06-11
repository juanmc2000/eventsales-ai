"""Customer-facing date formatter (RESP-057).

Converts ISO 8601 date strings to natural hospitality-email date format.

Examples::

    format_event_date("2026-06-12") → "Friday, 12 June 2026"
    format_event_date("2026-07-04") → "Saturday, 4 July 2026"

Design rules:
- Day-of-week first, then day number (no ordinal suffix), then month name, then year.
- No leading zero on day number.
- Returns the original string unchanged if it is not a recognised ISO date, so that
  callers do not need to guard against non-date strings.
- Returns an empty string if the input is None or empty.
"""

from __future__ import annotations

import re
from datetime import date

# Lightweight pre-check before calling date.fromisoformat — avoids exceptions on
# strings that clearly are not ISO dates (e.g. "the 12th of June", "TBC").
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def format_event_date(iso_date: str | None) -> str:
    """Convert an ISO date string to natural hospitality-email format.

    Args:
        iso_date: ISO 8601 date string (``"YYYY-MM-DD"``) or ``None``.

    Returns:
        Natural-language date string, e.g. ``"Friday, 12 June 2026"``.
        Returns the original string unchanged if it is not a valid ISO date.
        Returns an empty string when ``iso_date`` is ``None`` or empty.
    """
    if not iso_date:
        return ""
    if not _ISO_DATE_RE.match(iso_date):
        return iso_date  # pass through non-ISO strings unchanged
    try:
        d = date.fromisoformat(iso_date)
    except ValueError:
        return iso_date  # invalid date value — pass through unchanged
    return d.strftime(f"%A, {d.day} %B %Y")


def format_event_date_list(iso_dates: list[str] | None) -> list[str]:
    """Format a list of ISO date strings to natural format.

    Each element is passed through ``format_event_date``; non-ISO strings are
    returned unchanged.  ``None`` input returns an empty list.
    """
    if not iso_dates:
        return []
    return [format_event_date(d) for d in iso_dates]
