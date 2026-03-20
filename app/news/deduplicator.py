"""Remove duplicate and near-duplicate articles."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, datetime
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlparse

from app.news.parser import Article

_MIN = datetime.min.replace(tzinfo=UTC)

# Dropped from query strings when building a dedupe key (tracking / attribution).
_STRIP_QUERY_KEYS = frozenset(
    k.lower()
    for k in (
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "utm_reader",
        "utm_brand",
        "utm_marka",
        "ref",
        "referrer",
        "referral",
        "source",
        "src",
        "fbclid",
        "gclid",
        "dclid",
        "msclkid",
        "twclid",
        "li_fat_id",
        "mc_cid",
        "mc_eid",
        "igshid",
        "_ga",
        "mkt_tok",
        "affiliate_id",
    )
)


def _clean_query_pairs(query: str) -> list[tuple[str, str]]:
    return [
        (k, v)
        for k, v in parse_qsl(query, keep_blank_values=True)
        if k.lower() not in _STRIP_QUERY_KEYS
    ]


def _published_desc(a: Article) -> datetime:
    return a.published_at or _MIN


def _normalize_title(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _normalize_url(url: str) -> str:
    """
    Normalize URL for deduplication: host, path, and query without tracking params.

    Fragment is ignored. Trailing slashes on the path are removed.
    """
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    pairs = sorted(_clean_query_pairs(parsed.query))
    query = urlencode(pairs)
    if query:
        return f"{netloc}{path}?{query}"
    return f"{netloc}{path}"


def public_url_without_tracking(url: str) -> str:
    """Strip known tracking query params; keep scheme for links shown in the digest."""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    pairs = sorted(_clean_query_pairs(parsed.query))
    query = urlencode(pairs)
    prefix = f"{scheme}://{netloc}"
    if query:
        return f"{prefix}{path}?{query}"
    return f"{prefix}{path}"


def _netloc_matches_hints(url: str, hints: frozenset[str]) -> bool:
    if not hints or not url.strip():
        return False
    try:
        netloc = urlparse(url.strip()).netloc.lower().removeprefix("www.")
    except ValueError:
        return False
    if not netloc:
        return False
    return any(h in netloc for h in hints)


def _open_access_rank(art: Article, hints: frozenset[str]) -> int:
    """0 = on allowlist or hints disabled; 1 = not on allowlist when hints are set."""
    if not hints:
        return 0
    return 0 if _netloc_matches_hints(art.url, hints) else 1


def _title_dedup_sort_key(
    art: Article, *, open_access_hints: frozenset[str]
) -> tuple[bool, int, float, int]:
    """
    Prefer a likely non-paywall item, then an open-access allowlist host, then
    newer `published_at`, then a longer snippet.
    """
    pub = art.published_at or _MIN
    return (
        art.paywall_likely,
        _open_access_rank(art, open_access_hints),
        -pub.timestamp(),
        -len(art.snippet),
    )


def deduplicate_articles(
    articles: list[Article],
    *,
    title_similarity_threshold: float = 0.86,
    open_access_host_hints: frozenset[str] | None = None,
) -> list[Article]:
    """
    Drop URL duplicates and highly similar titles (same story, different outlets).

    For each unique normalized URL, the newest row is kept. For near-duplicate
    titles, one representative is kept: non-paywall first, then a host matching
    `open_access_host_hints` (when non-empty), then newer publish time, then
    longer snippet.
    """
    oa_hints = open_access_host_hints if open_access_host_hints is not None else frozenset()

    sorted_newest_first = sorted(articles, key=_published_desc, reverse=True)

    by_url: dict[str, Article] = {}
    for art in sorted_newest_first:
        key = _normalize_url(art.url)
        if key not in by_url:
            by_url[key] = replace(art, url=public_url_without_tracking(art.url))

    unique_by_url = list(by_url.values())
    unique_by_url.sort(
        key=lambda a: _title_dedup_sort_key(a, open_access_hints=oa_hints)
    )

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

    kept.sort(key=_published_desc, reverse=True)
    return kept
