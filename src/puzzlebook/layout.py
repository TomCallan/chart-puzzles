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
    # --- single candle ---
    "hammer": "Long lower wick, small body at the top of the range, after a decline. Buy strength above the hammer high.",
    "hanging_man": "Same shape as a hammer but after an advance — a warning that sellers are stepping in.",
    "shooting_star": "Long upper wick, small body near the low, after an advance. Short weakness below the star low.",
    "inverted_hammer": "Long upper wick after a decline — buyers testing higher prices.",
    "marubozu_white": "A long up candle with almost no shadows — buyers in control from open to close.",
    "marubozu_black": "A long down candle with almost no shadows — sellers in control from open to close.",
    "doji": "Open and close are nearly equal with balanced shadows — indecision.",
    "gravestone_doji": "A doji with a long upper shadow and no lower shadow — sellers reject higher prices.",
    "dragonfly_doji": "A doji with a long lower shadow and no upper shadow — buyers reject lower prices.",
    "long_lower_shadow": "A long lower shadow shows sellers dominated early but buyers recovered.",
    "long_upper_shadow": "A long upper shadow shows buyers dominated early but sellers recovered.",
    "spinning_top_white": "A small up body with shadows both sides — indecision leaning bullish.",
    "spinning_top_black": "A small down body with shadows both sides — indecision leaning bearish.",
    # --- two candles ---
    "on_neck": "A down candle then a small up candle closing at the prior low — bearish continuation.",
    "rising_window": "A gap up between two candles — bullish continuation; the gap acts as support.",
    "falling_window": "A gap down between two candles — bearish continuation; the gap acts as resistance.",
    "tweezer_top": "Two candles with matching highs and opposite bodies — bearish reversal.",
    "tweezer_bottom": "Two candles with matching lows and opposite bodies — bullish reversal.",
    "dark_cloud_cover": "An up candle then a down candle opening above its high and closing below its midpoint.",
    "piercing_line": "A down candle then an up candle opening below its low and closing above its midpoint.",
    "bullish_engulfing": "An up candle fully engulfs the prior down candle after a decline.",
    "bearish_engulfing": "A down candle fully engulfs the prior up candle after an advance.",
    "doji_star_bullish": "A down candle then a gapped-down doji — the decline is stalling.",
    "doji_star_bearish": "An up candle then a gapped-up doji — the advance is stalling.",
    "harami_bullish": "A small up candle inside the prior down candle's body — the decline is stalling.",
    "harami_bearish": "A small down candle inside the prior up candle's body — the advance is stalling.",
    "harami_cross_bullish": "A doji inside the prior down candle's body — indecision after a decline.",
    "harami_cross_bearish": "A doji inside the prior up candle's body — indecision after an advance.",
    "kicking_bullish": "A black marubozu then a gapped-up white marubozu — a sharp bullish reversal.",
    "kicking_bearish": "A white marubozu then a gapped-down black marubozu — a sharp bearish reversal.",
    # --- three candles ---
    "morning_star": "Down candle, small middle candle, then a strong up candle closing above the midpoint.",
    "evening_star": "Up candle, small middle candle, then a strong down candle closing below the midpoint.",
    "morning_doji_star": "Down candle, gapped-down doji, then a strong up candle — a stronger morning star.",
    "evening_doji_star": "Up candle, gapped-up doji, then a strong down candle — a stronger evening star.",
    "three_white_soldiers": "Three rising up candles, each opening inside the previous body.",
    "three_black_crows": "Three falling down candles, each opening inside the previous body.",
    "abandoned_baby_bullish": "A down candle, a gapped-down doji, then a gapped-up up candle.",
    "abandoned_baby_bearish": "An up candle, a gapped-up doji, then a gapped-down down candle.",
    "tri_star_bullish": "Three dojis with a gap down then a gap up after a decline — a rare reversal.",
    "tri_star_bearish": "Three dojis with a gap up then a gap down after an advance — a rare reversal.",
    "downside_tasuki_gap": "A down gap that the next candle fails to close — bearish continuation.",
    "upside_tasuki_gap": "An up gap that the next candle fails to close — bullish continuation.",
    # --- five candles ---
    "falling_three_methods": "A long down candle, three small up candles inside its range, then a new low.",
    "rising_three_methods": "A long up candle, three small down candles inside its range, then a new high.",
    # --- chart patterns ---
    "double_bottom": "Two lows at roughly the same price with a peak between them. Completes on a close above the neckline (the peak).",
    "double_top": "Two highs at roughly the same price with a trough between them. Completes on a close below the neckline (the trough).",
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
