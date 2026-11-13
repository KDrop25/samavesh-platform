"""Compliance rules: status summary, overdue, and when a reminder is due. Pure functions."""

from datetime import date, timedelta

OPEN = ("partially", "not_compliant")  # statuses that still need work
REMINDER_DAYS = 7


def is_overdue(status: str, due_date: date, today: date) -> bool:
    return status in OPEN and due_date < today


def reminder_due(status: str, due_date: date, today: date, lead_days: int = REMINDER_DAYS) -> bool:
    """Remind from `lead_days` before the due date until it passes, while the item is still open."""
    return status in OPEN and today <= due_date <= today + timedelta(days=lead_days)


def summarise(items: list[tuple[str, date]], today: date) -> dict:
    """Counts per status, how many are overdue or due soon, and the compliance rate.
    'Not applicable' items are left out of the rate: they are not obligations here."""
    counts = {status: 0 for status in ("compliant", "partially", "not_compliant", "not_applicable")}
    for status, _ in items:
        counts[status] += 1
    applicable = len(items) - counts["not_applicable"]
    return {
        "total": len(items),
        **counts,
        "overdue": sum(is_overdue(status, due, today) for status, due in items),
        "due_soon": sum(reminder_due(status, due, today) for status, due in items),
        "percent_compliant": round(100 * counts["compliant"] / applicable) if applicable else None,
    }
