"""Chart-pattern detectors (double top/bottom, head & shoulders).

Chart patterns are built from swing pivots rather than single candles. The
completion ("puzzle moment") is the breakout bar that confirms the pattern,
which is also the last bar we are allowed to render.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from .base import PatternDetector, PatternMatch, register
from ..indicators import atr as _atr


def _pivots(df: pd.DataFrame, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (high_pivot_indices, low_pivot_indices)."""
    n = len(df)
    if n < 2 * window + 1:
        return np.array([], dtype=int), np.array([], dtype=int)
    highs = argrelextrema(df["High"].to_numpy(), np.greater, order=window)[0]
    lows = argrelextrema(df["Low"].to_numpy(), np.less, order=window)[0]
    return highs, lows


class _ChartPattern(PatternDetector):
    kind = "chart"

    def _quality(
        self, equality: float, depth: float, atr_value: float, tolerance: float
    ) -> float:
        symmetry = max(0.0, 1.0 - (equality / tolerance if tolerance else 0.0))
        depth_quality = float(np.clip(depth / (3.0 * atr_value), 0.0, 1.0))
        return float(np.clip(0.5 * symmetry + 0.5 * depth_quality, 0.0, 1.0))


class DoubleBottom(_ChartPattern):
    name = "double_bottom"
    direction = "bullish"

    def detect(self, df: pd.DataFrame, cfg: Mapping[str, Any]) -> List[PatternMatch]:
        pc = cfg["patterns"]["chart"]
        tol = float(pc["tolerance"])
        min_sep = int(cfg["patterns"]["min_separation"])
        max_span = int(cfg["patterns"].get("max_pivot_span", 80))
        min_depth = float(pc["min_depth_atr"])
        max_depth_pct = float(pc.get("max_depth_pct", 0.18))
        max_breakout = int(cfg["patterns"].get("max_breakout_bars", 50))
        atr = _atr(df)
        _, lows = _pivots(df, int(cfg["patterns"]["pivot_window"]))
        high = df["High"].to_numpy()
        low = df["Low"].to_numpy()
        close = df["Close"].to_numpy()
        matches: List[PatternMatch] = []
        for a in range(len(lows)):
            for b in range(a + 1, len(lows)):
                i, j = int(lows[a]), int(lows[b])
                if j - i < min_sep:
                    continue
                if j - i > max_span:
                    break
                l1, l2 = low[i], low[j]
                equality = abs(l1 - l2) / max(l1, l2)
                if equality > tol:
                    continue
                segment = high[i + 1 : j]
                if segment.size == 0:
                    continue
                peak_idx = i + 1 + int(np.argmax(segment))
                peak = high[peak_idx]
                depth = peak - min(l1, l2)
                if depth < min_depth * atr.iloc[j]:
                    continue
                if depth / max(min(l1, l2), 1e-9) > max_depth_pct:
                    continue
                after = close[j + 1 :]
                breakout = np.nonzero(after > peak)[0]
                if breakout.size == 0:
                    continue
                if int(breakout[0]) > max_breakout:
                    continue
                end_idx = j + 1 + int(breakout[0])
                matches.append(
                    PatternMatch(
                        name=self.name,
                        direction=self.direction,
                        end_idx=end_idx,
                        start_idx=i,
                        meta={
                            "kind": self.kind,
                            "expect_prior_trend": "down",
                            "neckline": float(peak),
                            "low1_idx": i,
                            "low2_idx": j,
                            "peak_idx": peak_idx,
                            "quality": self._quality(
                                equality, depth, float(atr.iloc[j]), tol
                            ),
                        },
                    )
                )
        return matches


class DoubleTop(_ChartPattern):
    name = "double_top"
    direction = "bearish"

    def detect(self, df: pd.DataFrame, cfg: Mapping[str, Any]) -> List[PatternMatch]:
        pc = cfg["patterns"]["chart"]
        tol = float(pc["tolerance"])
        min_sep = int(cfg["patterns"]["min_separation"])
        max_span = int(cfg["patterns"].get("max_pivot_span", 80))
        min_depth = float(pc["min_depth_atr"])
        max_depth_pct = float(pc.get("max_depth_pct", 0.18))
        max_breakout = int(cfg["patterns"].get("max_breakout_bars", 50))
        atr = _atr(df)
        highs, _ = _pivots(df, int(cfg["patterns"]["pivot_window"]))
        high = df["High"].to_numpy()
        low = df["Low"].to_numpy()
        close = df["Close"].to_numpy()
        matches: List[PatternMatch] = []
        for a in range(len(highs)):
            for b in range(a + 1, len(highs)):
                i, j = int(highs[a]), int(highs[b])
                if j - i < min_sep:
                    continue
                if j - i > max_span:
                    break
                h1, h2 = high[i], high[j]
                equality = abs(h1 - h2) / max(h1, h2)
                if equality > tol:
                    continue
                segment = low[i + 1 : j]
                if segment.size == 0:
                    continue
                trough_idx = i + 1 + int(np.argmin(segment))
                trough = low[trough_idx]
                depth = max(h1, h2) - trough
                if depth < min_depth * atr.iloc[j]:
                    continue
                if depth / max(max(h1, h2), 1e-9) > max_depth_pct:
                    continue
                after = close[j + 1 :]
                breakdown = np.nonzero(after < trough)[0]
                if breakdown.size == 0:
                    continue
                if int(breakdown[0]) > max_breakout:
                    continue
                end_idx = j + 1 + int(breakdown[0])
                matches.append(
                    PatternMatch(
                        name=self.name,
                        direction=self.direction,
                        end_idx=end_idx,
                        start_idx=i,
                        meta={
                            "kind": self.kind,
                            "expect_prior_trend": "up",
                            "neckline": float(trough),
                            "high1_idx": i,
                            "high2_idx": j,
                            "trough_idx": trough_idx,
                            "quality": self._quality(
                                equality, depth, float(atr.iloc[j]), tol
                            ),
                        },
                    )
                )
        return matches


