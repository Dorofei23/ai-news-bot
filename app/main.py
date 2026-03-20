"""
Entry point for the Telegram AI news bot.

Run the bot with polling + daily scheduler (default)::

    python -m app.main

Send one digest immediately and exit::

    python -m app.main --once
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from telegram import Bot
from telegram.ext import Application

from app.config import Settings
from app.digest_runner import send_digest_to_chat
from app.logger import setup_logging
from app.scheduler.jobs import schedule_daily_digest
from app.telegram.bot import build_application

logger = logging.getLogger(__name__)


async def _run_once(settings: Settings) -> None:
    async with Bot(settings.telegram_bot_token) as bot:
        await send_digest_to_chat(bot, settings)


async def _post_init(application: Application) -> None:
    settings: Settings = application.bot_data["settings"]
    schedule_daily_digest(application, settings)


def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram AI news digest bot")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Build and send a single digest using TELEGRAM_CHAT_ID, then exit",
    )
    args = parser.parse_args()

    try:
        settings = Settings()
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        print("Copy .env.example to .env and fill in secrets.", file=sys.stderr)
        sys.exit(1)

    setup_logging(settings.log_level)

    if args.once:
        try:
            asyncio.run(_run_once(settings))
        except KeyboardInterrupt:
            raise SystemExit(130) from None
        except Exception:
            logger.exception("One-shot digest failed")
            sys.exit(1)
        return

    application = build_application(settings, post_init=_post_init)

    logger.info("Starting bot polling…")
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
