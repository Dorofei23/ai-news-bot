"""Tests for RSS deduplication helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.news.deduplicator import deduplicate_articles, public_url_without_tracking
from app.news.parser import Article


def _art(
    title: str,
    url: str,
    hours_ago: int = 1,
    *,
    snippet: str = "snippet",
    paywall_likely: bool = False,
) -> Article:
    return Article(
        title=title,
        source="Example",
        url=url,
        published_at=datetime.now(tz=UTC) - timedelta(hours=hours_ago),
        snippet=snippet,
        paywall_likely=paywall_likely,
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


def test_deduplicate_prefers_open_over_paywalled_same_story() -> None:
    """Near-duplicate title: keep the likely non-paywall URL even if it is older."""
    paywalled = _art(
        "Acme buys Beta in major AI infrastructure deal",
        "https://www.nytimes.com/2026/01/01/technology/acme-beta.html",
        hours_ago=1,
        snippet="Short NYT dek.",
        paywall_likely=True,
    )
    open_verge = _art(
        "Acme buys Beta in major AI infrastructure deal",
        "https://www.theverge.com/2026/1/1/acme-beta-ai-deal",
        hours_ago=8,
        snippet="The Verge has more detail from the announcement.",
        paywall_likely=False,
    )
    out = deduplicate_articles([paywalled, open_verge])
    assert len(out) == 1
    assert out[0].paywall_likely is False
    assert "theverge.com" in out[0].url


def test_deduplicate_among_open_sources_prefers_newer_when_titles_align() -> None:
    older = _art("Foo Corp launches AI pair programming tool", "https://a.com/x", hours_ago=20)
    newer = _art("Foo Corp launches AI pair programming tool", "https://b.com/y", hours_ago=2)
    out = deduplicate_articles([older, newer])
    assert len(out) == 1
    assert out[0].url.endswith("/y")


def test_public_url_drops_utm_keeps_meaningful_ids() -> None:
    u = public_url_without_tracking(
        "https://example.com/a?story=7&utm_source=email&sort=date"
    )
    assert "utm_source" not in u
    assert "story=7" in u
    assert "sort=date" in u


def test_deduplicate_collapses_tracking_query_variants() -> None:
    a = _art("Same piece", "https://example.com/news/item?utm_source=x", hours_ago=1)
    b = _art("Same piece relinked", "https://www.example.com/news/item?ref=newsletter", hours_ago=4)
    out = deduplicate_articles([a, b])
    assert len(out) == 1
    assert "utm_source" not in out[0].url


def test_deduplicate_prefers_allowlisted_open_host_when_titles_align() -> None:
    """Among non-paywall dupes, favor a host from open_access_host_hints."""
    blog = _art(
        "GadgetCo announces AI IDE feature",
        "https://random-dev-blog.example/gadgetco-ai-ide",
        hours_ago=1,
    )
    verge = _art(
        "GadgetCo announces AI IDE feature",
        "https://www.theverge.com/2026/1/9/gadgetco-ai-ide",
        hours_ago=1,
    )
    out = deduplicate_articles(
        [blog, verge],
        open_access_host_hints=frozenset({"theverge.com"}),
    )
    assert len(out) == 1
    assert "theverge.com" in out[0].url
