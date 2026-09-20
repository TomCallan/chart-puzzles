"""Pure black-and-white chart rendering with mplfinance.

Two variants are produced per puzzle:

* **puzzle** - candles stop at the pattern completion ("puzzle moment") and the
  axis is extended with blank space so the reader can draw their answer.
* **answer** - the same candles plus ``resolution_bars`` of future bars, with
  the future region shaded and ideal entry/stop/target lines drawn.

Up candles are hollow (white fill, black outline), down candles are solid
black. Bars after the puzzle moment never appear on the puzzle chart.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .patterns.base import PatternMatch


def _build_style(mplfinance: Any, cfg: Mapping[str, Any]) -> Any:
    chart_cfg = cfg["chart"]
    market_colors = mplfinance.make_marketcolors(
        up="white",
        down="black",
        edge="black",
        wick="black",
        ohlc="black",
        volume={"up": "#d9d9d9", "down": "#4d4d4d"},
    )
    return mplfinance.make_mpf_style(
        base_mpf_style="classic",
        marketcolors=market_colors,
        gridstyle="-" if chart_cfg.get("grid", True) else "",
        gridcolor="#dddddd",
        facecolor="white",
        figcolor="white",
        rc={
            "axes.edgecolor": "black",
            "axes.linewidth": 0.6,
            "axes.labelcolor": "black",
            "font.size": 7,
            "xtick.color": "black",
            "ytick.color": "black",
        },
    )


def _view_bounds(
    df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any], mode: str
) -> tuple[int, int]:
    """Start/end positions that always include the whole pattern plus context."""
    lookback = int(cfg["chart"]["lookback_bars"])
    resolution = int(cfg["chart"]["resolution_bars"])
    context = int(cfg["chart"].get("context_bars", 15))
    start = max(0, min(match.start_idx - context, match.end_idx - lookback + 1))
    if mode == "answer":
        end = min(len(df) - 1, match.end_idx + resolution)
    else:
        end = match.end_idx
    return start, end


def _puzzle_view(
    df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any]
) -> pd.DataFrame:
    """Bars up to and including the puzzle moment (never any future bars)."""
    start, end = _view_bounds(df, match, cfg, "puzzle")
    return df.iloc[start : end + 1]


def _answer_view(
    df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any]
) -> pd.DataFrame:
    """Puzzle bars plus ``resolution_bars`` of future bars."""
    start, end = _view_bounds(df, match, cfg, "answer")
    return df.iloc[start : end + 1]


def _view(
    df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any], mode: str = "puzzle"
) -> pd.DataFrame:
    if mode == "answer":
        return _answer_view(df, match, cfg)
    return _puzzle_view(df, match, cfg)


def _pos(view: pd.DataFrame, df: pd.DataFrame, idx: int) -> int | None:
    try:
        return int(view.index.get_loc(df.index[idx]))
    except KeyError:
        return None


def _set_xlim(axes: list[Any], left: float, right: float) -> None:
    for axis in axes:
        try:
            axis.set_xlim(left, right)
        except Exception:
            pass


def _whiteout(axis: Any, left: float, right: float) -> None:
    """Hide everything in an x-range (used to blank out future bars)."""
    if right <= left:
        return
    axis.axvspan(left, right, facecolor="white", edgecolor="none", zorder=6)
    for tick in axis.get_yticks():
        axis.axhline(tick, color="#dddddd", linewidth=0.6, zorder=6.2)


def _draw_pattern(
    ax: Any, view: pd.DataFrame, df: pd.DataFrame, match: PatternMatch, cfg: Mapping[str, Any]
) -> None:
    """Draw the detected pattern's geometry on the answer chart."""
    line_width = float(cfg["chart"]["line_width"])
    meta = match.meta

    def pos(idx: int | None) -> int | None:
        return None if idx is None else _pos(view, df, idx)

    def price_at(position: int, use_high: bool) -> float:
        return float(view["High"].iloc[position] if use_high else view["Low"].iloc[position])

    # --- candlestick patterns: shade the candles involved -------------------
    if meta.get("kind") == "candlestick":
        start = pos(match.start_idx)
        end = pos(match.end_idx)
        if start is not None and end is not None:
            ax.axvspan(start - 0.5, end + 0.5, color="black", alpha=0.12, zorder=0)
        return

    # --- chart patterns: neckline, connecting lines, labelled pivots --------
    name = match.name
    if name == "double_top":
        points = [
            (meta.get("high1_idx"), "H1", True),
            (meta.get("trough_idx"), "N", False),
            (meta.get("high2_idx"), "H2", True),
        ]
    elif name == "double_bottom":
        points = [
            (meta.get("low1_idx"), "L1", False),
            (meta.get("peak_idx"), "N", True),
            (meta.get("low2_idx"), "L2", False),
        ]
    elif name in ("head_and_shoulders", "inverse_head_and_shoulders"):
        inverse = name.startswith("inverse")
        points = [
            (meta.get("shoulder1_idx"), "LS", not inverse),
            (meta.get("trough1_idx"), "N1", inverse),
            (meta.get("head_idx"), "H", not inverse),
            (meta.get("trough2_idx"), "N2", inverse),
            (meta.get("shoulder2_idx"), "RS", not inverse),
        ]
    else:
        points = []

    neckline = meta.get("neckline")
    if neckline is not None:
        ax.axhline(
            neckline,
            color="black",
            linestyle=(0, (6, 4)),
            linewidth=line_width,
            zorder=2,
        )

    # connecting zig-zag through the pivots
    xs: list[int] = []
    ys: list[float] = []
    for idx, _label, use_high in points:
        position = pos(idx)
        if position is None:
            continue
        xs.append(position)
        ys.append(price_at(position, use_high))
    if len(xs) >= 2:
        ax.plot(xs, ys, color="black", linewidth=line_width, zorder=3)

    for idx, label, use_high in points:
        position = pos(idx)
        if position is None:
            continue
        y = price_at(position, use_high)
        ax.plot(
            position, y, marker="o", markersize=5, markerfacecolor="white",
            markeredgecolor="black", markeredgewidth=1.0, zorder=5,
        )
        ax.annotate(
            label,
            xy=(position, y),
            xytext=(0, 9 if use_high else -14),
            textcoords="offset points",
            ha="center",
            fontsize=7,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="black", lw=0.5),
            zorder=6,
        )

    if neckline is not None and xs:
        ax.annotate(
            "neckline",
            xy=(xs[0], neckline),
            xytext=(4, 4),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=6.5,
            style="italic",
            color="#333",
            zorder=6,
        )


