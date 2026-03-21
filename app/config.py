"""Application configuration loaded from environment variables."""

from __future__ import annotations

import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default RSS sources: AI news, vendor updates, dev tooling changelogs, frontend feeds.
# Override via NEWS_RSS_FEEDS JSON in .env.
DEFAULT_RSS_FEEDS: list[str] = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
    "https://openai.com/blog/rss.xml",
    "https://openai.com/news/rss.xml",
    "https://www.artificialintelligence-news.com/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://blog.google/innovation-and-ai/technology/ai/rss/",
    "https://deepmind.google/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://github.blog/feed/",
    "https://cursor.com/changelog/rss.xml",
    "https://blogs.nvidia.com/feed/",
    "https://www.docker.com/feed/",
    "https://developers.cloudflare.com/changelog/rss/index.xml",
    "https://blog.packagist.com/rss/",
    "https://blog.jetbrains.com/feed/",
    "https://react.dev/rss.xml",
    "https://web.dev/feed.xml",
    "https://javascriptweekly.com/rss/",
    "https://blog.expo.dev/feed",
    "https://developer.chrome.com/blog/feed.xml",
]

# Host substrings (lowercase) for paywall labeling. Override with PAYWALL_HOST_HINTS;
# set to JSON [] to disable tagging.
DEFAULT_PAYWALL_HOST_HINTS: list[str] = [
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "economist.com",
    "bloomberg.com",
    "washingtonpost.com",
    "theinformation.com",
    "newyorker.com",
    "theatlantic.com",
    "telegraph.co.uk",
    "thetimes.co.uk",
]

# Prefer these hosts when titles are near-duplicates (tie-break after paywall flag).
# Override with OPEN_ACCESS_HOST_HINTS; JSON [] disables the bonus for everyone.
DEFAULT_OPEN_ACCESS_HOST_HINTS: list[str] = [
    "theverge.com",
    "techcrunch.com",
    "arstechnica.com",
    "theregister.com",
    "github.blog",
    "openai.com",
    "react.dev",
    "web.dev",
    "developer.chrome.com",
    "blog.google",
    "developers.googleblog.com",
    "blog.expo.dev",
    "mozilla.org",
    "hacks.mozilla.org",
    "increment.com",
    "engineering.fb.com",
    "netflixtechblog.com",
    "huggingface.co",
    "deepmind.google",
    "cursor.com",
    "docker.com",
    "cloudflare.com",
    "jetbrains.com",
    "packagist.org",
]


class Settings(BaseSettings):
    """Runtime settings for the bot and digest pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(..., alias="TELEGRAM_CHAT_ID")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")

    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")

    digest_hour: int = Field(8, ge=0, le=23, alias="DIGEST_HOUR")
    digest_minute: int = Field(0, ge=0, le=59, alias="DIGEST_MINUTE")
    timezone: str = Field("UTC", alias="TIMEZONE")

    news_rss_feeds: list[str] = Field(default_factory=list, alias="NEWS_RSS_FEEDS")

    lookback_hours: int = Field(36, ge=1, le=168, alias="LOOKBACK_HOURS")
    max_items_in_digest: int = Field(8, ge=1, le=15, alias="MAX_ITEMS_IN_DIGEST")
    max_candidates_for_openai: int = Field(
        50, ge=5, le=120, alias="MAX_CANDIDATES_FOR_OPENAI"
    )
    http_timeout_seconds: float = Field(20.0, ge=5.0, le=120.0, alias="HTTP_TIMEOUT_SECONDS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    paywall_host_hints: list[str] | None = Field(default=None, alias="PAYWALL_HOST_HINTS")
    open_access_host_hints: list[str] | None = Field(
        default=None, alias="OPEN_ACCESS_HOST_HINTS"
    )

    @field_validator("news_rss_feeds", mode="before")
    @classmethod
    def _parse_feed_list(cls, v: Any) -> list[str]:
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                return [p.strip() for p in s.split(",") if p.strip()]
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
            raise ValueError("NEWS_RSS_FEEDS must be a JSON array of URL strings")
        raise TypeError("Invalid type for NEWS_RSS_FEEDS")

    @field_validator("paywall_host_hints", mode="before")
    @classmethod
    def _parse_paywall_host_hints(cls, v: Any) -> list[str] | None:
        if v is None or v == "":
            return None
        if isinstance(v, list):
            return [str(x).strip().lower() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                return [p.strip().lower() for p in s.split(",") if p.strip()]
            if isinstance(parsed, list):
                return [str(x).strip().lower() for x in parsed if str(x).strip()]
            raise ValueError("PAYWALL_HOST_HINTS must be a JSON array of host substring strings")
        raise TypeError("Invalid type for PAYWALL_HOST_HINTS")

    @field_validator("open_access_host_hints", mode="before")
    @classmethod
    def _parse_open_access_host_hints(cls, v: Any) -> list[str] | None:
        if v is None or v == "":
            return None
        if isinstance(v, list):
            return [str(x).strip().lower() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                return [p.strip().lower() for p in s.split(",") if p.strip()]
            if isinstance(parsed, list):
                return [str(x).strip().lower() for x in parsed if str(x).strip()]
            raise ValueError(
                "OPEN_ACCESS_HOST_HINTS must be a JSON array of host substring strings"
            )
        raise TypeError("Invalid type for OPEN_ACCESS_HOST_HINTS")

    def resolved_feed_urls(self) -> list[str]:
        """Return configured feeds, or built-in defaults if none set."""
        return self.news_rss_feeds if self.news_rss_feeds else list(DEFAULT_RSS_FEEDS)

    def resolved_paywall_host_hints(self) -> frozenset[str]:
        """Hosts used to flag likely subscription-only articles (best-effort, not legal advice)."""
        if self.paywall_host_hints is None:
            return frozenset(h.lower() for h in DEFAULT_PAYWALL_HOST_HINTS)
        return frozenset(self.paywall_host_hints)

    def resolved_open_access_host_hints(self) -> frozenset[str]:
        """Hosts favored when picking among same-story candidates (after paywall, before recency)."""
        if self.open_access_host_hints is None:
            return frozenset(h.lower() for h in DEFAULT_OPEN_ACCESS_HOST_HINTS)
        return frozenset(self.open_access_host_hints)
