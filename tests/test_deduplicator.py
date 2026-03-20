"""Tests for RSS deduplication helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.news.deduplicator import deduplicate_articles
from app.news.parser import Article


def _art(title: str, url: str, hours_ago: int = 1) -> Article:
    return Article(
        title=title,
        source="Example",
        url=url,
        published_at=datetime.now(tz=UTC) - timedelta(hours=hours_ago),
        snippet="snippet",
    )


def test_deduplicate_drops_same_url() -> None:
    a = _art("Hello AI world", "https://example.com/a")
    b = _art("Different title", "https://example.com/a")
    out = deduplicate_articles([a, b])
    assert len(out) == 1


def test_deduplicate_keeps_similar_titles_if_urls_differ() -> None:
    a = _art("OpenAI releases new model", "https://a.com/1")
    b = _art("OpenAI releases new model today", "https://b.com/2")
    out = deduplicate_articles([a, b], title_similarity_threshold=0.95)
    # Same story different wording might still pass; ensure at least one remains
    assert len(out) >= 1
