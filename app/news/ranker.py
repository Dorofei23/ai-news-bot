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

# Frontend / UI engineering — boosts pure web and AI-for-developers candidates.
_FE_KEYWORDS = re.compile(
    r"\b("
    r"react native|reactnative|typescript|javascript|\bjsx\b|\btsx\b|"
    r"\breact\b|next\.js|nextjs|vite|webpack|esbuild|rollup|parcel|"
    r"\bexpo\b|metro|tailwind|storybook|jest|cypress|playwright|"
    r"graphql|hydration|server components?|server-side rendering|\bssr\b|"
    r"web platform|web api|service worker|progressive web|\bpwa\b|"
    r"chrome|safari|firefox|webkit|devtools|"
    r"frontend|front-end|ui engineering|design system|"
    r"codegen|code generation|ide plugin|\bllm\b dev|developer preview"
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
    Score articles for AI and/or frontend relevance and recency.

    Higher is better. Used to trim the candidate list before the OpenAI step.
    """
    now = now or datetime.now(tz=UTC)
    text = f"{article.title}\n{article.snippet}"
    score = 0.0

    has_ai = bool(_AI_KEYWORDS.search(text))
    has_fe = bool(_FE_KEYWORDS.search(text))

    if has_ai:
        score += 4.0
    if has_fe:
        score += 3.0
    if has_ai and has_fe:
        score += 2.0

    title_lower = article.title.lower()
    if (
        "ai" in title_lower
        or "gpt" in title_lower
        or "openai" in title_lower
        or "react" in title_lower
        or "typescript" in title_lower
    ):
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
