"""Tests for Telegram HTML formatting utilities."""

from __future__ import annotations

from app.news.summarizer import DigestItem
from app.telegram.formatter import format_digest_html, split_telegram_messages


def test_format_digest_escapes_html() -> None:
    items = [
        DigestItem(
            headline='Beta <script>',
            summary='Line & co.',
            source='Source "X"',
            url="https://example.com?q=1&r=2",
        )
    ]
    text = format_digest_html(items, "Jan 1, 2026")
    assert "<script>" not in text
    assert "&amp;" in text or "q=1&amp;r=2" in text


def test_split_telegram_messages_single_chunk() -> None:
    chunks = split_telegram_messages("hello\n\nworld", max_length=1000)
    assert chunks == ["hello\n\nworld"]


def test_split_telegram_messages_multiple_chunks() -> None:
    big = "aa\n\n" * 800
    chunks = split_telegram_messages(big, max_length=50)
    assert len(chunks) > 1
    assert all(len(c) <= 50 for c in chunks)
