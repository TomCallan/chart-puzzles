"""Candlestick pattern detectors ported from the PineScript reference.

Every pattern in ``pinescript_examples.md`` is implemented here as a pure-pandas
condition on a "prepped" frame. The helper columns mirror the PineScript
variables one-for-one (``C_Body``, ``C_BodyAvg``, ``C_DownTrend`` ...) so the
logic stays easy to compare against the source.

Each condition is evaluated at the pattern's *completion* bar, so multi-bar
patterns reference earlier bars with ``.shift(k)`` exactly like ``[k]`` in
PineScript. The reference frame is anchored at the completion bar to keep the
shift arithmetic correct.
"""

from __future__ import annotations

from typing import Any, Callable, List, Mapping

import numpy as np
import pandas as pd

from .base import PatternDetector, PatternMatch, register

BODY_EMA_LEN = 14
SHADOW_PERCENT = 5.0
DOJI_BODY_PERCENT = 5.0
FACTOR = 2.0


def _prep(df: pd.DataFrame, cfg: Mapping[str, Any]) -> pd.DataFrame:
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    body_hi = np.maximum(o, c)
    body_lo = np.minimum(o, c)
    body = body_hi - body_lo
    rng = h - l
    up = h - body_hi
    dn = body_lo - l
    body_avg = body.ewm(span=BODY_EMA_LEN, adjust=False).mean()
    small = body < body_avg
    long = body > body_avg
    white = o < c
    black = o > c
    has_up = up > SHADOW_PERCENT / 100.0 * body
    has_dn = dn > SHADOW_PERCENT / 100.0 * body
    body_mid = body / 2.0 + body_lo

    up_safe = up.replace(0, np.nan)
    dn_safe = dn.replace(0, np.nan)
    shadow_equals = (up == dn) | (
        ((up - dn).abs() / dn_safe * 100.0 < 100.0)
        & ((dn - up).abs() / up_safe * 100.0 < 100.0)
    )
    is_doji_body = (rng > 0) & (body <= rng * DOJI_BODY_PERCENT / 100.0)
    doji = is_doji_body & shadow_equals

    rule = str(cfg["patterns"].get("trend_rule", "sma50")).lower()
    if rule == "none":
        up_trend = pd.Series(True, index=df.index)
        down_trend = pd.Series(True, index=df.index)
    elif rule in ("sma50_200", "sma50,sma200"):
        sma50 = c.rolling(50).mean()
        sma200 = c.rolling(200).mean()
        up_trend = (c > sma50) & (sma50 > sma200)
        down_trend = (c < sma50) & (sma50 < sma200)
    else:
        sma50 = c.rolling(50).mean()
        up_trend = c > sma50
        down_trend = c < sma50

    return pd.DataFrame(
        {
            "o": o, "h": h, "l": l, "c": c,
            "body": body, "bodyhi": body_hi, "bodylo": body_lo,
            "bodyavg": body_avg, "rng": rng, "up": up, "dn": dn,
            "hasup": has_up, "hasdn": has_dn,
            "white": white, "black": black,
            "small": small, "long": long, "bodymid": body_mid,
            "is_doji_body": is_doji_body, "doji": doji,
            "hl2": (h + l) / 2.0,
            "uptrend": up_trend, "downtrend": down_trend,
        },
        index=df.index,
    )


# ---------------------------------------------------------------------------
# Condition functions (each returns a boolean Series at the completion bar)
# ---------------------------------------------------------------------------
def on_neck(p):
    return (
        p["downtrend"] & p["black"].shift(1) & p["long"].shift(1) & p["white"]
        & (p["o"] < p["c"].shift(1)) & p["small"] & (p["rng"] != 0)
        & ((p["c"] - p["l"].shift(1)).abs() <= p["bodyavg"] * 0.05)
    )


def rising_window(p):
    return (
        p["uptrend"].shift(1) & (p["rng"] != 0) & (p["rng"].shift(1) != 0)
        & (p["l"] > p["h"].shift(1))
    )


def falling_window(p):
    return (
        p["downtrend"].shift(1) & (p["rng"] != 0) & (p["rng"].shift(1) != 0)
        & (p["h"] < p["l"].shift(1))
    )


def falling_three_methods(p):
    low4, high4 = p["l"].shift(4), p["h"].shift(4)

    def mid(k):
        return (
            p["small"].shift(k) & p["white"].shift(k)
            & (p["o"].shift(k) > low4) & (p["c"].shift(k) < high4)
        )

    first = p["downtrend"].shift(4) & p["long"].shift(4) & p["black"].shift(4)
    last = p["long"] & p["black"] & (p["c"] < p["c"].shift(4))
    return first & mid(3) & mid(2) & mid(1) & last


