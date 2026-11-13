"""Date rules. Pure functions: no database, no request."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Kolkata")  # "today" for an Indian institution, wherever the server runs


def today() -> date:
    return datetime.now(LOCAL_TZ).date()


def age_on(date_of_birth: date, on: date) -> int:
    had_birthday = (on.month, on.day) >= (date_of_birth.month, date_of_birth.day)
    return on.year - date_of_birth.year - (0 if had_birthday else 1)


def is_minor(date_of_birth: date | None, on: date) -> bool:
    """Under 18. An unknown date of birth is treated as a minor, so consent is never skipped."""
    return date_of_birth is None or age_on(date_of_birth, on) < 18
