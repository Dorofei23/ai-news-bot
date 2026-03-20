"""Small retry helper for transient HTTP/API failures."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def retry_call(
    fn: Callable[P, R],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> R:
    """
    Call `fn`, retrying on failure with exponential backoff.

    Intended for quick local MVP use; swap for Tenacity or similar if needed.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except exceptions as exc:  # noqa: PERF203 — intentional retry loop
            last_exc = exc
            if attempt >= attempts:
                break
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Call failed (attempt %s/%s): %s; retrying in %.1fs",
                attempt,
                attempts,
                exc,
                delay,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
