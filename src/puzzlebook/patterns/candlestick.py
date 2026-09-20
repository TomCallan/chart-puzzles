"""Pure-pandas candlestick pattern detectors.

These do not require pandas-ta or TA-Lib. If pandas-ta is installed you can
still add detectors that wrap it through the same registry. Each condition
function takes a "prepped" frame (see :func:`_prep`) and returns a boolean
Series marking the *completion* bar of the pattern.
"""

from __future__ import annotations

from typing import Any, Callable, List, Mapping

import numpy as np
import pandas as pd

from .base import PatternDetector, PatternMatch, register


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    body = c - o
    rng = (h - l).replace(0, np.nan)
    return pd.DataFrame(
        {
            "o": o,
            "h": h,
            "l": l,
            "c": c,
            "body": body,
            "abody": body.abs(),
            "rng": rng,
            "upper": h - np.maximum(o, c),
            "lower": np.minimum(o, c) - l,
        }
    )


# ---------------------------------------------------------------------------
# Condition functions
# ---------------------------------------------------------------------------
def bullish_engulfing(p: pd.DataFrame) -> pd.Series:
    prev_bear = p["body"].shift(1) < 0
    cur_bull = p["body"] > 0
    engulfs = (p["c"] >= p["o"].shift(1)) & (p["o"] <= p["c"].shift(1))
    bigger = p["abody"] > p["abody"].shift(1)
    return prev_bear & cur_bull & engulfs & bigger


def bearish_engulfing(p: pd.DataFrame) -> pd.Series:
    prev_bull = p["body"].shift(1) > 0
    cur_bear = p["body"] < 0
    engulfs = (p["o"] >= p["c"].shift(1)) & (p["c"] <= p["o"].shift(1))
    bigger = p["abody"] > p["abody"].shift(1)
    return prev_bull & cur_bear & engulfs & bigger


def hammer(p: pd.DataFrame) -> pd.Series:
    small_body = p["abody"] <= 0.35 * p["rng"]
    long_lower = p["lower"] >= 2.0 * p["abody"]
    tiny_upper = p["upper"] <= 0.20 * p["rng"]
    return small_body & long_lower & tiny_upper


def shooting_star(p: pd.DataFrame) -> pd.Series:
    small_body = p["abody"] <= 0.35 * p["rng"]
    long_upper = p["upper"] >= 2.0 * p["abody"]
    tiny_lower = p["lower"] <= 0.20 * p["rng"]
    return small_body & long_upper & tiny_lower


def doji(p: pd.DataFrame) -> pd.Series:
    return p["abody"] <= 0.10 * p["rng"]


def morning_star(p: pd.DataFrame) -> pd.Series:
    first_bear = (p["body"].shift(2) < 0) & (
        p["abody"].shift(2) > 0.45 * p["rng"].shift(2)
    )
    middle_small = p["abody"].shift(1) < 0.35 * p["rng"].shift(1)
    third_bull = p["body"] > 0
    midpoint = (p["o"].shift(2) + p["c"].shift(2)) / 2.0
    return first_bear & middle_small & third_bull & (p["c"] > midpoint)


def evening_star(p: pd.DataFrame) -> pd.Series:
    first_bull = (p["body"].shift(2) > 0) & (
        p["abody"].shift(2) > 0.45 * p["rng"].shift(2)
    )
    middle_small = p["abody"].shift(1) < 0.35 * p["rng"].shift(1)
    third_bear = p["body"] < 0
    midpoint = (p["o"].shift(2) + p["c"].shift(2)) / 2.0
    return first_bull & middle_small & third_bear & (p["c"] < midpoint)


def bullish_harami(p: pd.DataFrame) -> pd.Series:
    prev_bear = (p["body"].shift(1) < 0) & (
        p["abody"].shift(1) > 0.45 * p["rng"].shift(1)
    )
    inside = (p["o"] >= p["c"].shift(1)) & (p["c"] <= p["o"].shift(1))
    return prev_bear & (p["body"] > 0) & inside


def bearish_harami(p: pd.DataFrame) -> pd.Series:
    prev_bull = (p["body"].shift(1) > 0) & (
        p["abody"].shift(1) > 0.45 * p["rng"].shift(1)
    )
    inside = (p["c"] >= p["o"].shift(1)) & (p["o"] <= p["c"].shift(1))
    return prev_bull & (p["body"] < 0) & inside


