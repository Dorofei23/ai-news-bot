"""Download and parse RSS feeds into Article objects."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import feedparser
import httpx

from app.config import Settings
from app.news.parser import Article, entry_to_article
from app.utils.retry import retry_call
from app.utils.time_utils import window_start

logger = logging.getLogger(__name__)


def _normalize_feed_url(url: str) -> str:
    """Use scheme + netloc + path for light dedupe of feed URLs."""
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def fetch_articles_from_feeds(settings: Settings) -> list[Article]:
    """
    Fetch all configured feeds and return articles within the lookback window.

    Failures for individual feeds are logged and skipped so one bad URL does not
    stop the entire digest.
    """
    feeds = [_normalize_feed_url(u) for u in settings.resolved_feed_urls()]
    feeds = list(dict.fromkeys(feeds))  # preserve order, unique
    window = window_start(settings.lookback_hours)
    articles: list[Article] = []
    paywall_hints = settings.resolved_paywall_host_hints()

    timeout = httpx.Timeout(settings.http_timeout_seconds)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for feed_url in feeds:
            try:
                batch = _fetch_single_feed(client, feed_url, window, paywall_hints)
                articles.extend(batch)
                logger.info("Fetched %s articles from %s", len(batch), feed_url)
            except Exception:
                logger.exception("Failed to fetch or parse feed: %s", feed_url)

    return articles


def _fetch_single_feed(
    client: httpx.Client,
    feed_url: str,
    window_start_utc,
    paywall_host_hints: frozenset[str],
) -> list[Article]:
    """HTTP GET + feedparser for one feed URL."""

    def _get() -> httpx.Response:
        return client.get(feed_url, headers={"User-Agent": "ai-news-telegram-bot/0.1"})

    response = retry_call(_get, attempts=3, exceptions=(httpx.HTTPError, httpx.TransportError))
    response.raise_for_status()

    parsed = feedparser.parse(response.content)
    feed_title = ""
    if parsed.feed:
        feed_title = (parsed.feed.get("title") or "").strip()

    # Root `href` is missing for some feeds; fall back to channel link or request URL.
    href = (parsed.get("href") or "").strip()
    if not href and parsed.feed:
        href = (parsed.feed.get("link") or "").strip()
    if not href:
        href = feed_url

    out: list[Article] = []
    for entry in parsed.entries or []:
        if not isinstance(entry, dict):
            continue
        art = entry_to_article(
            entry,
            feed_title=feed_title,
            feed_href=href,
            paywall_host_hints=paywall_host_hints,
        )
        if art is None:
            continue
        if art.published_at is not None and art.published_at < window_start_utc:
            continue
        out.append(art)
    return out
