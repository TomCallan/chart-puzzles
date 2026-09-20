"""Shared technical indicators used across the pipeline."""

from __future__ import annotations

import pandas as pd


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range (Wilder-style rolling mean)."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window, min_periods=1).mean()