def rising_three_methods(p):
    low4, high4 = p["l"].shift(4), p["h"].shift(4)

    def mid(k):
        return (
            p["small"].shift(k) & p["black"].shift(k)
            & (p["o"].shift(k) < high4) & (p["c"].shift(k) > low4)
        )

    first = p["uptrend"].shift(4) & p["long"].shift(4) & p["white"].shift(4)
    last = p["long"] & p["white"] & (p["c"] > p["c"].shift(4))
    return first & mid(3) & mid(2) & mid(1) & last


def tweezer_top(p):
    shape = (~p["is_doji_body"]) | (p["hasup"] & p["hasdn"])
    return (
        p["uptrend"].shift(1) & shape
        & ((p["h"] - p["h"].shift(1)).abs() <= p["bodyavg"] * 0.05)
        & p["white"].shift(1) & p["black"] & p["long"].shift(1)
    )


def tweezer_bottom(p):
    shape = (~p["is_doji_body"]) | (p["hasup"] & p["hasdn"])
    return (
        p["downtrend"].shift(1) & shape
        & ((p["l"] - p["l"].shift(1)).abs() <= p["bodyavg"] * 0.05)
        & p["black"].shift(1) & p["white"] & p["long"].shift(1)
    )


def dark_cloud_cover(p):
    return (
        p["uptrend"].shift(1) & p["white"].shift(1) & p["long"].shift(1)
        & p["black"] & (p["o"] >= p["h"].shift(1))
        & (p["c"] < p["bodymid"].shift(1)) & (p["c"] > p["o"].shift(1))
    )


def downside_tasuki_gap(p):
    return (
        p["long"].shift(2) & p["small"].shift(1) & p["downtrend"]
        & p["black"].shift(2) & (p["bodyhi"].shift(1) < p["bodylo"].shift(2))
        & p["black"].shift(1) & p["white"]
        & (p["bodyhi"] <= p["bodylo"].shift(2))
        & (p["bodyhi"] >= p["bodyhi"].shift(1))
    )


def upside_tasuki_gap(p):
    return (
        p["long"].shift(2) & p["small"].shift(1) & p["uptrend"]
        & p["white"].shift(2) & (p["bodylo"].shift(1) > p["bodyhi"].shift(2))
        & p["white"].shift(1) & p["black"]
        & (p["bodylo"] >= p["bodyhi"].shift(2))
        & (p["bodylo"] <= p["bodylo"].shift(1))
    )


def evening_doji_star(p):
    return (
        p["long"].shift(2) & p["is_doji_body"].shift(1) & p["long"] & p["uptrend"]
        & p["white"].shift(2) & (p["bodylo"].shift(1) > p["bodyhi"].shift(2))
        & p["black"] & (p["bodylo"] <= p["bodymid"].shift(2))
        & (p["bodylo"] > p["bodylo"].shift(2))
        & (p["bodylo"].shift(1) > p["bodyhi"])
    )


def morning_doji_star(p):
    return (
        p["long"].shift(2) & p["is_doji_body"].shift(1) & p["long"] & p["downtrend"]
        & p["black"].shift(2) & (p["bodyhi"].shift(1) < p["bodylo"].shift(2))
        & p["white"] & (p["bodyhi"] >= p["bodymid"].shift(2))
        & (p["bodyhi"] < p["bodyhi"].shift(2))
        & (p["bodyhi"].shift(1) < p["bodylo"])
    )


def doji_star_bearish(p):
    return (
        p["uptrend"] & p["white"].shift(1) & p["long"].shift(1)
        & p["is_doji_body"] & (p["bodylo"] > p["bodyhi"].shift(1))
    )


def doji_star_bullish(p):
    return (
        p["downtrend"] & p["black"].shift(1) & p["long"].shift(1)
        & p["is_doji_body"] & (p["bodyhi"] < p["bodylo"].shift(1))
    )


def piercing_line(p):
    return (
        p["downtrend"].shift(1) & p["black"].shift(1) & p["long"].shift(1)
        & p["white"] & (p["o"] <= p["l"].shift(1))
        & (p["c"] > p["bodymid"].shift(1)) & (p["c"] < p["o"].shift(1))
    )