def _annotate_answer(
    ax: Any,
    view: pd.DataFrame,
    df: pd.DataFrame,
    match: PatternMatch,
    cfg: Mapping[str, Any],
    puzzle_pos: int,
) -> None:
    """Shade the revealed region, draw the pattern geometry and trade levels."""
    from matplotlib.lines import Line2D

    line_width = float(cfg["chart"]["line_width"])
    n = len(view)

    # --- delineate question data (left) from answer data (right) -----------
    if puzzle_pos < n - 1:
        ax.axvspan(
            puzzle_pos + 0.5, n - 0.5, color="black", alpha=0.06, zorder=0
        )
        ax.text(
            (puzzle_pos + 0.5 + n - 0.5) / 2,
            float(view["High"].max()),
            "answer",
            ha="center",
            va="bottom",
            fontsize=6.5,
            style="italic",
            color="#555",
        )
    ax.axvline(
        x=puzzle_pos,
        color="black",
        linestyle=(0, (4, 4)),
        linewidth=line_width,
        alpha=0.9,
        zorder=3,
    )

    # --- the pattern itself ------------------------------------------------
    _draw_pattern(ax, view, df, match, cfg)

    # --- ideal entry / stop / target ---------------------------------------
    levels = match.meta.get("levels") or {}
    handles = []
    if levels:
        specs = [
            ("entry", "-", "Entry"),
            ("stop", (0, (4, 3)), "Stop"),
            ("target", (0, (1, 2)), "Target"),
        ]
        for key, linestyle, label in specs:
            value = levels.get(key)
            if value is None:
                continue
            ax.axhline(
                value,
                color="black",
                linestyle=linestyle,
                linewidth=line_width,
                alpha=0.9,
                zorder=2,
            )
            handles.append(
                Line2D([0], [0], color="black", linestyle=linestyle,
                       linewidth=line_width, label=f"{label} {value:g}")
            )
        ax.legend(
            handles=handles,
            loc="upper left",
            fontsize=6,
            framealpha=0.92,
            borderpad=0.4,
            handlelength=1.8,
        )

    ax.annotate(
        match.name.replace("_", " ").title(),
        xy=(puzzle_pos, float(view["High"].max())),
        xytext=(puzzle_pos, float(view["High"].max()) * 1.01),
        ha="right",
        va="bottom",
        fontsize=8,
        fontweight="bold",
        color="black",
    )


