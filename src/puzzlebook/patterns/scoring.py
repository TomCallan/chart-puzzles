"""Cleanliness scoring for detected patterns.

A pattern only makes it into the book if it scores above ``min_score``
(default 85/100). The score is a weighted blend of five factors:

    trend    - is there a clear, *smooth* prior trend the pattern can reverse/continue?
    volume   - is the completion bar confirmed by above-average volume?
    size     - is the pattern meaningful relative to ATR (not noise, not huge)?
    quality  - pattern-specific geometry (engulfing coverage, shadow ratios,
               swing prominence for hammers/stars...)
    context  - enough clean history before the pattern, not too many bars?
"""

from __future__ import annotations

from typing import Any, List, Mapping

import numpy as np
import pandas as pd

from .base import PatternMatch
from ..indicators import atr


def _ramp(x: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.0
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def _trend_factor(df: pd.DataFrame, match: PatternMatch) -> float:
    """Magnitude of the prior trend, discounted by how smooth it is."""
    look = 20
    start = match.start_idx
    close = df["Close"].to_numpy(dtype=float)
    if start < look:
        return 0.15
    segment = close[start - look : start + 1]
    if segment.size < 3:
        return 0.15
    atr_value = float(atr(df).iloc[start])
    if atr_value <= 0:
        return 0.4
    move_atr = (segment[-1] - segment[0]) / atr_value

    # Smoothness: R^2 of a linear fit on log price. A whipsawing market can
    # still net +2 ATR, so we discount trends that do not look like a clean slope.
    x = np.arange(segment.size, dtype=float)
    y = np.log(np.clip(segment, 1e-9, None))
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(((y - fitted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    smoothness = 0.4 + 0.6 * float(np.clip(r2, 0.0, 1.0))

    expect = match.meta.get("expect_prior_trend")
    if expect == "down":
        base = _ramp(-move_atr, 0.5, 3.0)
    elif expect == "up":
        base = _ramp(move_atr, 0.5, 3.0)
    else:
        base = _ramp(abs(move_atr), 0.5, 3.0)
    return base * smoothness


def _prominence(df: pd.DataFrame, match: PatternMatch, look: int = 10) -> float:
    """How far the pattern's extreme protrudes beyond the prior bars.

    A hammer buried inside the recent range is ambiguous; one that pokes below
    the prior lows is a textbook swing extreme.
    """
    end = match.end_idx
    start = max(0, end - look)
    if end - start < 3:
        return 0.6
    atr_value = float(atr(df).iloc[end]) or 1.0
    if match.name == "shooting_star":
        prior_extreme = float(df["High"].to_numpy()[start:end].max())
        protrusion = (float(df["High"].iloc[end]) - prior_extreme) / atr_value
    else:
        prior_extreme = float(df["Low"].to_numpy()[start:end].min())
        protrusion = (prior_extreme - float(df["Low"].iloc[end])) / atr_value
    return float(np.clip(0.5 + 0.5 * protrusion, 0.0, 1.0))


def _volume_factor(df: pd.DataFrame, match: PatternMatch) -> float:
    volume = df["Volume"].to_numpy(dtype=float)
    end = match.end_idx
    base = volume[max(0, end - 20) : end]
    base = base[np.isfinite(base)]
    if base.size == 0 or base.mean() <= 0:
        return 0.5
    ratio = volume[end] / base.mean()
    return _ramp(ratio, 0.8, 1.8)


def _size_factor(df: pd.DataFrame, match: PatternMatch) -> float:
    atr_value = float(atr(df).iloc[match.end_idx])
    if atr_value <= 0:
        return 0.5
    high = df["High"].to_numpy(dtype=float)[match.start_idx : match.end_idx + 1]
    low = df["Low"].to_numpy(dtype=float)[match.start_idx : match.end_idx + 1]
    span = float(high.max() - low.min())
    ratio = span / atr_value
    low_ok = _ramp(ratio, 0.6, 1.8)
    high_ok = 1.0 - _ramp(ratio, 8.0, 18.0)
    return max(0.0, low_ok * high_ok)


def _quality_factor(df: pd.DataFrame, match: PatternMatch) -> float:
    explicit = match.meta.get("quality")
    if explicit is not None:
        return float(np.clip(explicit, 0.0, 1.0))

    o = df["Open"].to_numpy(dtype=float)
    h = df["High"].to_numpy(dtype=float)
    l = df["Low"].to_numpy(dtype=float)
    c = df["Close"].to_numpy(dtype=float)
    end = match.end_idx
    body = abs(c[end] - o[end])
    rng = max(h[end] - l[end], 1e-9)
    upper = h[end] - max(o[end], c[end])
    lower = min(o[end], c[end]) - l[end]
    name = match.name

    if name in ("bullish_engulfing", "bearish_engulfing"):
        prev_body = abs(c[end - 1] - o[end - 1])
        return _ramp(body / max(prev_body, 1e-9), 1.0, 2.2)
    if name == "hammer":
        return _ramp(lower / max(body, 1e-9), 2.0, 4.0) * _prominence(df, match)
    if name == "shooting_star":
        return _ramp(upper / max(body, 1e-9), 2.0, 4.0) * _prominence(df, match)
    if name == "doji":
        return 1.0 - _ramp(body / rng, 0.04, 0.15)
    if name in ("gravestone_doji", "dragonfly_doji"):
        return 1.0 - _ramp(body / rng, 0.04, 0.15)
    if name in ("morning_star", "evening_star", "morning_doji_star", "evening_doji_star"):
        prev_body = abs(c[end - 1] - o[end - 1])
        first_body = abs(c[end - 2] - o[end - 2])
        return 0.5 * _ramp(body / max(first_body, 1e-9), 0.5, 1.2) + 0.5 * (
            1.0 - _ramp(prev_body / max(rng, 1e-9), 0.3, 0.6)
        )
    if name in (
        "piercing_line",
        "dark_cloud_cover",
        "harami_bullish",
        "harami_bearish",
        "harami_cross_bullish",
        "harami_cross_bearish",
    ):
        return 0.75
    return 0.7


def _context_factor(
    df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any]
) -> float:
    """Enough clean history before the pattern. Span only matters for chart patterns.

    Candlesticks span 1-3 bars, so a span term would always saturate; chart
    patterns spanning dozens of bars get messier and are penalised for it.
    """
    min_history = int(cfg["patterns"]["min_history_bars"])
    before = _ramp(match.start_idx, min_history * 0.5, min_history)
    if match.meta.get("kind") == "candlestick":
        return before
    bars = match.end_idx - match.start_idx + 1
    span = 1.0 - _ramp(bars, 40.0, 90.0)
    return max(0.0, 0.5 * before + 0.5 * span)


def cleanliness_score(
    df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any]
) -> float:
    """Return a 0-100 cleanliness score and stash the factor breakdown."""
    weights = cfg["patterns"]["weights"]
    factors = {
        "trend": _trend_factor(df, match),
        "volume": _volume_factor(df, match),
        "size": _size_factor(df, match),
        "quality": _quality_factor(df, match),
        "context": _context_factor(df, match, cfg),
    }
    total_weight = sum(weights.values()) or 1.0
    score = 100.0 * sum(weights[k] * factors[k] for k in factors) / total_weight
    match.meta["factors"] = {k: round(v, 3) for k, v in factors.items()}
    return round(float(score), 1)


def score_matches(
    df: pd.DataFrame, matches: List[PatternMatch], cfg: Mapping[str, Any]
) -> List[PatternMatch]:
    for match in matches:
        match.score = cleanliness_score(df, match, cfg)
    return matches


def dedupe(
    matches: List[PatternMatch], cfg: Mapping[str, Any]
) -> List[PatternMatch]:
    """Drop lower-quality duplicates and heavily overlapping patterns."""
    gap = int(cfg["patterns"]["dedupe_bars"])
    ordered = sorted(matches, key=lambda m: (-m.score, m.start_idx))
    kept: List[PatternMatch] = []
    for match in ordered:
        drop = False
        for other in kept:
            same_name = match.name == other.name
            if same_name and abs(match.end_idx - other.end_idx) <= gap:
                drop = True
                break
            overlaps = not (
                match.end_idx < other.start_idx - gap
                or match.start_idx > other.end_idx + gap
            )
            if not same_name and overlaps:
                drop = True
                break
        if not drop:
            kept.append(match)
    return sorted(kept, key=lambda m: m.start_idx)
