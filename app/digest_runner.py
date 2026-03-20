"""End-to-end digest pipeline: fetch → dedupe → rank → OpenAI → format → send."""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot
from telegram.error import TelegramError

from app.config import Settings
from app.news.deduplicator import deduplicate_articles
from app.news.fetcher import fetch_articles_from_feeds
from app.news.ranker import rank_for_openai_window
from app.news.summarizer import build_digest_with_openai
from app.telegram.formatter import DIGEST_TITLE, format_digest_html, split_telegram_messages
from app.utils.time_utils import format_digest_date

logger = logging.getLogger(__name__)


def _build_digest_html_sync(settings: Settings) -> str:
    """Blocking pipeline used from a worker thread."""
    articles = fetch_articles_from_feeds(settings)
    logger.info("Collected %s raw articles from feeds", len(articles))

    if not articles:
        date = format_digest_date(settings.timezone)
        return (
            f"🤖 <b>{DIGEST_TITLE} — {date}</b>\n\n"
            "<i>No articles found in the current time window. "
            "Try widening LOOKBACK_HOURS or check your RSS sources.</i>"
        )

    deduped = deduplicate_articles(
        articles,
        open_access_host_hints=settings.resolved_open_access_host_hints(),
    )
    logger.info("%s articles after deduplication", len(deduped))

    candidates = rank_for_openai_window(
        deduped,
        limit=settings.max_candidates_for_openai,
    )
    digest_items = build_digest_with_openai(candidates, settings)

    date = format_digest_date(settings.timezone)
    if not digest_items:
        return (
            f"🤖 <b>{DIGEST_TITLE} — {date}</b>\n\n"
            "<i>No qualifying stories were selected today "
            "(model returned empty or API error — see logs).</i>"
        )

    return format_digest_html(digest_items, date)


async def build_digest_html_message(settings: Settings) -> str:
    """Run the full pipeline and return a single HTML message (may exceed Telegram limit)."""
    return await asyncio.to_thread(_build_digest_html_sync, settings)


async def send_digest_to_chat(
    bot: Bot,
    settings: Settings,
    *,
    chat_id: str | None = None,
) -> None:
    """Build the digest and send it to a chat, splitting if needed."""
    text = await build_digest_html_message(settings)
    target = (chat_id or settings.telegram_chat_id).strip()
    chunks = split_telegram_messages(text, max_length=3900)
    for i, chunk in enumerate(chunks):
        try:
            await bot.send_message(
                chat_id=target,
                text=chunk,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            logger.info("Sent digest chunk %s/%s", i + 1, len(chunks))
        except TelegramError:
            logger.exception("Telegram send failed for chunk %s", i + 1)
            raise
