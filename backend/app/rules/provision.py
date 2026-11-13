"""Provision rules: when an accommodation is overdue, and planned vs delivered in a term.

Pure functions over dates - no database - so each rule can be tested directly.
"""

from datetime import date, timedelta


def next_due(interval_days: int | None, plan_start: date, last_provided: date | None) -> date | None:
    """The date by which the next provision is expected. Standing arrangements have none."""
    if not interval_days:
        return None
    return (last_provided or plan_start) + timedelta(days=interval_days)


def is_overdue(interval_days: int | None, plan_start: date, last_provided: date | None, today: date) -> bool:
    """Overdue = the plan's interval has passed since the last provision (or since the plan started)."""
    due = next_due(interval_days, plan_start, last_provided)
    return due is not None and due < today


def planned_in_term(
    interval_days: int | None, active_from: date, active_to: date | None, term_start: date, term_end: date
) -> int | None:
    """How many provisions the plan calls for inside a term: days the item was active within
    the term, divided by its interval. None for standing arrangements (nothing to count)."""
    if not interval_days:
        return None
    start = max(active_from, term_start)
    end = min(active_to or term_end, term_end)
    if end < start:
        return 0
    return ((end - start).days + 1) // interval_days
