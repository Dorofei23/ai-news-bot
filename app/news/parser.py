"""Normalize raw RSS entries into a common article schema."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from app.utils.time_utils import parse_published


@dataclass(frozen=True, slots=True)
class Article:
    """Normalized news item used across the pipeline."""

    title: str
    source: str
    url: str
    published_at: datetime | None
    snippet: str


def _parse_published_from_entry(entry: dict[str, Any]) -> datetime | None:
    """Best-effort published time from a feedparser entry."""
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct:
        try:
            return datetime(
                struct.tm_year,
                struct.tm_mon,
                struct.tm_mday,
                struct.tm_hour,
                struct.tm_min,
                struct.tm_sec,
                tzinfo=UTC,
            )
        except (TypeError, ValueError):
            pass

    for key in ("published", "updated"):
        raw = entry.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                return parse_published(parsedate_to_datetime(raw))
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def entry_to_article(entry: dict[str, Any], *, feed_title: str, feed_href: str) -> Article | None:
    """Map a single feedparser entry dict to Article, or None if unusable."""
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or entry.get("id") or "").strip()
    if not title or not link:
        return None

    summary = entry.get("summary") or entry.get("description") or ""
    if isinstance(summary, str):
        snippet = summary.strip()
    else:
        snippet = str(summary).strip()

    if len(snippet) > 1200:
        snippet = snippet[:1200] + "…"

    published = parse_published(_parse_published_from_entry(entry))
    source = (feed_title or feed_href or "Unknown").strip()
    return Article(
        title=title,
        source=source,
        url=link,
        published_at=published,
        snippet=snippet,
    )
