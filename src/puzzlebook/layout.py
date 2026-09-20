"""Turn detected patterns into an ordered list of book pages.

Page parity matters for KDP: page 1 is a right-hand (recto) page. We keep the
front matter at an odd page count so that puzzle 1 lands on a left-hand
(verso) page and each puzzle faces its workspace when the book is open.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .questions import (
    QUESTION_CHECKLIST,
    QUESTION_LABELS,
    QUESTION_PROMPTS,
    QUESTION_TITLES,
)

SECTORS: dict[str, str] = {
    "SPY": "Index ETF",
    "QQQ": "Index ETF",
    "IWM": "Index ETF",
    "DIA": "Index ETF",
    "AAPL": "Large-Cap Technology",
    "MSFT": "Large-Cap Technology",
    "NVDA": "Semiconductors",
    "AMD": "Semiconductors",
    "INTC": "Semiconductors",
    "GOOGL": "Communication Services",
    "META": "Communication Services",
    "NFLX": "Communication Services",
    "DIS": "Communication Services",
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "WMT": "Consumer Staples",
    "KO": "Consumer Staples",
    "PFE": "Healthcare",
    "JPM": "Financials",
    "XOM": "Energy",
    "CVX": "Energy",
    "BA": "Industrials",
    "GE": "Industrials",
}

PUZZLE_PROMPT = (
    "A pattern is completing at the dashed line. Name it, then turn the page "
    "and mark the neckline plus your entry, stop-loss and first target."
)

PATTERN_NOTES: dict[str, str] = {
    "bullish_engulfing": "A bullish candle fully engulfs the prior down candle after a decline. Long above the engulfing high, stop below its low.",
    "bearish_engulfing": "A bearish candle fully engulfs the prior up candle after an advance. Short below the engulfing low, stop above its high.",
    "hammer": "A long lower wick with a small body at the bottom of a decline. Buy strength above the hammer high.",
    "shooting_star": "A long upper wick with a small body after an advance. Short weakness below the star low.",
    "doji": "Open and close are nearly equal, signalling indecision. Wait for the next candle to resolve direction.",
    "morning_star": "Down candle, small indecision candle, then a strong up candle. Long above the third candle's high.",
    "evening_star": "Up candle, small indecision candle, then a strong down candle. Short below the third candle's low.",
    "bullish_harami": "A small up candle sits inside the prior down candle's body, hinting the decline is stalling.",
    "bearish_harami": "A small down candle sits inside the prior up candle's body, hinting the advance is stalling.",
    "piercing_line": "An up candle opens below the prior low and closes back above the midpoint of the down candle.",
    "dark_cloud_cover": "A down candle opens above the prior high and closes below the midpoint of the up candle.",
    "three_white_soldiers": "Three rising up candles with higher closes, each opening inside the previous body.",
    "three_black_crows": "Three falling down candles with lower closes, each opening inside the previous body.",
    "double_bottom": "Two lows at roughly the same price with a peak between them. The pattern completes on a close above the neckline (the peak).",
    "double_top": "Two highs at roughly the same price with a trough between them. The pattern completes on a close below the neckline (the trough).",
    "head_and_shoulders": "Three peaks with a higher middle (head) and similar shoulders. Completes on a close below the neckline through the two troughs.",
    "inverse_head_and_shoulders": "Three troughs with a lower middle (head) and similar shoulders. Completes on a close above the neckline through the two peaks.",
}


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass
class Puzzle:
    number: int
    chart: str
    answer_chart: str
    symbol: str
    sector: str
    pattern: str
    direction: str
    score: float
    difficulty: str
    prompt: str
    bars: int
    note: str = ""
    factors: dict[str, float] = field(default_factory=dict)
    levels: dict[str, float] = field(default_factory=dict)
    clue: str = "none"
    question: str = "identify"
    outcome: dict[str, Any] = field(default_factory=dict)

    @property
    def display_pattern(self) -> str:
        return self.pattern.replace("_", " ").title()

    @property
    def question_label(self) -> str:
        return QUESTION_LABELS.get(self.question, "")

    @property
    def question_title(self) -> str:
        return QUESTION_TITLES.get(self.question, QUESTION_TITLES["identify"])

    @property
    def checklist(self) -> list[str]:
        return QUESTION_CHECKLIST.get(self.question, QUESTION_CHECKLIST["identify"])

    @property
    def clue_label(self) -> str:
        return {"volume": "Volume clue", "price": "Price clue"}.get(self.clue, "")

    @property
    def clue_hint(self) -> str:
        return {
            "volume": "Only volume is shown beyond the dashed line. Use it to infer what price did.",
            "price": "Only price is shown beyond the dashed line. Use it to infer what volume did.",
        }.get(self.clue, "")

    @property
    def outcome_note(self) -> str:
        if not self.outcome:
            return ""
        result = self.outcome.get("outcome")
        if result == "flat":
            return "Price was little changed over the bars that followed."
        verb = "rose" if result == "up" else "fell"
        verdict = (
            "in line with the pattern's expected direction"
            if self.outcome.get("hit")
            else "against the pattern's expected direction"
        )
        move = abs(self.outcome.get("move_pct", 0.0))
        bars = self.outcome.get("resolved_bars", 0)
        return f"Price {verb} {move}% over the next {bars} bars — {verdict}."


def _difficulty(score: float) -> str:
    if score >= 92:
        return "Warm-up"
    if score >= 88:
        return "Intermediate"
    return "Advanced"


def build_puzzles(
    manifest: list[dict[str, Any]], cfg: Mapping[str, Any]
) -> list[Puzzle]:
    max_puzzles = int(cfg["book"]["max_puzzles"])
    puzzles: list[Puzzle] = []
    for entry in manifest:
        if len(puzzles) >= max_puzzles:
            break
        symbol = entry.get("symbol", "")
        question = entry.get("question", "identify")
        puzzles.append(
            Puzzle(
                number=len(puzzles) + 1,
                chart=entry["chart"],
                answer_chart=entry["answer_chart"],
                symbol=symbol,
                sector=SECTORS.get(symbol.upper(), "Equities"),
                pattern=entry["name"],
                direction=entry.get("direction", "neutral"),
                score=float(entry.get("score", 0.0)),
                difficulty=_difficulty(float(entry.get("score", 0.0))),
                prompt=QUESTION_PROMPTS.get(question, QUESTION_PROMPTS["identify"]),
                bars=int(entry.get("bars", 0)),
                note=PATTERN_NOTES.get(
                    entry["name"],
                    "Review the pattern geometry and the level that confirms it.",
                ),
                factors=entry.get("factors", {}),
                levels=entry.get("levels", {}),
                clue=entry.get("clue", "none"),
                question=question,
                outcome=entry.get("outcome", {}),
            )
        )
    return puzzles


def build_pages(
    puzzles: list[Puzzle], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return an ordered list of page descriptors for the template."""
    pages: list[dict[str, Any]] = []
    book = cfg["book"]

    # --- front matter (padded to an odd count) -----------------------------
    front: list[dict[str, Any]] = [
        {
            "kind": "front",
            "number": None,
            "title": book["title"],
            "subtitle": book["subtitle"],
            "author": book["author"],
            "edition": book["edition"],
        }
    ]
    if len(front) % 2 == 0:
        front.append({"kind": "blank", "number": None})
    pages.extend(front)

    # --- puzzle / workspace spreads ---------------------------------------
    for puzzle in puzzles:
        puzzle_page = {
            "kind": "puzzle",
            "number": len(pages) + 1,
            "puzzle": puzzle,
        }
        pages.append(puzzle_page)
        pages.append(
            {
                "kind": "workspace",
                "number": len(pages) + 1,
                "puzzle": puzzle,
            }
        )

    # --- answer key (two answers per page) ---------------------------------
    answers = puzzles
    for start in range(0, len(answers), 2):
        pages.append(
            {
                "kind": "answer",
                "number": len(pages) + 1,
                "answers": answers[start : start + 2],
                "title": "Answer Key" if start == 0 else None,
            }
        )

    return pages


def content_height_in(cfg: Mapping[str, Any]) -> float:
    """Usable page height inside the top/bottom margins, minus a safety gap."""
    margins = cfg["book"]["margins"]
    height = float(cfg["book"]["trim"]["height"])
    return height - float(margins["top"]) - float(margins["bottom"]) - 0.1
