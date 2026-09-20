"""Ideal trade levels (entry / stop / target) for a detected pattern.

For chart patterns the entry is the neckline breakout; for candlesticks it is
the pattern's extreme. The stop sits on the opposite side of the pattern and
the target is a fixed multiple of risk (``chart.target_r``, default 2R).
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
    neckline = match.meta.get("neckline")
    window_high = float(high[start : end + 1].max())
    window_low = float(low[start : end + 1].min())
    target_r = float(cfg["chart"].get("target_r", 2.0))

    if match.direction == "bearish":
        entry = (float(neckline) if neckline is not None else window_low) - buffer
        stop = window_high + buffer
        risk = stop - entry
        target = entry - target_r * risk
    else:  # bullish (and neutral patterns, treated as a long breakout)
        entry = (float(neckline) if neckline is not None else window_high) + buffer
        stop = window_low - buffer
        risk = entry - stop
        target = entry + target_r * risk

    return {
        "direction": match.direction,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk": round(risk, 2),
    }
