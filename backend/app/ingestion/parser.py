"""Pure parsing/validation for Boston 311 records.

Kept free of I/O so it can be unit-tested without a network or database. Maps a
raw CKAN record dict to the kwargs for ``Historical311Request``.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

# Boston 311 datetime format, e.g. "2025-01-02 09:50:33.593". Some rows omit
# fractional seconds; we try a couple of formats.
_DT_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class ParseError(ValueError):
    """Raised when a record cannot be parsed into a valid historical row."""


def _clean(value: Any) -> str | None:
    """Normalize a raw cell to a trimmed string or None."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def parse_datetime(value: Any) -> dt.datetime | None:
    """Parse a Boston 311 timestamp into a naive datetime, or None."""
    s = _clean(value)
    if s is None:
        return None
    for fmt in _DT_FORMATS:
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_float(value: Any) -> float | None:
    s = _clean(value)
    if s is None:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    # Guard against obviously invalid coordinates (0,0 placeholders etc.).
    return f


def parse_record(raw: dict[str, Any], *, city_id: int) -> dict[str, Any]:
    """Convert a raw CKAN 311 record into Historical311Request kwargs.

    Raises ParseError if the natural key (case_enquiry_id) is missing, since it
    is required for idempotent upserts.
    """
    case_id = _clean(raw.get("case_enquiry_id"))
    if not case_id:
        raise ParseError("missing case_enquiry_id")

    lat = parse_float(raw.get("latitude"))
    lng = parse_float(raw.get("longitude"))
    # Treat (0,0) and out-of-range values as missing.
    if lat is not None and not (-90 <= lat <= 90):
        lat = None
    if lng is not None and not (-180 <= lng <= 180):
        lng = None
    if lat == 0.0 and lng == 0.0:
        lat = lng = None

    return {
        "city_id": city_id,
        "case_enquiry_id": case_id,
        "case_title": _clean(raw.get("case_title")),
        "subject": _clean(raw.get("subject")),
        "reason": _clean(raw.get("reason")),
        "case_type": _clean(raw.get("type")),
        "queue": _clean(raw.get("queue")),
        "department": _clean(raw.get("department")),
        "case_status": _clean(raw.get("case_status")),
        "closure_reason": _clean(raw.get("closure_reason")),
        "neighborhood": _clean(raw.get("neighborhood")),
        "location_street": _clean(raw.get("location_street_name"))
        or _clean(raw.get("location")),
        "zipcode": _clean(raw.get("location_zipcode")),
        "latitude": lat,
        "longitude": lng,
        "opened_at": parse_datetime(raw.get("open_dt")),
        "closed_at": parse_datetime(raw.get("closed_dt")),
        "source": "boston_311",
    }
