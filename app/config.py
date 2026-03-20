"""Application configuration loaded from environment variables."""

from __future__ import annotations

import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default RSS sources (AI-heavy tech news). Override via NEWS_RSS_FEEDS JSON in .env.
DEFAULT_RSS_FEEDS: list[str] = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
    "https://openai.com/blog/rss.xml",
    "https://www.artificialintelligence-news.com/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
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
        35, ge=5, le=80, alias="MAX_CANDIDATES_FOR_OPENAI"
    )
    http_timeout_seconds: float = Field(20.0, ge=5.0, le=120.0, alias="HTTP_TIMEOUT_SECONDS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

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

    def resolved_feed_urls(self) -> list[str]:
        """Return configured feeds, or built-in defaults if none set."""
        return self.news_rss_feeds if self.news_rss_feeds else list(DEFAULT_RSS_FEEDS)
