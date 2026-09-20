#!/usr/bin/env python3
"""Fetch market data, detect + score patterns and render B&W charts.

Writes a JSON manifest that ``build_pdf.py`` consumes, plus a catalog of every
pattern found so you can decide what to sample for the final edition. No future
bars are ever rendered on a puzzle chart.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from puzzlebook.charts import render_chart  # noqa: E402
from puzzlebook.clues import build_clue_schedule  # noqa: E402
from puzzlebook.config import PROJECT_ROOT as CFG_ROOT  # noqa: E402
from puzzlebook.config import load_config, resolve_path  # noqa: E402
from puzzlebook.data import fetch_ohlcv, load_universe  # noqa: E402
from puzzlebook.levels import trade_levels  # noqa: E402
from puzzlebook.patterns import build_detectors, dedupe, score_matches  # noqa: E402
from puzzlebook.questions import (  # noqa: E402
    QUESTION_LABELS,
    assign_clues,
    build_question_schedule,
    resolve_clue,
)


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(CFG_ROOT))
    except ValueError:
        return str(path.resolve())


def _detect(df: Any, detectors: list, cfg: dict) -> list:
    matches = []
    for detector in detectors:
        try:
            matches.extend(detector.detect(df, cfg))
        except Exception as exc:  # keep one bad detector from killing the run
            print(f"    ! {detector.name} failed: {exc}", file=sys.stderr)
    return matches


def _outcome(df: Any, match: Any, resolution: int) -> dict[str, Any]:
    """What actually happened over the resolution window after the pattern."""
    end = match.end_idx
    target_idx = min(end + resolution, len(df) - 1)
    move = float(df["Close"].iloc[target_idx] - df["Close"].iloc[end])
    outcome = "up" if move > 0 else "down" if move < 0 else "flat"
    hit = (match.direction == "bullish" and outcome == "up") or (
        match.direction == "bearish" and outcome == "down"
    )
    return {
        "outcome": outcome,
        "hit": bool(hit),
        "resolved_bars": target_idx - end,
        "move_pct": round(move / float(df["Close"].iloc[end]) * 100, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--symbols", nargs="*", default=None, help="override universe")
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument(
        "--require-hit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="keep only patterns that resolved in the expected direction",
    )
    parser.add_argument("--limit", type=int, default=None, help="max charts to keep")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.min_score is not None:
        cfg["patterns"]["min_score"] = args.min_score
    if args.require_hit is not None:
        cfg["patterns"]["require_hit"] = args.require_hit

    charts_dir = resolve_path(cfg, cfg["output"]["charts_dir"])
    manifest_path = resolve_path(cfg, cfg["output"]["manifest"])
    catalog_path = manifest_path.with_name("catalog.json")
    symbols = args.symbols or load_universe(cfg)
    detectors = build_detectors(cfg)
    min_score = float(cfg["patterns"]["min_score"])
    require_hit = bool(cfg["patterns"].get("require_hit", False))
    max_per_symbol = int(cfg["patterns"]["max_per_symbol"])
    resolution = int(cfg["chart"]["resolution_bars"])
    single_clue = str(cfg["chart"].get("puzzle_clue", "none")).lower()
    limit = args.limit if args.limit is not None else int(cfg["book"]["max_puzzles"])
    clue_schedule = build_clue_schedule(cfg["chart"].get("puzzle_clue_mix"), limit)
    question_schedule = build_question_schedule(cfg["book"].get("question_mix"), limit)
    # Assign clues against the questions so the mix is honoured subject to the
    # per-question validity rules (price clues only work for identify puzzles).
    clue_schedule = assign_clues(question_schedule, cfg["chart"].get("puzzle_clue_mix")) or clue_schedule
    single_question = str(cfg["book"].get("question", "identify")).lower()
    puzzle_index = 0

    print(f"Detectors : {', '.join(d.name for d in detectors)}")
    print(f"Threshold : score > {min_score}" + ("  (require hit)" if require_hit else ""))
    print(f"Universe  : {', '.join(symbols)}\n")

    stats: dict[str, Any] = {
        "patterns": {},
        "totals": {"detected": 0, "above_threshold": 0, "selected": 0},
    }

    def pattern_stat(name: str) -> dict[str, int]:
        return stats["patterns"].setdefault(
            name,
            {
                "detected": 0,
                "above_threshold": 0,
                "selected": 0,
                "hit": 0,
                "miss": 0,
            },
        )

    entries: list[dict[str, Any]] = []
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, cfg, use_cache=not args.no_cache)
        except Exception as exc:
            print(f"  {symbol}: fetch failed ({exc})", file=sys.stderr)
            continue
        matches = _detect(df, detectors, cfg)
        score_matches(df, matches, cfg)
        for match in matches:
            stat = pattern_stat(match.name)
            stat.setdefault("direction", match.direction)
            stat["detected"] += 1
            stats["totals"]["detected"] += 1
            if match.score > min_score:
                stat["above_threshold"] += 1
                stats["totals"]["above_threshold"] += 1

        matches = [m for m in matches if m.score > min_score]
        matches = dedupe(matches, cfg)
        # Only keep patterns with enough future bars to show a real resolution.
        matches = [m for m in matches if m.end_idx + resolution < len(df)]
        for match in matches:
            match.meta["outcome"] = _outcome(df, match, resolution)
        if require_hit:
            matches = [m for m in matches if m.meta["outcome"]["hit"]]
        matches = sorted(matches, key=lambda m: -m.score)[:max_per_symbol]

        for match in matches:
            match.symbol = symbol
            match.meta["levels"] = trade_levels(df, match, cfg)
            question = (
                question_schedule[puzzle_index % len(question_schedule)]
                if question_schedule
                else single_question
            )
            raw_clue = (
                clue_schedule[puzzle_index % len(clue_schedule)]
                if clue_schedule
                else single_clue
            )
            clue = resolve_clue(question, raw_clue)
            suffix = "" if clue == "none" else f"_{clue}"
            stem = f"{symbol}_{match.name}_{match.end_idx}_{question}{suffix}"
            puzzle_png = charts_dir / f"{stem}_puzzle.png"
            answer_png = charts_dir / f"{stem}_answer.png"
            try:
                render_chart(df, match, cfg, puzzle_png, mode="puzzle", clue=clue)
                render_chart(df, match, cfg, answer_png, mode="answer")
            except Exception as exc:
                print(f"    ! render failed for {stem}: {exc}", file=sys.stderr)
                continue

            outcome = match.meta["outcome"]
            entries.append(
                {
                    "symbol": symbol,
                    "name": match.name,
                    "direction": match.direction,
                    "score": match.score,
                    "start_idx": match.start_idx,
                    "end_idx": match.end_idx,
                    "bars": match.bar_count,
                    "factors": match.meta.get("factors", {}),
                    "levels": match.meta.get("levels", {}),
                    "question": question,
                    "clue": clue,
                    "outcome": outcome,
                    "chart": _relative(puzzle_png),
                    "answer_chart": _relative(answer_png),
                }
            )
            pattern_stat(match.name)["selected"] += 1
            stat = pattern_stat(match.name)
            stat["hit" if outcome["hit"] else "miss"] += 1
            stats["totals"]["selected"] += 1
            stats["totals"]["hit" if outcome["hit"] else "miss"] = (
                stats["totals"].get("hit" if outcome["hit"] else "miss", 0) + 1
            )
            puzzle_index += 1

        kept = ", ".join(f"{m.name} ({m.score})" for m in matches) or "none"
        print(f"  {symbol}: {kept}")

    entries.sort(key=lambda e: -e["score"])
    entries = entries[:limit]

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    stats["universe"] = symbols
    stats["threshold"] = min_score
    stats["require_hit"] = require_hit
    stats["resolution_bars"] = resolution
    stats["questions"] = dict(Counter(e["question"] for e in entries))
    stats["clues"] = dict(Counter(e["clue"] for e in entries))
    stats["selected"] = len(entries)
    catalog_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"\nQuestion mix: {stats['questions']}")
    print(f"Clue mix    : {stats['clues']}")
    print(f"{len(entries)} puzzles -> {manifest_path}")
    print(f"catalog     -> {catalog_path}")
    return 0 if entries else 1


if __name__ == "__main__":
    raise SystemExit(main())