class HeadAndShoulders(_ChartPattern):
    name = "head_and_shoulders"
    direction = "bearish"

    def detect(self, df: pd.DataFrame, cfg: Mapping[str, Any]) -> List[PatternMatch]:
        return self._detect(df, cfg, inverse=False)

    def _detect(
        self, df: pd.DataFrame, cfg: Mapping[str, Any], inverse: bool
    ) -> List[PatternMatch]:
        pc = cfg["patterns"]["chart"]
        tol = float(pc["tolerance"])
        min_sep = int(cfg["patterns"]["min_separation"])
        max_span = int(cfg["patterns"].get("max_pivot_span", 80))
        min_depth = float(pc["min_depth_atr"])
        max_depth_pct = float(pc.get("max_depth_pct", 0.18))
        max_breakout = int(cfg["patterns"].get("max_breakout_bars", 50))
        atr = _atr(df)
        highs, lows = _pivots(df, int(cfg["patterns"]["pivot_window"]))
        pivots: Sequence[int] = lows if inverse else highs
        outer = df["Low"].to_numpy() if inverse else df["High"].to_numpy()
        inner = df["High"].to_numpy() if inverse else df["Low"].to_numpy()
        close = df["Close"].to_numpy()
        matches: List[PatternMatch] = []
        for a in range(len(pivots)):
            for b in range(a + 1, len(pivots)):
                if int(pivots[b]) - int(pivots[a]) > max_span:
                    break
                for c in range(b + 1, len(pivots)):
                    i, j, k = int(pivots[a]), int(pivots[b]), int(pivots[c])
                    if k - j > max_span:
                        break
                    if (j - i) < min_sep or (k - j) < min_sep:
                        continue
                    p1, p2, p3 = outer[i], outer[j], outer[k]
                    if inverse:
                        head_ok = p2 < p1 and p2 < p3
                    else:
                        head_ok = p2 > p1 and p2 > p3
                    if not head_ok:
                        continue
                    equality = abs(p1 - p3) / max(p1, p3)
                    if equality > tol:
                        continue
                    seg1 = inner[i + 1 : j]
                    seg2 = inner[j + 1 : k]
                    if seg1.size == 0 or seg2.size == 0:
                        continue
                    if inverse:
                        t1_idx = i + 1 + int(np.argmax(seg1))
                        t2_idx = j + 1 + int(np.argmax(seg2))
                        neck1 = float(seg1.max())
                        neck2 = float(seg2.max())
                        neckline = max(neck1, neck2)
                        prominence = min(p1, p3) - p2
                    else:
                        t1_idx = i + 1 + int(np.argmin(seg1))
                        t2_idx = j + 1 + int(np.argmin(seg2))
                        neck1 = float(seg1.min())
                        neck2 = float(seg2.min())
                        neckline = min(neck1, neck2)
                        prominence = p2 - max(p1, p3)
                    if prominence < min_depth * atr.iloc[j]:
                        continue
                    neckline_depth = (p2 - neckline) if not inverse else (neckline - p2)
                    if neckline_depth / max(abs(p2), 1e-9) > max_depth_pct:
                        continue
                    after = close[k + 1 :]
                    if inverse:
                        breakout = np.nonzero(after > neckline)[0]
                    else:
                        breakout = np.nonzero(after < neckline)[0]
                    if breakout.size == 0:
                        continue
                    if int(breakout[0]) > max_breakout:
                        continue
                    end_idx = k + 1 + int(breakout[0])
                    matches.append(
                        PatternMatch(
                            name=self.name,
                            direction=self.direction,
                            end_idx=end_idx,
                            start_idx=i,
                            meta={
                                "kind": self.kind,
                                "expect_prior_trend": "up" if not inverse else "down",
                                "neckline": neckline,
                                "shoulder1_idx": i,
                                "head_idx": j,
                                "shoulder2_idx": k,
                                "trough1_idx": t1_idx,
                                "trough2_idx": t2_idx,
                                "quality": self._quality(
                                    equality,
                                    float(prominence),
                                    float(atr.iloc[j]),
                                    tol,
                                ),
                            },
                        )
                    )
        return matches


class InverseHeadAndShoulders(HeadAndShoulders):
    name = "inverse_head_and_shoulders"
    direction = "bullish"

    def detect(self, df: pd.DataFrame, cfg: Mapping[str, Any]) -> List[PatternMatch]:
        return self._detect(df, cfg, inverse=True)


register(DoubleBottom())
register(DoubleTop())
register(HeadAndShoulders())
register(InverseHeadAndShoulders())
