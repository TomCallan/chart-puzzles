"""Configuration loading with sane defaults and deep-merge overrides."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

import yaml

# ---------------------------------------------------------------------------
# Default configuration. Everything is overridable from config.yaml.
# ---------------------------------------------------------------------------
DEFAULTS: dict[str, Any] = {
    "universe": [
        "SPY",
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "META",
        "GOOGL",
        "TSLA",
        "AMD",
        "NFLX",
        "JPM",
        "XOM",
        "BA",
        "DIS",
        "INTC",
        "KO",
        "WMT",
        "CVX",
        "PFE",
        "GE",
    ],
    "data": {
        "start": "2016-01-01",
        "end": None,
        "interval": "1d",
        "source": "yfinance",  # yfinance | alpaca
        "cache_dir": ".cache/ohlcv",
        "use_cache": True,
        "max_symbols": None,
    },
    "patterns": {
        "min_score": 85.0,
        "require_hit": False,
        "pivot_window": 5,
        "min_separation": 8,
        "min_history_bars": 40,
        "max_per_symbol": 3,
        "dedupe_bars": 5,
        "weights": {
            "trend": 0.25,
            "volume": 0.20,
            "size": 0.15,
            "quality": 0.30,
            "context": 0.10,
        },
        "candlestick": {
            "enabled": True,
            "names": [
                "bullish_engulfing",
                "bearish_engulfing",
                "hammer",
                "shooting_star",
                "morning_star",
                "evening_star",
                "bullish_harami",
                "bearish_harami",
                "piercing_line",
                "dark_cloud_cover",
                "three_white_soldiers",
                "three_black_crows",
                "doji",
            ],
        },
        "chart": {
            "enabled": True,
            "names": [
                "double_bottom",
                "double_top",
                "head_and_shoulders",
                "inverse_head_and_shoulders",
            ],
            "tolerance": 0.035,      # 3.5% price tolerance for equal lows/highs
            "min_depth_atr": 1.5,    # neckline depth relative to ATR
        },
    },
    "chart": {
        "dpi": 300,
        "lookback_bars": 90,
        "resolution_bars": 25,
        "target_r": 2.0,
        "puzzle_clue": "none",
        "puzzle_clue_mix": None,
        "min_history_bars": 40,
        "figsize": [7.0, 5.0],
        "show_volume": True,
        "yaxis_location": "right",
        "show_x_labels": False,
        "line_width": 1.1,
        "grid": True,
    },
    "book": {
        "title": "The Chart Pattern Puzzle Book",
        "subtitle": "Identify the Pattern. Mark the Levels.",
        "author": "Howard Hughes",
        "edition": "First Edition",
        "trim": {"width": 8.5, "height": 11.0},
        # KDP no-bleed minimums. `inside` is the binding/gutter margin and
        # depends on final page count:
        #   24-150 pp -> 0.375", 151-300 pp -> 0.625", 301-500 pp -> 0.875"
        "margins": {
            "inside": 0.375,
            "outside": 0.25,
            "top": 0.25,
            "bottom": 0.25,
        },
        "dot_grid": {
            "color": "#dcdcdc",
            "spacing": 0.2,   # inches between dots
            "radius": 0.9,    # dot radius in px
        },
        "max_puzzles": 60,
        "show_page_numbers": True,
        "question_mix": {"identify": 40, "direction": 30, "levels": 30},
    },
    "output": {
        "charts_dir": "assets/charts",
        "manifest": "build/manifest.json",
        "pdf": "output/workbook.pdf",
        "answer_key_pdf": "output/answer_key.pdf",
        "render_answer_key": True,
    },
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` onto a copy of ``base``."""
    result: dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], Mapping)
            and isinstance(value, Mapping)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load config.yaml (if present) merged over the built-in defaults."""
    if path is None:
        candidate = PROJECT_ROOT / "config.yaml"
    else:
        candidate = Path(path)
    overrides: dict[str, Any] = {}
    if candidate.exists():
        with candidate.open("r", encoding="utf-8") as handle:
            overrides = yaml.safe_load(handle) or {}
    return _deep_merge(DEFAULTS, overrides)


def resolve_path(cfg: Mapping[str, Any], value: str | Path) -> Path:
    """Resolve a possibly-relative path against the project root."""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path