def piercing_line(p: pd.DataFrame) -> pd.Series:
    prev_bear = (p["body"].shift(1) < 0) & (
        p["abody"].shift(1) > 0.45 * p["rng"].shift(1)
    )
    midpoint = (p["o"].shift(1) + p["c"].shift(1)) / 2.0
    return (
        prev_bear
        & (p["body"] > 0)
        & (p["o"] < p["c"].shift(1))
        & (p["c"] > midpoint)
        & (p["c"] < p["o"].shift(1))
    )


def dark_cloud_cover(p: pd.DataFrame) -> pd.Series:
    prev_bull = (p["body"].shift(1) > 0) & (
        p["abody"].shift(1) > 0.45 * p["rng"].shift(1)
    )
    midpoint = (p["o"].shift(1) + p["c"].shift(1)) / 2.0
    return (
        prev_bull
        & (p["body"] < 0)
        & (p["o"] > p["c"].shift(1))
        & (p["c"] < midpoint)
        & (p["c"] > p["o"].shift(1))
    )


def three_white_soldiers(p: pd.DataFrame) -> pd.Series:
    bull = p["body"] > 0
    all_bull = bull & bull.shift(1) & bull.shift(2)
    rising = (p["c"] > p["c"].shift(1)) & (p["c"].shift(1) > p["c"].shift(2))
    opens_in_body = (p["o"] > p["o"].shift(1)) & (p["o"] < p["c"].shift(1))
    return all_bull & rising & opens_in_body


def three_black_crows(p: pd.DataFrame) -> pd.Series:
    bear = p["body"] < 0
    all_bear = bear & bear.shift(1) & bear.shift(2)
    falling = (p["c"] < p["c"].shift(1)) & (p["c"].shift(1) < p["c"].shift(2))
    opens_in_body = (p["o"] < p["o"].shift(1)) & (p["o"] > p["c"].shift(1))
    return all_bear & falling & opens_in_body


# ---------------------------------------------------------------------------
# Detector wrapper
# ---------------------------------------------------------------------------
class CandlePattern(PatternDetector):
    """Wraps a boolean condition function as a detector."""

    kind = "candlestick"

    def __init__(
        self,
        name: str,
        direction: str,
        fn: Callable[[pd.DataFrame], pd.Series],
        span: int = 1,
        expect_prior_trend: str | None = None,
    ) -> None:
        self.name = name
        self.direction = direction
        self.fn = fn
        self.span = span
        self.expect_prior_trend = expect_prior_trend

    def detect(
        self, df: pd.DataFrame, cfg: Mapping[str, Any]
    ) -> List[PatternMatch]:
        if len(df) < max(self.span + 2, 5):
            return []
        prepped = _prep(df)
        mask = self.fn(prepped).fillna(False).to_numpy(dtype=bool)
        matches: List[PatternMatch] = []
        for idx in np.nonzero(mask)[0]:
            i = int(idx)
            if i - self.span + 1 < 0:
                continue
            matches.append(
                PatternMatch(
                    name=self.name,
                    direction=self.direction,
                    end_idx=i,
                    start_idx=i - self.span + 1,
                    meta={
                        "kind": self.kind,
                        "expect_prior_trend": self.expect_prior_trend,
                    },
                )
            )
        return matches


_CANDLES: list[tuple[str, str, Callable, int, str | None]] = [
    ("bullish_engulfing", "bullish", bullish_engulfing, 2, "down"),
    ("bearish_engulfing", "bearish", bearish_engulfing, 2, "up"),
    ("hammer", "bullish", hammer, 1, "down"),
    ("shooting_star", "bearish", shooting_star, 1, "up"),
    ("doji", "neutral", doji, 1, None),
    ("morning_star", "bullish", morning_star, 3, "down"),
    ("evening_star", "bearish", evening_star, 3, "up"),
    ("bullish_harami", "bullish", bullish_harami, 2, "down"),
    ("bearish_harami", "bearish", bearish_harami, 2, "up"),
    ("piercing_line", "bullish", piercing_line, 2, "down"),
    ("dark_cloud_cover", "bearish", dark_cloud_cover, 2, "up"),
    ("three_white_soldiers", "bullish", three_white_soldiers, 3, None),
    ("three_black_crows", "bearish", three_black_crows, 3, None),
]

for _name, _dir, _fn, _span, _trend in _CANDLES:
    register(CandlePattern(_name, _dir, _fn, _span, _trend))