def hammer(p):
    return (
        p["small"] & (p["body"] > 0) & (p["bodylo"] > p["hl2"])
        & (p["dn"] >= FACTOR * p["body"]) & (~p["hasup"]) & p["downtrend"]
    )


def hanging_man(p):
    return (
        p["small"] & (p["body"] > 0) & (p["bodylo"] > p["hl2"])
        & (p["dn"] >= FACTOR * p["body"]) & (~p["hasup"]) & p["uptrend"]
    )


def shooting_star(p):
    return (
        p["small"] & (p["body"] > 0) & (p["bodyhi"] < p["hl2"])
        & (p["up"] >= FACTOR * p["body"]) & (~p["hasdn"]) & p["uptrend"]
    )


def inverted_hammer(p):
    return (
        p["small"] & (p["body"] > 0) & (p["bodyhi"] < p["hl2"])
        & (p["up"] >= FACTOR * p["body"]) & (~p["hasdn"]) & p["downtrend"]
    )


def morning_star(p):
    return (
        p["long"].shift(2) & p["small"].shift(1) & p["long"] & p["downtrend"]
        & p["black"].shift(2) & (p["bodyhi"].shift(1) < p["bodylo"].shift(2))
        & p["white"] & (p["bodyhi"] >= p["bodymid"].shift(2))
        & (p["bodyhi"] < p["bodyhi"].shift(2))
        & (p["bodyhi"].shift(1) < p["bodylo"])
    )


def evening_star(p):
    return (
        p["long"].shift(2) & p["small"].shift(1) & p["long"] & p["uptrend"]
        & p["white"].shift(2) & (p["bodylo"].shift(1) > p["bodyhi"].shift(2))
        & p["black"] & (p["bodylo"] <= p["bodymid"].shift(2))
        & (p["bodylo"] > p["bodylo"].shift(2))
        & (p["bodylo"].shift(1) > p["bodyhi"])
    )


def marubozu_white(p):
    return (
        p["white"] & p["long"] & (p["up"] <= 0.05 * p["body"])
        & (p["dn"] <= 0.05 * p["body"])
    )


def marubozu_black(p):
    return (
        p["black"] & p["long"] & (p["up"] <= 0.05 * p["body"])
        & (p["dn"] <= 0.05 * p["body"])
    )


def doji(p):
    dragonfly = p["is_doji_body"] & (p["up"] <= p["body"])
    gravestone = p["is_doji_body"] & (p["dn"] <= p["body"])
    return p["doji"] & (~dragonfly) & (~gravestone)


def gravestone_doji(p):
    return p["is_doji_body"] & (p["dn"] <= p["body"])


def dragonfly_doji(p):
    return p["is_doji_body"] & (p["up"] <= p["body"])


def harami_cross_bullish(p):
    return (
        p["long"].shift(1) & p["black"].shift(1) & p["downtrend"].shift(1)
        & p["is_doji_body"]
        & (p["h"] <= p["bodyhi"].shift(1)) & (p["l"] >= p["bodylo"].shift(1))
    )


def harami_cross_bearish(p):
    return (
        p["long"].shift(1) & p["white"].shift(1) & p["uptrend"].shift(1)
        & p["is_doji_body"]
        & (p["h"] <= p["bodyhi"].shift(1)) & (p["l"] >= p["bodylo"].shift(1))
    )


def harami_bullish(p):
    return (
        p["long"].shift(1) & p["black"].shift(1) & p["downtrend"].shift(1)
        & p["white"] & p["small"]
        & (p["h"] <= p["bodyhi"].shift(1)) & (p["l"] >= p["bodylo"].shift(1))
    )


def harami_bearish(p):
    return (
        p["long"].shift(1) & p["white"].shift(1) & p["uptrend"].shift(1)
        & p["black"] & p["small"]
        & (p["h"] <= p["bodyhi"].shift(1)) & (p["l"] >= p["bodylo"].shift(1))
    )


def long_lower_shadow(p):
    return p["dn"] > p["rng"] * 0.75


def long_upper_shadow(p):
    return p["up"] > p["rng"] * 0.75


def spinning_top_white(p):
    return (
        (p["dn"] >= p["rng"] * 0.34) & (p["up"] >= p["rng"] * 0.34)
        & (~p["is_doji_body"]) & p["white"]
    )


def spinning_top_black(p):
    return (
        (p["dn"] >= p["rng"] * 0.34) & (p["up"] >= p["rng"] * 0.34)
        & (~p["is_doji_body"]) & p["black"]
    )


