#!/usr/bin/env python3
"""Render a catalog of available patterns, question types and clue modes.

Reads ``build/catalog.json`` (written by ``generate_charts.py``) and updates the
marked section of ``README.md`` plus a standalone ``CATALOG.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from puzzlebook.clues import VALID_CLUES  # noqa: E402
from puzzlebook.config import load_config, resolve_path  # noqa: E402
from puzzlebook.questions import QUESTION_LABELS, QUESTION_PROMPTS  # noqa: E402

START = "<!-- CATALOG:START -->"
END = "<!-- CATALOG:END -->"

CLUE_DESCRIPTIONS = {
    "none": "Blank space after the dash",
    "volume": "Volume bars shown after the dash",
    "price": "Price bars shown after the dash",
}


def build_markdown(catalog: Mapping[str, Any]) -> str:
    patterns = catalog.get("patterns", {})
    totals = catalog.get("totals", {})
    questions = catalog.get("questions", {})
    clues = catalog.get("clues", {})
    hit, miss = totals.get("hit", 0), totals.get("miss", 0)

    lines: list[str] = []
    lines.append("_Generated from the latest `generate_charts.py` run._")
    lines.append("")
    lines.append(f"- **Universe**: {len(catalog.get('universe', []))} symbols")
    lines.append(f"- **Score threshold**: > {catalog.get('threshold')}")
    lines.append(f"- **Resolution window**: {catalog.get('resolution_bars')} bars")
    lines.append(
        f"- **Detections**: {totals.get('detected', 0):,} total · "
        f"{totals.get('above_threshold', 0):,} above threshold · "
        f"{totals.get('selected', 0):,} selected for the sample"
    )
    if hit or miss:
        lines.append(f"- **Resolved outcome**: {hit} as expected · {miss} against")
    lines.append("")

    lines.append("#### Patterns")
    lines.append("")
    lines.append("| Pattern | Direction | Detected | Above threshold | Selected | Resolved as expected |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    ordered = sorted(
        patterns.items(), key=lambda item: (-item[1].get("selected", 0), item[0])
    )
    for name, stat in ordered:
        h, m = stat.get("hit", 0), stat.get("miss", 0)
        rate = f"{h} / {h + m}" if (h + m) else "—"
        lines.append(
            f"| `{name}` | {stat.get('direction', '')} | {stat.get('detected', 0):,} | "
            f"{stat.get('above_threshold', 0):,} | {stat.get('selected', 0)} | {rate} |"
        )
    lines.append("")

    lines.append("#### Question types")
    lines.append("")
    lines.append("| Question | The reader... | Selected |")
    lines.append("| --- | --- | ---: |")
    for question, label in QUESTION_LABELS.items():
        lines.append(
            f"| `{question}` | {QUESTION_PROMPTS.get(question, '')} | {questions.get(question, 0)} |"
        )
    lines.append("")

    lines.append("#### Clue modes")
    lines.append("")
    lines.append("| Clue | Puzzle chart after the dash | Selected |")
    lines.append("| --- | --- | ---: |")
    for clue in VALID_CLUES:
        lines.append(
            f"| `{clue}` | {CLUE_DESCRIPTIONS.get(clue, '')} | {clues.get(clue, 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _inject(readme: Path, block: str) -> bool:
    if not readme.exists():
        return False
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        return False
    before = text.split(START)[0]
    after = text.split(END, 1)[1]
    readme.write_text(
        f"{before}{START}\n{block}\n{END}{after}", encoding="utf-8"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--catalog", default=None, help="override catalog.json path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    catalog_path = (
        Path(args.catalog)
        if args.catalog
        else resolve_path(cfg, cfg["output"]["manifest"]).with_name("catalog.json")
    )
    if not catalog_path.exists():
        print(f"No catalog at {catalog_path} - run generate_charts.py first.", file=sys.stderr)
        return 1
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    block = build_markdown(catalog)

    (PROJECT_ROOT / "CATALOG.md").write_text(
        "# Puzzle catalog\n\n" + block, encoding="utf-8"
    )
    injected = _inject(PROJECT_ROOT / "README.md", block)
    print(f"wrote CATALOG.md{' and updated README.md' if injected else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
