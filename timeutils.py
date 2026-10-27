"""Timezone helpers.

Every value stored by this project is intended to be Indian Standard Time.
The helpers below are deliberately tolerant: MySQL returns ``datetime``
objects, while earlier SQLite data and some test payloads contain strings.
"""

from datetime import date, datetime, time, timedelta, timezone

# Fixed offset avoids requiring the Windows IANA timezone database.
IST = timezone(timedelta(hours=5, minutes=30), 'IST')

DISPLAY_FORMAT = '%d %b %Y, %I:%M %p'
DATE_FORMAT = '%d %b %Y'
TIME_FORMAT = '%I:%M %p'

_DATE_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%d',
    '%d-%m-%Y %H:%M:%S',
    '%d-%m-%Y',
    '%d %b %Y, %I:%M %p',
    '%d %b %Y',
)


def now_ist() -> datetime:
    """Current time in IST, as a timezone-aware datetime."""
    return datetime.now(IST)


def now_ist_naive() -> datetime:
    """Current IST time without tzinfo, useful for MySQL DATETIME columns."""
    return now_ist().replace(tzinfo=None)


def as_ist(value) -> datetime | None:
    """Convert a date / datetime / string to a timezone-aware IST datetime."""
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value.astimezone(IST)

    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=IST)

    text = str(value).strip()
    if not text:
        return None

    if text.endswith('Z'):
        text = text[:-1] + '+00:00'

    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=IST)
        return parsed.astimezone(IST)
    except ValueError:
        pass

    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=IST)
        except ValueError:
            continue

    return None


def format_ist(value, fmt: str = DISPLAY_FORMAT, with_zone: bool = True) -> str:
    """Format a value for the UI, e.g. ``27 Oct 2026, 07:28 PM IST``."""
    parsed = as_ist(value)
    if parsed is None:
        return '-'
    rendered = parsed.strftime(fmt)
    return f'{rendered} IST' if with_zone else rendered


def format_date_ist(value) -> str:
    return format_ist(value, DATE_FORMAT, with_zone=False)


def format_time_ist(value) -> str:
    return format_ist(value, TIME_FORMAT, with_zone=False)


def format_json_ist(value) -> str:
    """Readable value returned by JSON APIs."""
    return format_ist(value)


def today_ist_iso() -> str:
    return now_ist().date().isoformat()
