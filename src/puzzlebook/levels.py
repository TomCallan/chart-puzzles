"""Ideal trade levels (entry / stop / target) for a detected pattern.

Candlestick patterns use a fixed multiple of risk (``chart.target_r``, default
2R). Chart patterns (double top/bottom, head & shoulders) use the classic
*measured move*: the target is the pattern's height projected from the
neckline, and the stop sits just beyond the pattern's own pivots — never the
whole window, which can include later price action.
"""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from .indicators import atr
from .patterns.base import PatternMatch


def trade_levels(
    df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    start, end = match.start_idx, match.end_idx
    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    atr_value = float(atr(df).iloc[end])
    buffer = 0.10 * atr_value if atr_value > 0 else 0.0
    meta = match.meta
    neckline = meta.get("neckline")
    window_high = float(high[start : end + 1].max())
    window_low = float(low[start : end + 1].min())
    target_r = float(cfg["chart"].get("target_r", 2.0))
    is_chart = meta.get("kind") == "chart" and neckline is not None

    def _value(key: str, use_high: bool) -> float | None:
        idx = meta.get(key)
        if idx is None:
            return None
        return float(high[idx] if use_high else low[idx])

    if is_chart and match.direction == "bearish":
        peaks = [
            v
            for v in (
                _value("high1_idx", True),
                _value("high2_idx", True),
                _value("head_idx", True),
            )
            if v is not None
        ]
        pattern_high = max(peaks) if peaks else window_high
        entry = float(neckline) - buffer
        stop = pattern_high + buffer
        height = max(pattern_high - float(neckline), atr_value)
        target = float(neckline) - height
    elif is_chart:  # bullish chart pattern
        troughs = [
            v
            for v in (
                _value("low1_idx", False),
                _value("low2_idx", False),
                _value("head_idx", False),
            )
            if v is not None
        ]
        pattern_low = min(troughs) if troughs else window_low
        entry = float(neckline) + buffer
        stop = pattern_low - buffer
        height = max(float(neckline) - pattern_low, atr_value)
        target = float(neckline) + height
    elif match.direction == "bearish":
        entry = (float(neckline) if neckline is not None else window_low) - buffer
        stop = window_high + buffer
        target = entry - target_r * (stop - entry)
    else:  # bullish / neutral candlestick
        entry = (float(neckline) if neckline is not None else window_high) + buffer
        stop = window_low - buffer
        target = entry + target_r * (entry - stop)

    return {
        "direction": match.direction,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk": round(abs(entry - stop), 2),
    }
