import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def _ohlc_from_close(close, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = np.asarray(close, dtype=float)
    n = len(close)
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.004, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.004, n))
    volume = rng.uniform(1_000_000, 2_000_000, n)
    index = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=index,
    )


@pytest.fixture
def double_bottom_df() -> pd.DataFrame:
    """A clean double bottom that breaks out above the neckline."""
    segments = [
        (100.0, 82.0, 60),  # downtrend into the first low
        (82.0, 90.0, 12),   # rally to the neckline
        (90.0, 82.0, 12),   # pullback to the second low
        (82.0, 96.0, 22),   # breakout
    ]
    close: list[float] = []
    for start, end, count in segments:
        close.extend(np.linspace(start, end, count, endpoint=False).tolist())
    close.append(96.0)
    return _ohlc_from_close(close, seed=1)


@pytest.fixture
def random_df() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0002, 0.012, 260)
    close = 100 * np.exp(np.cumsum(returns))
    return _ohlc_from_close(close, seed=7)


@pytest.fixture
def cfg() -> dict:
    from puzzlebook.config import load_config

    return load_config()
