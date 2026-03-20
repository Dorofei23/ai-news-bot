"""Register recurring jobs with python-telegram-bot's JobQueue (APScheduler-backed)."""

from __future__ import annotations

import logging
from datetime import time as dt_time

from telegram.ext import Application, ContextTypes
from zoneinfo import ZoneInfo

from app.config import Settings
from app.digest_runner import send_digest_to_chat

logger = logging.getLogger(__name__)


async def _daily_digest_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue callback — sends digest to TELEGRAM_CHAT_ID."""
    settings: Settings = context.application.bot_data["settings"]
    try:
        await send_digest_to_chat(context.bot, settings)
    except Exception:
        logger.exception("Scheduled digest failed")


def schedule_daily_digest(application: Application, settings: Settings) -> None:
    """
    Queue a daily digest at DIGEST_HOUR:DIGEST_MINUTE in TIMEZONE.

    Requires the `python-telegram-bot[job-queue]` extra (APScheduler + tzdata).
    """
    if application.job_queue is None:
        raise RuntimeError(
            "Job queue is not available. Install python-telegram-bot with the "
            "'job-queue' extra: pip install 'python-telegram-bot[job-queue]'"
        )

    tz = ZoneInfo(settings.timezone)
    run_at = dt_time(
        hour=settings.digest_hour,
        minute=settings.digest_minute,
        tzinfo=tz,
    )
    application.job_queue.run_daily(
        _daily_digest_callback,
        time=run_at,
        name="daily_ai_digest",
    )
    logger.info(
        "Scheduled daily digest at %s:%02d (%s)",
        settings.digest_hour,
        settings.digest_minute,
        settings.timezone,
    )
