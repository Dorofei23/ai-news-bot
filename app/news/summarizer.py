"""Use OpenAI to filter, dedupe by topic, and summarize digest items."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from app.config import Settings
from app.news.parser import Article

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DigestItem:
    """One row in the final digest after model selection."""

    headline: str
    summary: str
    source: str
    url: str
    paywall_likely: bool = False


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def build_digest_with_openai(
    candidates: list[Article],
    settings: Settings,
) -> list[DigestItem]:
    """
    Ask the model to pick items for an AI×frontend engineering digest.

    Returns an empty list when there are no candidates or the model returns none.
    """
    if not candidates:
        return []

    client = OpenAI(api_key=settings.openai_api_key)
    payload = [
        {
            "index": i,
            "title": _strip_html(a.title)[:300],
            "source": a.source[:120],
            "url": a.url,
            "paywall_likely": a.paywall_likely,
            "snippet": _strip_html(a.snippet)[:1200],
        }
        for i, a in enumerate(candidates)
    ]

    system = (
        "You curate a daily digest for senior UI engineers (React, React Native, web). "
        "You receive a JSON array of articles. "
        "Pick between 5 and 10 items total. Priority: stories where AI meets product "
        "engineering — IDE assistants, codegen and agents, design-to-code, LLMs in design "
        "systems or component libraries, on-device or client-side ML in apps, evaluating "
        "models for UI work, or security and privacy of AI in the browser or mobile apps. "
        "Also include 1–3 high-signal items that are purely frontend when they materially "
        "affect day-to-day UI work (major React or RN releases, JS/TS or web platform changes, "
        "important browser or tooling updates). "
        "Skip general AI hype with no line to building user interfaces, robotics, "
        "enterprise AI with no developer angle, and duplicate coverage of the same event. "
        "When paywall_likely is true, summarize only from the provided snippet — "
        "do not invent details that are not in that text. "
        "Each summary must be one short sentence in English; when useful, add a brief hint "
        "of why it matters for frontend work. "
        "Respond with compact JSON only, no markdown fences, matching this schema: "
        '{"items":[{"index":0,"summary":"one short sentence in English"}]} '
        "Use each chosen article's original title — do not invent URLs. "
        "Order items from most to least important."
    )
    user = json.dumps({"articles": payload})

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
    except Exception:
        logger.exception("OpenAI request failed while building digest")
        return []

    raw = (completion.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("OpenAI returned non-JSON digest payload: %s", raw[:500])
        return []

    items = data.get("items")
    if not isinstance(items, list):
        return []

    by_index = {i: a for i, a in enumerate(candidates)}
    out: list[DigestItem] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row["index"])
        except (KeyError, TypeError, ValueError):
            continue
        summary = str(row.get("summary", "")).strip()
        art = by_index.get(idx)
        if art is None or not summary:
            continue
        out.append(
            DigestItem(
                headline=_strip_html(art.title).strip(),
                summary=summary,
                source=art.source,
                url=art.url,
                paywall_likely=art.paywall_likely,
            )
        )

    max_n = settings.max_items_in_digest
    if len(out) > max_n:
        out = out[:max_n]

    logger.info("OpenAI selected %s digest items", len(out))
    return out
