"""Generic weighted scheduler for spreading puzzle attributes through a book.

Given weights such as ``{"identify": 40, "direction": 30, "levels": 30}`` and a
total count, produce a well-interleaved sequence using deficit round-robin so
values are spread evenly rather than clustered.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def normalize_weights(
    weights: Mapping[str, Any] | None, valid: Sequence[str]
) -> dict[str, float]:
    """Return only the valid, positive weights."""
    if not weights:
        return {}
    valid_set = set(valid)
    result: dict[str, float] = {}
    for key, value in weights.items():
        name = str(key).lower()
        if name not in valid_set:
            continue
        try:
            weight = float(value)
        except (TypeError, ValueError):
            continue
        if weight > 0:
            result[name] = weight
    return result


def build_schedule(
    weights: Mapping[str, Any] | None, count: int, valid: Sequence[str]
) -> list[str]:
    """Build a ``count``-long, evenly interleaved schedule for the weights."""
    norm = normalize_weights(weights, valid)
    if not norm or count <= 0:
        return []
    total = sum(norm.values())
    targets = {name: weight / total * count for name, weight in norm.items()}
    counts = {name: 0 for name in norm}
    schedule: list[str] = []
    for _ in range(count):
        chosen = max(norm, key=lambda name: (targets[name] - counts[name], name))
        counts[chosen] += 1
        schedule.append(chosen)
    return schedule
