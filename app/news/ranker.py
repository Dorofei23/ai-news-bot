"""Heuristic pre-ranking before OpenAI selection."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.news.parser import Article

# Broad AI-related tokens for a cheap first pass (not a substitute for the model).
_AI_KEYWORDS = re.compile(
    r"\b("
    r"ai\b|a\.i\.|artificial intelligence|machine learning|\bml\b|deep learning|"
    r"neural|llm|large language|gpt|openai|anthropic|claude|gemini|"
    r"copilot|chatbot|generative|diffusion|transformer|nvidia|cuda|"
    r"foundation model|inference|tokenizer|embedding|agentic|"
    r"robotics|autonomous vehicle|computer vision|speech recognition"
    r")\b",
    re.IGNORECASE,
)

_MIN = datetime.min.replace(tzinfo=UTC)


def _age_hours(published: datetime | None, now: datetime) -> float:
    if published is None:
        return 999.0
    delta = now - published.astimezone(UTC)
    return max(delta.total_seconds() / 3600.0, 0.0)


def heuristic_score(article: Article, *, now: datetime | None = None) -> float:
    """
    Score articles for likely AI relevance and recency.

    Higher is better. Used to trim the candidate list before the OpenAI step.
    """
    now = now or datetime.now(tz=UTC)
    text = f"{article.title}\n{article.snippet}"
    score = 0.0

    if _AI_KEYWORDS.search(text):
        score += 4.0

    title_lower = article.title.lower()
    if "ai" in title_lower or "gpt" in title_lower or "openai" in title_lower:
        score += 1.0

    hours = _age_hours(article.published_at, now)
    # Prefer very recent items; gentle decay
    score += max(0.0, 10.0 - min(hours, 48.0) * 0.15)

    return score


def rank_for_openai_window(articles: list[Article], *, limit: int) -> list[Article]:
    """Return the top `limit` articles by heuristic score (stable for OpenAI)."""
    now = datetime.now(tz=UTC)
    scored = sorted(
        articles,
        key=lambda a: heuristic_score(a, now=now),
        reverse=True,
    )
    return scored[:limit]
