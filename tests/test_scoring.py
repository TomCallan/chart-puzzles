import numpy as np
import pandas as pd

from puzzlebook.patterns.base import PatternMatch
from puzzlebook.patterns.scoring import _context_factor, _prominence, cleanliness_score


def _frame(lows: list[float]) -> pd.DataFrame:
    n = len(lows)
    index = pd.bdate_range("2020-01-01", periods=n)
    low = np.asarray(lows, dtype=float)
    close = low + 1.0
    open_ = close - 0.2
    high = close + 0.2
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1_000_000.0),
        },
        index=index,
    )


def test_prominence_rewards_new_extremes():
    prior = [100, 101, 99, 102, 98, 100, 101, 99, 100, 101, 100]
    buried = _frame(prior + [100.5])       # last low sits inside the range
    protruding = _frame(prior + [90.0])    # last low pokes far below
    m_buried = PatternMatch("hammer", "bullish", len(buried) - 1, len(buried) - 1)
    m_prot = PatternMatch("hammer", "bullish", len(protruding) - 1, len(protruding) - 1)
    assert _prominence(protruding, m_prot) > _prominence(buried, m_buried)
    assert _prominence(buried, m_buried) <= 0.6
    assert _prominence(protruding, m_prot) > 0.9


def test_context_does_not_saturate_for_candlesticks(cfg):
    df = _frame([100.0] * 60)
    early = PatternMatch("hammer", "bullish", 5, 5, meta={"kind": "candlestick"})
    late = PatternMatch("hammer", "bullish", 55, 55, meta={"kind": "candlestick"})
    assert _context_factor(df, early, cfg) < 1.0
    assert _context_factor(df, late, cfg) == 1.0


def test_cleanliness_score_is_bounded(cfg):
    df = _frame(list(np.linspace(110, 100, 40)) + [99.0])
    match = PatternMatch(
        "hammer", "bullish", 40, 40, meta={"kind": "candlestick", "expect_prior_trend": "down"}
    )
    score = cleanliness_score(df, match, cfg)
    assert 0.0 <= score <= 100.0
    assert set(match.meta["factors"]) == {"trend", "volume", "size", "quality", "context"}