def three_white_soldiers(p):
    long3 = p["long"] & p["long"].shift(1) & p["long"].shift(2)
    white3 = p["white"] & p["white"].shift(1) & p["white"].shift(2)
    rising = (p["c"] > p["c"].shift(1)) & (p["c"].shift(1) > p["c"].shift(2))
    opens = (
        (p["o"] < p["c"].shift(1)) & (p["o"] > p["o"].shift(1))
        & (p["o"].shift(1) < p["c"].shift(2)) & (p["o"].shift(1) > p["o"].shift(2))
    )
    no_up = (
        (p["rng"] * 0.05 > p["up"])
        & (p["rng"].shift(1) * 0.05 > p["up"].shift(1))
        & (p["rng"].shift(2) * 0.05 > p["up"].shift(2))
    )
    return long3 & white3 & rising & opens & no_up


def three_black_crows(p):
    long3 = p["long"] & p["long"].shift(1) & p["long"].shift(2)
    black3 = p["black"] & p["black"].shift(1) & p["black"].shift(2)
    falling = (p["c"] < p["c"].shift(1)) & (p["c"].shift(1) < p["c"].shift(2))
    opens = (
        (p["o"] > p["c"].shift(1)) & (p["o"] < p["o"].shift(1))
        & (p["o"].shift(1) > p["c"].shift(2)) & (p["o"].shift(1) < p["o"].shift(2))
    )
    no_dn = (
        (p["rng"] * 0.05 > p["dn"])
        & (p["rng"].shift(1) * 0.05 > p["dn"].shift(1))
        & (p["rng"].shift(2) * 0.05 > p["dn"].shift(2))
    )
    return long3 & black3 & falling & opens & no_dn


def bullish_engulfing(p):
    return (
        p["downtrend"] & p["white"] & p["long"]
        & p["black"].shift(1) & p["small"].shift(1)
        & (p["c"] >= p["o"].shift(1)) & (p["o"] <= p["c"].shift(1))
        & ((p["c"] > p["o"].shift(1)) | (p["o"] < p["c"].shift(1)))
    )


def bearish_engulfing(p):
    return (
        p["uptrend"] & p["black"] & p["long"]
        & p["white"].shift(1) & p["small"].shift(1)
        & (p["c"] <= p["o"].shift(1)) & (p["o"] >= p["c"].shift(1))
        & ((p["c"] < p["o"].shift(1)) | (p["o"] > p["c"].shift(1)))
    )


def abandoned_baby_bullish(p):
    return (
        p["downtrend"].shift(2) & p["black"].shift(2) & p["is_doji_body"].shift(1)
        & (p["l"].shift(2) > p["h"].shift(1)) & p["white"]
        & (p["h"].shift(1) < p["l"])
    )


def abandoned_baby_bearish(p):
    return (
        p["uptrend"].shift(2) & p["white"].shift(2) & p["is_doji_body"].shift(1)
        & (p["h"].shift(2) < p["l"].shift(1)) & p["black"]
        & (p["l"].shift(1) > p["h"])
    )


def tri_star_bullish(p):
    three = p["doji"] & p["doji"].shift(1) & p["doji"].shift(2)
    gap_down = p["bodylo"].shift(1) > p["bodyhi"].shift(2)
    gap_up = p["bodyhi"].shift(1) < p["bodylo"]
    return three & p["downtrend"].shift(2) & gap_down & gap_up


def tri_star_bearish(p):
    three = p["doji"] & p["doji"].shift(1) & p["doji"].shift(2)
    gap_up = p["bodyhi"].shift(1) < p["bodylo"].shift(2)
    gap_down = p["bodylo"].shift(1) > p["bodyhi"]
    return three & p["uptrend"].shift(2) & gap_up & gap_down


def kicking_bullish(p):
    marubozu = p["long"] & (p["up"] <= 0.05 * p["body"]) & (p["dn"] <= 0.05 * p["body"])
    return marubozu.shift(1) & p["black"].shift(1) & marubozu & p["white"] & (p["h"].shift(1) < p["l"])


def kicking_bearish(p):
    marubozu = p["long"] & (p["up"] <= 0.05 * p["body"]) & (p["dn"] <= 0.05 * p["body"])
    return marubozu.shift(1) & p["white"].shift(1) & marubozu & p["black"] & (p["l"].shift(1) > p["h"])


