import logging
from datetime import datetime

import recurrent
from dateutil.rrule import rrulestr


def to_rrule(text: str) -> str | None:
    """Convert natural language recurrence to RRULE string. Returns None if unparseable."""
    r = recurrent.RecurringEvent()
    result = r.parse(text)
    if isinstance(result, str) and result.startswith("RRULE"):
        return result
    logging.warning(f"Could not parse recur pattern: {text!r}")
    return None


def next_occurrence_after(rrule: str, after: datetime) -> datetime | None:
    """Return the next occurrence of an RRULE after a given datetime."""
    try:
        return rrulestr(rrule, dtstart=after).after(after)
    except Exception as e:
        logging.warning(f"Failed to compute next occurrence: {e}")
        return None


def most_recent_occurrence(rrule: str, before: datetime) -> datetime | None:
    """Return the most recent past occurrence of an RRULE before a given datetime."""
    try:
        return rrulestr(rrule, dtstart=datetime(2020, 1, 1)).before(before)
    except Exception as e:
        logging.warning(f"Failed to compute most recent occurrence: {e}")
        return None
