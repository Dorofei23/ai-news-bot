"""Remove duplicate and near-duplicate articles."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse

from app.news.parser import Article

_MIN = datetime.min.replace(tzinfo=UTC)


def _published_desc(a: Article) -> datetime:
    return a.published_at or _MIN


def _normalize_title(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{netloc}{path}"


def deduplicate_articles(
    articles: list[Article],
    *,
    title_similarity_threshold: float = 0.86,
) -> list[Article]:
    """
    Drop URL duplicates and highly similar titles (same story, different outlets).

    When duplicates are detected, the article with the more recent `published_at`
    is kept; if equal, the first in the sorted order wins.
    """
    sorted_newest_first = sorted(articles, key=_published_desc, reverse=True)

    by_url: dict[str, Article] = {}
    for art in sorted_newest_first:
        key = _normalize_url(art.url)
        if key not in by_url:
            by_url[key] = art

    unique_by_url = list(by_url.values())
    unique_by_url.sort(key=_published_desc, reverse=True)

    kept: list[Article] = []
    seen_norms: list[str] = []

    for art in unique_by_url:
        norm = _normalize_title(art.title)
        duplicate = any(
            SequenceMatcher(a=norm, b=prev).ratio() >= title_similarity_threshold
            for prev in seen_norms
        )
        if duplicate:
            continue
        seen_norms.append(norm)
        kept.append(art)

    return kept
