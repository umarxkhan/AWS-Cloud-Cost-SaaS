"""Input validation helpers.

Prevents unbounded queries (date-range cap), malformed account ids, and
invalid date/month strings. All raise ApiError -> HTTP 400.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from .errors import bad_request

_ACCOUNT_ID_RE = re.compile(r"^\d{12}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

MAX_DAILY_RANGE_DAYS = 31


def validate_account_id(raw) -> str:
    s = str(raw).strip() if raw is not None else ""
    if not _ACCOUNT_ID_RE.match(s):
        raise bad_request(
            "aws_account_id must be a 12-digit AWS account id",
            "INVALID_ACCOUNT_ID",
        )
    return s


def parse_date(raw, field: str = "date") -> date:
    s = str(raw).strip() if raw is not None else ""
    if not _DATE_RE.match(s):
        raise bad_request(f"{field} must be in YYYY-MM-DD format", "INVALID_DATE")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise bad_request(f"{field} must be a valid calendar date", "INVALID_DATE")


def parse_month(raw: str) -> str:
    s = str(raw).strip() if raw is not None else ""
    if not _MONTH_RE.match(s):
        raise bad_request("month must be in YYYY-MM format", "INVALID_MONTH")
    year, mon = s.split("-")
    if not (1 <= int(mon) <= 12):
        raise bad_request("month must be a valid YYYY-MM value", "INVALID_MONTH")
    # Ensure the year parses as an integer to reject garbage.
    int(year)
    return f"{year}-{mon}"


def validate_date_range(start_raw, end_raw, max_days: int = MAX_DAILY_RANGE_DAYS) -> tuple[str, str]:
    start = parse_date(start_raw, "start")
    end = parse_date(end_raw, "end")
    if start > end:
        raise bad_request("start must be on or before end", "INVALID_RANGE")
    if (end - start).days + 1 > max_days:
        raise bad_request(f"date range must not exceed {max_days} days", "RANGE_TOO_LARGE")
    return start.isoformat(), end.isoformat()


def month_range(month: str) -> tuple[str, str]:
    """Return (first_day, last_day) ISO strings for a YYYY-MM month."""
    year, mon = (int(p) for p in month.split("-"))
    import calendar

    last = calendar.monthrange(year, mon)[1]
    return f"{month}-01", f"{month}-{last:02d}"
