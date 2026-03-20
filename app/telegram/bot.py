"""Telegram command handlers and Application factory."""

from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import Settings
from app.digest_runner import send_digest_to_chat

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(
        "Hi! I post a daily AI news digest.\n"
        "Commands:\n"
        "/send — build and send today's digest to this chat\n"
        "/health — bot status\n"
        "/sources — list configured RSS feeds\n\n"
        "Scheduled digests use TELEGRAM_CHAT_ID from the server environment."
    )


async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return
    settings: Settings = context.application.bot_data["settings"]
    await update.message.reply_text("Gathering and summarizing the latest AI news…")
    try:
        await send_digest_to_chat(
            context.bot,
            settings,
            chat_id=str(update.effective_chat.id),
        )
        await update.message.reply_text("Done — digest sent.")
    except Exception:
        logger.exception("/send failed")
        await update.message.reply_text(
            "Something went wrong while building or sending the digest. Check server logs."
        )


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    try:
        me = await context.bot.get_me()
        await update.message.reply_text(f"OK — bot @{me.username} is reachable.")
    except Exception as exc:
        logger.exception("health check failed")
        await update.message.reply_text(f"Unhealthy: {exc!s}")


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    settings: Settings = context.application.bot_data["settings"]
    feeds = settings.resolved_feed_urls()
    lines = ["Configured RSS feeds:"] + [f"• {u}" for u in feeds]
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    await update.message.reply_text(text)


def build_application(
    settings: Settings,
    *,
    post_init=None,
) -> Application:
    """Create the python-telegram-bot Application with handlers."""
    builder = Application.builder().token(settings.telegram_bot_token)
    if post_init is not None:
        builder = builder.post_init(post_init)
    application = builder.build()
    application.bot_data["settings"] = settings

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("send", cmd_send))
    application.add_handler(CommandHandler("health", cmd_health))
    application.add_handler(CommandHandler("sources", cmd_sources))

    return application
