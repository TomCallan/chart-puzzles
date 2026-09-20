"""Market data fetching with a pluggable source and a local cache.

Only yfinance is required. Alpaca is supported when the optional
``alpaca-py`` package and credentials are available.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Return a clean OHLCV frame with a tz-naive DatetimeIndex."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(col).title() for col in df.columns]
    present = [col for col in OHLCV_COLUMNS if col in df.columns]
    df = df[present]
    df = df.dropna(subset=[c for c in ("Open", "High", "Low", "Close") if c in df])
    index = pd.to_datetime(df.index)
    if getattr(index, "tz", None) is not None:
        index = index.tz_localize(None)
    df.index = index
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if "Volume" in df:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0.0)
    for column in ("Open", "High", "Low", "Close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["Open", "High", "Low", "Close"])


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
def _fetch_yfinance(
    symbol: str, start: str, end: str | None, interval: str
) -> pd.DataFrame:
    import yfinance as yf  # imported lazily so tests stay light

    raw = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise ValueError(f"No data returned for {symbol!r}")
    return _normalize(raw)


def _fetch_alpaca(
    symbol: str, start: str, end: str | None, interval: str
) -> pd.DataFrame:
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "alpaca-py is not installed. Run `pip install alpaca-py` or set "
            "data.source to 'yfinance'."
        ) from exc

    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError(
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY to use the alpaca source."
        )

    timeframe = (
        TimeFrame(1, TimeFrameUnit.Day)
        if interval == "1d"
        else TimeFrame(1, TimeFrameUnit.Hour)
    )
    client = StockHistoricalDataClient(key, secret)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        adjustment="all",
    )
    bars = client.get_stock_bars(request).df
    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.droplevel(0)
    bars = bars.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    return _normalize(bars)


_SOURCES = {"yfinance": _fetch_yfinance, "alpaca": _fetch_alpaca}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _cache_path(
    cache_dir: Path, symbol: str, interval: str, start: str, end: str | None
) -> Path:
    key = f"{symbol}_{interval}_{start}_{end or 'latest'}".replace("/", "-")
    return cache_dir / f"{key}.parquet"


def fetch_ohlcv(
    symbol: str,
    cfg: Mapping[str, Any],
    use_cache: bool | None = None,
) -> pd.DataFrame:
    """Fetch (and cache) daily OHLCV data for ``symbol``."""
    data_cfg = cfg["data"]
    start = str(data_cfg["start"])
    end = data_cfg.get("end")
    end = str(end) if end else None
    interval = str(data_cfg["interval"])
    source = str(data_cfg["source"])
    if source not in _SOURCES:
        raise ValueError(f"Unknown data source {source!r}. Use one of {list(_SOURCES)}")

    if use_cache is None:
        use_cache = bool(data_cfg.get("use_cache", True))
    cache_dir = Path(data_cfg["cache_dir"]).expanduser()
    cache_file = _cache_path(cache_dir, symbol, interval, start, end)

    if use_cache and cache_file.exists():
        try:
            return pd.read_parquet(cache_file)
        except Exception:  # corrupt cache -> refetch
            cache_file.unlink(missing_ok=True)

    df = _SOURCES[source](symbol, start, end, interval)
    if use_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            df.to_parquet(cache_file)
        except Exception:
            pass
    return df


def load_universe(cfg: Mapping[str, Any]) -> list[str]:
    universe = list(cfg["universe"])
    cap = cfg["data"].get("max_symbols")
    if cap:
        universe = universe[: int(cap)]
    return universe
