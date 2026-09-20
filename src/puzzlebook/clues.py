"""Allocate puzzle clue types across the book.

A "clue" controls what is revealed after the puzzle moment on the puzzle
chart: ``none`` (blank drawing space), ``volume`` (volume only) or ``price``
(price only). A weighted mix spreads the types evenly through the book.
"""

from __future__ import annotations

from typing import Any, Mapping

from .mix import build_schedule, normalize_weights

VALID_CLUES = ("none", "volume", "price")


def normalize_mix(mix: Mapping[str, Any] | None) -> dict[str, float]:
    """Return only the valid, positive clue weights."""
    return normalize_weights(mix, VALID_CLUES)


def build_clue_schedule(mix: Mapping[str, Any] | None, count: int) -> list[str]:
    """Build a ``count``-long, well-interleaved schedule for the given weights."""
    return build_schedule(mix, count, VALID_CLUES)
