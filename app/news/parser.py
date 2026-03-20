"""Normalize raw RSS entries into a common article schema."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

from app.utils.time_utils import parse_published


_SNIPPET_MAX_CHARS = 8000


def _strip_html(text: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", plain).strip()


def _snippet_strings_from_value(raw: Any) -> list[str]:
    """Normalize feedparser string or detail dict (`value` key) to text chunks."""
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    if isinstance(raw, dict):
        val = raw.get("value")
        if isinstance(val, str) and val.strip():
            return [val.strip()]
    return []


def _collect_snippet_parts(entry: dict[str, Any]) -> list[str]:
    """Gather raw HTML/text chunks from common RSS/Atom fields (deduped, stable order)."""
    out: list[str] = []
    seen: set[str] = set()
    for key in ("summary", "summary_detail", "description"):
        for s in _snippet_strings_from_value(entry.get(key)):
            if s not in seen:
                seen.add(s)
                out.append(s)
    content = entry.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                val = block.get("value")
                if isinstance(val, str) and val.strip():
                    s = val.strip()
                    if s not in seen:
                        seen.add(s)
                        out.append(s)
    return out


def _best_snippet_text(entry: dict[str, Any], *, max_chars: int = _SNIPPET_MAX_CHARS) -> str:
    """Prefer the longest field — often `content:encoded` holds full article text from the feed."""
    parts = _collect_snippet_parts(entry)
    if not parts:
        return ""
    raw = max(parts, key=len)
    text = _strip_html(raw)
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def _url_matches_paywall_hint(url: str, hints: frozenset[str]) -> bool:
    if not hints or not url.strip():
        return False
    try:
        netloc = urlparse(url.strip()).netloc.lower().removeprefix("www.")
    except ValueError:
        return False
    if not netloc:
        return False
    return any(h in netloc for h in hints)


@dataclass(frozen=True, slots=True)
class Article:
    """Normalized news item used across the pipeline."""

    title: str
    source: str
    url: str
    published_at: datetime | None
    snippet: str
    paywall_likely: bool = False


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


def entry_to_article(
    entry: dict[str, Any],
    *,
    feed_title: str,
    feed_href: str,
    paywall_host_hints: frozenset[str] = frozenset(),
) -> Article | None:
    """Map a single feedparser entry dict to Article, or None if unusable."""
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or entry.get("id") or "").strip()
    if not title or not link:
        return None

    snippet = _best_snippet_text(entry)

    published = parse_published(_parse_published_from_entry(entry))
    source = (feed_title or feed_href or "Unknown").strip()
    return Article(
        title=title,
        source=source,
        url=link,
        published_at=published,
        snippet=snippet,
        paywall_likely=_url_matches_paywall_hint(link, paywall_host_hints),
    )
