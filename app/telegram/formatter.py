"""Format digest items for Telegram (HTML parse mode)."""

from __future__ import annotations

import html
import re

from app.news.summarizer import DigestItem


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def format_digest_html(items: list[DigestItem], date_label: str) -> str:
    """
    Build one HTML message matching the user's readable layout.

    Telegram HTML: https://core.telegram.org/bots/api#html-style
    """
    lines: list[str] = [
        f"🤖 {_esc('AI News Digest')} — {_esc(date_label)}",
        "",
    ]
    for n, it in enumerate(items, start=1):
        safe_url = it.url.strip()
        lines.append(f"<b>{n}. {_esc(it.headline)}</b>")
        lines.append(_esc(it.summary))
        href_attr = html.escape(safe_url, quote=True)
        lines.append(
            f"{_esc('Source')}: <a href=\"{href_attr}\">{_esc(it.source)}</a>"
        )
        lines.append("")

    lines.append(
        "<i>Reply /send to generate today's digest manually.</i>"
    )
    return "\n".join(lines).strip()


def split_telegram_messages(text: str, *, max_length: int = 3900) -> list[str]:
    """
    Split a long HTML message into Telegram-safe chunks under `max_length`.

    Prefers splitting on blank lines between stories to avoid breaking tags.
    """
    if len(text) <= max_length:
        return [text]

    blocks = re.split(r"\n\n+", text)
    chunks: list[str] = []
    buf: list[str] = []
    current_len = 0

    for block in blocks:
        sep = "\n\n" if buf else ""
        addition = sep + block
        if current_len + len(addition) <= max_length:
            buf.append(block)
            current_len += len(addition)
            continue

        if buf:
            chunks.append("\n\n".join(buf))
            buf = []
            current_len = 0

        if len(block) <= max_length:
            buf = [block]
            current_len = len(block)
        else:
            # Hard split very long blocks
            start = 0
            while start < len(block):
                part = block[start : start + max_length]
                chunks.append(part)
                start += max_length

    if buf:
        chunks.append("\n\n".join(buf))

    return [c for c in chunks if c.strip()]