# ---------------------------------------------------------------------------
# Detector wrapper
# ---------------------------------------------------------------------------
class CandlePattern(PatternDetector):
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

    def detect(self, df: pd.DataFrame, cfg: Mapping[str, Any]) -> List[PatternMatch]:
        if len(df) < max(self.span + 2, 60):
            return []
        prepped = _prep(df, cfg)
        mask = self.fn(prepped).fillna(False).to_numpy(dtype=bool)
        matches: List[PatternMatch] = []
        for idx in np.nonzero(mask)[0]:
            i = int(idx)
            start = i - self.span + 1
            if start < 0:
                continue
            matches.append(
                PatternMatch(
                    name=self.name,
                    direction=self.direction,
                    end_idx=i,
                    start_idx=start,
                    meta={
                        "kind": self.kind,
                        "span": self.span,
                        "expect_prior_trend": self.expect_prior_trend,
                    },
                )
            )
        return matches


# name, direction, function, span, expected prior trend
CANDLES: list[tuple[str, str, Callable, int, str | None]] = [
    # --- single candle ---
    ("hammer", "bullish", hammer, 1, "down"),
    ("hanging_man", "bearish", hanging_man, 1, "up"),
    ("shooting_star", "bearish", shooting_star, 1, "up"),
    ("inverted_hammer", "bullish", inverted_hammer, 1, "down"),
    ("marubozu_white", "bullish", marubozu_white, 1, None),
    ("marubozu_black", "bearish", marubozu_black, 1, None),
    ("doji", "neutral", doji, 1, None),
    ("gravestone_doji", "bearish", gravestone_doji, 1, None),
    ("dragonfly_doji", "bullish", dragonfly_doji, 1, None),
    ("long_lower_shadow", "bullish", long_lower_shadow, 1, None),
    ("long_upper_shadow", "bearish", long_upper_shadow, 1, None),
    ("spinning_top_white", "neutral", spinning_top_white, 1, None),
    ("spinning_top_black", "neutral", spinning_top_black, 1, None),
    # --- two candles ---
    ("on_neck", "bearish", on_neck, 2, "down"),
    ("rising_window", "bullish", rising_window, 2, "up"),
    ("falling_window", "bearish", falling_window, 2, "down"),
    ("tweezer_top", "bearish", tweezer_top, 2, "up"),
    ("tweezer_bottom", "bullish", tweezer_bottom, 2, "down"),
    ("dark_cloud_cover", "bearish", dark_cloud_cover, 2, "up"),
    ("piercing_line", "bullish", piercing_line, 2, "down"),
    ("bullish_engulfing", "bullish", bullish_engulfing, 2, "down"),
    ("bearish_engulfing", "bearish", bearish_engulfing, 2, "up"),
    ("doji_star_bullish", "bullish", doji_star_bullish, 2, "down"),
    ("doji_star_bearish", "bearish", doji_star_bearish, 2, "up"),
    ("harami_bullish", "bullish", harami_bullish, 2, "down"),
    ("harami_bearish", "bearish", harami_bearish, 2, "up"),
    ("harami_cross_bullish", "bullish", harami_cross_bullish, 2, "down"),
    ("harami_cross_bearish", "bearish", harami_cross_bearish, 2, "up"),
    ("kicking_bullish", "bullish", kicking_bullish, 2, None),
    ("kicking_bearish", "bearish", kicking_bearish, 2, None),
    # --- three candles ---
    ("morning_star", "bullish", morning_star, 3, "down"),
    ("evening_star", "bearish", evening_star, 3, "up"),
    ("morning_doji_star", "bullish", morning_doji_star, 3, "down"),
    ("evening_doji_star", "bearish", evening_doji_star, 3, "up"),
    ("three_white_soldiers", "bullish", three_white_soldiers, 3, None),
    ("three_black_crows", "bearish", three_black_crows, 3, None),
    ("abandoned_baby_bullish", "bullish", abandoned_baby_bullish, 3, "down"),
    ("abandoned_baby_bearish", "bearish", abandoned_baby_bearish, 3, "up"),
    ("tri_star_bullish", "bullish", tri_star_bullish, 3, "down"),
    ("tri_star_bearish", "bearish", tri_star_bearish, 3, "up"),
    ("downside_tasuki_gap", "bearish", downside_tasuki_gap, 3, "down"),
    ("upside_tasuki_gap", "bullish", upside_tasuki_gap, 3, "up"),
    # --- five candles ---
    ("falling_three_methods", "bearish", falling_three_methods, 5, "down"),
    ("rising_three_methods", "bullish", rising_three_methods, 5, "up"),
]

for _name, _dir, _fn, _span, _trend in CANDLES:
    register(CandlePattern(_name, _dir, _fn, _span, _trend))
