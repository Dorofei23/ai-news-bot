"""Time helpers for article windows and display strings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """Current time in UTC with tzinfo."""
    return datetime.now(tz=UTC)


def window_start(lookback_hours: int) -> datetime:
    """Start of the collection window (UTC)."""
    return utc_now() - timedelta(hours=lookback_hours)


def format_digest_date(timezone_name: str) -> str:
    """Human-readable date in the configured timezone for the digest header."""
    tz = ZoneInfo(timezone_name)
    return datetime.now(tz=tz).strftime("%B %d, %Y")


def parse_published(value: datetime | None) -> datetime | None:
    """Ensure published datetimes are timezone-aware (assume UTC if naive)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