def render_chart(
    df: pd.DataFrame,
    match: PatternMatch,
    cfg: Mapping[str, Any],
    out_path: str | Path,
    mode: str = "puzzle",
    clue: str | None = None,
) -> Path:
    """Render ``match`` from ``df`` to a PNG. Returns the path.

    ``mode`` is ``puzzle`` or ``answer``. On the puzzle chart ``clue`` controls
    what is revealed after the puzzle moment:

    * ``none``   - nothing (blank drawing space)
    * ``volume`` - volume bars only (predict price from volume)
    * ``price``  - price bars only (predict volume from price)
    """
    import matplotlib

    matplotlib.use("Agg")
    import mplfinance as mpf

    chart_cfg = cfg["chart"]
    clue = (clue or chart_cfg.get("puzzle_clue", "none")).lower()
    if mode == "puzzle" and clue == "none":
        view = _puzzle_view(df, match, cfg)
        puzzle_pos = len(view) - 1
    else:
        view = _answer_view(df, match, cfg)
        puzzle_pos = _pos(view, df, match.end_idx)
        if puzzle_pos is None:
            puzzle_pos = len(view) - 1
    if view.empty:
        raise ValueError(f"Empty view for {match.symbol} {match.name}")

    style = _build_style(mpf, cfg)
    fig, axes = mpf.plot(
        view,
        type="candle",
        style=style,
        volume=bool(chart_cfg.get("show_volume", True)),
        returnfig=True,
        figsize=tuple(chart_cfg["figsize"]),
        ylabel="",
        ylabel_lower="",
        xlabel="",
        datetime_format="%b %y",
        xrotation=0,
        tight_layout=True,
        warn_too_much_data=1_000_000,
    )
    ax = axes[0]
    if chart_cfg.get("yaxis_location", "right") == "right":
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")

    if not chart_cfg.get("show_x_labels", False):
        for axis in axes:
            axis.tick_params(labelbottom=False)
    for axis in axes[2:]:
        axis.set_yticks([])
        axis.yaxis.set_visible(False)
    ax.spines["top"].set_visible(False)

    if mode == "puzzle":
        if clue == "none":
            # Blank drawing space to the right of the puzzle moment.
            resolution = int(chart_cfg["resolution_bars"])
            _set_xlim(axes, -0.5, puzzle_pos + resolution + 0.5)
        else:
            # Full width; blank out the future region according to the clue.
            _set_xlim(axes, -0.5, len(view) - 0.5)
            if clue != "price":
                _whiteout(axes[0], puzzle_pos + 0.5, len(view) - 0.5)
            if clue != "volume":
                for axis in axes[2:]:
                    _whiteout(axis, puzzle_pos + 0.5, len(view) - 0.5)
        ax.axvline(
            x=puzzle_pos,
            color="black",
            linestyle=(0, (4, 4)),
            linewidth=float(chart_cfg["line_width"]),
            alpha=0.9,
            zorder=8,
        )
    else:
        _annotate_answer(ax, view, df, match, cfg, puzzle_pos)
        _expand_ylim(ax, view, match)
        # Same x-scale as the puzzle chart so the two line up.
        _set_xlim(axes, -0.5, len(view) - 0.5)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        out_path,
        dpi=int(chart_cfg["dpi"]),
        bbox_inches="tight",
        pad_inches=0.06,
        facecolor="white",
    )
    import matplotlib.pyplot as plt

    plt.close(fig)
    return out_path


def _expand_ylim(ax: Any, view: pd.DataFrame, match: PatternMatch) -> None:
    """Show the entry/stop/target lines without letting a distant target squash
    the candles. Expansion is capped at one data-span beyond the price range."""
    levels = match.meta.get("levels") or {}
    data_low = float(view["Low"].min())
    data_high = float(view["High"].max())
    span = (data_high - data_low) or max(abs(data_high), 1.0) * 0.05
    low, high = data_low, data_high
    for key in ("entry", "stop", "target"):
        value = levels.get(key)
        if isinstance(value, (int, float)):
            low = min(low, float(value))
            high = max(high, float(value))
    low = max(low, data_low - span)
    high = min(high, data_high + span)
    pad = (high - low) * 0.04
    ax.set_ylim(low - pad, high + pad)
