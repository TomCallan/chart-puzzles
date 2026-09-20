"""Practice question types for the puzzle book.

A question type is the task the reader performs on a chart. It is orthogonal to
the *clue* (what future information is revealed), but some combinations are
invalid and are resolved by :func:`resolve_clue`.

    identify  - name the pattern completing at the dashed line
    direction - decide whether the next move is up or down
    levels    - mark the entry, stop-loss and first target
"""

from __future__ import annotations

from typing import Any, Mapping

from .mix import build_schedule, normalize_weights

VALID_QUESTIONS = ("identify", "direction", "levels")

QUESTION_LABELS: dict[str, str] = {
    "identify": "Identify",
    "direction": "Direction",
    "levels": "Levels",
}

QUESTION_PROMPTS: dict[str, str] = {
    "identify": (
        "A pattern is completing at the dashed line. Name it, then turn the "
        "page and mark the neckline plus your entry, stop-loss and first target."
    ),
    "direction": (
        "A pattern is completing at the dashed line. Decide whether price will "
        "move up or down from here, then turn the page and mark your entry, "
        "stop-loss and first target."
    ),
    "levels": (
        "A pattern is completing at the dashed line. Turn the page and mark "
        "your entry, stop-loss and first target for the setup."
    ),
}

QUESTION_CHECKLIST: dict[str, list[str]] = {
    "identify": [
        "Name the pattern.",
        "Mark the neckline or key level.",
    ],
    "direction": [
        "Circle up or down.",
    ],
    "levels": [
        "Mark the entry, stop-loss and first target.",
    ],
}

QUESTION_TITLES: dict[str, str] = {
    "identify": "What pattern is completing here?",
    "direction": "Which way next?",
    "levels": "Plan the trade.",
}


def normalize_mix(mix: Mapping[str, Any] | None) -> dict[str, float]:
    """Return only the valid, positive question weights."""
    return normalize_weights(mix, VALID_QUESTIONS)


def build_question_schedule(
    mix: Mapping[str, Any] | None, count: int
) -> list[str]:
    """Build a ``count``-long, well-interleaved schedule of question types."""
    return build_schedule(mix, count, VALID_QUESTIONS)


def resolve_clue(question: str, clue: str) -> str:
    """Downgrade clue/question combinations that would give the answer away."""
    # A price clue reveals where price went, so it trivialises level marking
    # and gives away the answer to a direction question.
    if question == "levels" and clue == "price":
        return "none"
    if question == "direction" and clue == "price":
        return "none"
    return clue


# Which clues make sense for each question type.
CLUE_VALIDITY: dict[str, tuple[str, ...]] = {
    "identify": ("none", "volume", "price"),
    "direction": ("none", "volume"),
    "levels": ("none", "volume"),
}


def _round_preserving_sum(
    values: Mapping[str, float], total: int
) -> dict[str, int]:
    """Round weights to integers that sum to ``total`` (largest remainder)."""
    floors = {key: int(value) for key, value in values.items()}
    remainder = total - sum(floors.values())
    if remainder > 0 and values:
        order = sorted(
            values, key=lambda key: (values[key] - floors[key], key), reverse=True
        )
        for index in range(remainder):
            floors[order[index % len(order)]] += 1
    return {key: value for key, value in floors.items() if value > 0}


def _interleave(values: list[str]) -> list[str]:
    """Evenly interleave a multiset (deficit round-robin)."""
    from collections import Counter

    counts = Counter(values)
    total = len(values)
    used = {key: 0 for key in counts}
    ordered: list[str] = []
    for _ in range(total):
        chosen = max(counts, key=lambda key: (counts[key] - used[key], key))
        used[chosen] += 1
        ordered.append(chosen)
    return ordered


def assign_clues(
    questions: list[str], clue_mix: Mapping[str, Any] | None
) -> list[str]:
    """Assign clues to questions so the target mix is met as closely as the
    per-question validity rules allow.

    Clues are allocated to question types (most-constrained clue first, so
    ``price`` goes to the ``identify`` puzzles that can use it), then
    interleaved within each question type so no type gets a single clue.
    """
    from collections import Counter

    from .clues import VALID_CLUES, normalize_mix

    weights = normalize_mix(clue_mix)
    count = len(questions)
    if not weights or count == 0:
        return []

    total = sum(weights.values())
    raw_targets = {clue: weights.get(clue, 0.0) / total * count for clue in VALID_CLUES}
    targets = _round_preserving_sum(raw_targets, count)

    question_counts = Counter(questions)
    remaining = dict(question_counts)
    quotas: dict[str, dict[str, int]] = {question: {} for question in question_counts}

    def eligible(clue: str) -> list[str]:
        return [q for q in question_counts if clue in CLUE_VALIDITY.get(q, ())]

    for clue in sorted(VALID_CLUES, key=lambda c: len(eligible(c))):
        pools = [q for q in eligible(clue) if remaining[q] > 0]
        capacity = sum(remaining[q] for q in pools)
        want = min(targets.get(clue, 0), capacity)
        if want <= 0 or capacity <= 0:
            continue
        shares = _round_preserving_sum(
            {q: want * remaining[q] / capacity for q in pools}, want
        )
        for question, amount in shares.items():
            quotas[question][clue] = quotas[question].get(clue, 0) + amount
            remaining[question] -= amount

    per_type: dict[str, list[str]] = {}
    for question, quota in quotas.items():
        values: list[str] = []
        for clue, amount in sorted(quota.items()):
            values.extend([clue] * amount)
        per_type[question] = _interleave(values) or ["none"]

    cursors = {question: 0 for question in question_counts}
    assigned: list[str] = []
    for question in questions:
        pool = per_type[question]
        assigned.append(pool[cursors[question] % len(pool)])
        cursors[question] += 1
    return assigned
