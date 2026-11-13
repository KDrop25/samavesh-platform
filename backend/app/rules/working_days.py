"""Working-day arithmetic for the grievance escalation rule. Pure functions."""

from datetime import date, timedelta

DEFAULT_WEEKDAYS = [0, 1, 2, 3, 4, 5]  # Monday-Saturday (Monday = 0), common in Indian colleges
DEFAULT_ESCALATION_DAYS = 15


def working_days_between(start: date, end: date, weekdays: set[int], holidays: set[date]) -> int:
    """Working days after `start`, up to and including `end`. The start day itself is not counted,
    so a grievance taken under review on Monday has been under review for 1 working day on Tuesday."""
    count, day = 0, start
    while day < end:
        day += timedelta(days=1)
        if day.weekday() in weekdays and day not in holidays:
            count += 1
    return count


def escalation_due(under_review_since: date, today: date, limit: int, weekdays: set[int], holidays: set[date]) -> bool:
    """True once a grievance has been under review for MORE than `limit` working days."""
    return working_days_between(under_review_since, today, weekdays, holidays) > limit
