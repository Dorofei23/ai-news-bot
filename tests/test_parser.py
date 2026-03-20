"""Tests for RSS entry normalization."""

from __future__ import annotations

from app.news.parser import Article, entry_to_article


def test_entry_prefers_longer_content_block_over_short_summary() -> None:
    """Many feeds put a teaser in summary and full HTML in `content`."""
    entry = {
        "title": "Test",
        "link": "https://example.com/p/1",
        "summary": "<p>Short.</p>",
        "content": [{"type": "text/html", "value": "<p>" + ("word " * 50) + "</p>"}],
    }
    art = entry_to_article(entry, feed_title="Blog", feed_href="https://example.com/")
    assert art is not None
    assert "word" in art.snippet
    assert len(art.snippet) > len("Short.")


def test_paywall_flag_matches_host_hint() -> None:
    hints = frozenset({"nytimes.com", "ft.com"})
    entry = {
        "title": "NYT story",
        "link": "https://www.nytimes.com/2026/03/20/technology/foo.html",
        "description": "Teaser",
    }
    art = entry_to_article(
        entry,
        feed_title="NYT",
        feed_href="https://nytimes.com",
        paywall_host_hints=hints,
    )
    assert art is not None
    assert art.paywall_likely is True

    open_entry = {
        "title": "Open",
        "link": "https://example.org/post",
        "description": "Hi",
    }
    open_art = entry_to_article(
        open_entry,
        feed_title="Ex",
        feed_href="https://example.org",
        paywall_host_hints=hints,
    )
    assert open_art is not None
    assert open_art.paywall_likely is False


def test_article_paywall_defaults_false() -> None:
    a = Article(
        title="t",
        source="s",
        url="https://x.com",
        published_at=None,
        snippet="",
    )
    assert a.paywall_likely is False
