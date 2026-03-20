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


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def build_digest_with_openai(
    candidates: list[Article],
    settings: Settings,
) -> list[DigestItem]:
    """
    Ask the model to pick the most important AI stories and one-line summaries.

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
            "snippet": _strip_html(a.snippet)[:500],
        }
        for i, a in enumerate(candidates)
    ]

    system = (
        "You curate a daily AI news digest. You receive a JSON array of articles. "
        "Pick between 5 and 10 items that are genuinely about artificial intelligence, "
        "machine learning, major model/product moves, AI policy, or research with a clear "
        "AI angle. Drop low-value pieces, pure hardware without an AI story, spam, "
        "and duplicates that cover the same event. Prefer major outlets and higher impact. "
        "Respond with compact JSON only, no markdown fences, matching this schema: "
        '{"items":[{"index":0,"summary":"one short sentence in English"}]} '
        "Use each chosen article's original title as displayed elsewhere — do not invent URLs. "
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
            )
        )

    max_n = settings.max_items_in_digest
    if len(out) > max_n:
        out = out[:max_n]

    logger.info("OpenAI selected %s digest items", len(out))
    return out
