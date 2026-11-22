from datetime import datetime, timedelta
import logging
import re
from typing import Optional

from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

DATE_REGEX = re.compile(
    r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}|\d{1,2}-[A-Za-z]{3}-\d{4})\b",
    re.IGNORECASE,
)
ISO_DATE_REGEX = re.compile(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$")
RELATIVE_PERIOD_REGEX = re.compile(
    r"\b(1|2|3|4|5|10)\s*(y|yr|yrs|year|years|mo|mos|month|months)\b",
    re.IGNORECASE,
)
DATE_RANGE_PHRASE_REGEX = re.compile(
    r"\b(?:between|from\s+.*\s+to|202[0-9])\b",
    re.IGNORECASE,
)


def _parse_single_date(token: str) -> Optional[datetime]:
    cleaned = token.strip()
    iso_match = ISO_DATE_REGEX.match(cleaned)
    if iso_match:
        year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        return datetime(year, month, day)
    return date_parser.parse(cleaned, fuzzy=True, dayfirst=False)


def has_date_reference(user_query: str) -> bool:
    """Returns True only when the query contains explicit dates, relative periods, or date-range phrasing."""
    if not user_query:
        return False
    return bool(
        DATE_REGEX.search(user_query)
        or RELATIVE_PERIOD_REGEX.search(user_query)
        or DATE_RANGE_PHRASE_REGEX.search(user_query)
    )


def extract_and_normalize_dates(user_query: str) -> tuple[Optional[str], Optional[str]]:
    """Extracts and validates chronological start/end dates (YYYY-MM-DD) from a query."""
    if not user_query:
        return None, None

    matches = DATE_REGEX.findall(user_query)
    if len(matches) >= 2:
        parsed_dts: list[datetime] = []
        for match_str in matches[:2]:
            try:
                parsed_dts.append(_parse_single_date(match_str))
            except Exception:
                continue

        if len(parsed_dts) >= 2:
            start_dt, end_dt = parsed_dts[0], parsed_dts[1]
            if start_dt > end_dt:
                logger.warning("Invalid date range: start (%s) is after end (%s)", start_dt, end_dt)
                return None, None
            return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

    query_lower = user_query.lower()
    today = datetime.today()
    rel_match = RELATIVE_PERIOD_REGEX.search(query_lower)
    if rel_match and "between" not in query_lower and "from" not in query_lower:
        num = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        days = num * 365 if unit.startswith("y") else num * 30
        start_dt = today - timedelta(days=days)
        return start_dt.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    return None, None


def has_explicit_date_range(user_query: str) -> bool:
    """Returns True if a valid start and end date are extracted from the query."""
    start_date, end_date = extract_and_normalize_dates(user_query)
    return start_date is not None and end_date is not None