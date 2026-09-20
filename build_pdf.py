#!/usr/bin/env python3
"""Assemble the generated charts into a print-ready PDF via Jinja2 + WeasyPrint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from puzzlebook.config import PROJECT_ROOT as CFG_ROOT  # noqa: E402
from puzzlebook.config import load_config, resolve_path  # noqa: E402
from puzzlebook.layout import build_pages, build_puzzles, load_manifest  # noqa: E402
from puzzlebook.pdf import html_to_pdf, render_book_html  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--manifest", default=None, help="override manifest path")
    parser.add_argument("--out", default=None, help="override output PDF path")
    parser.add_argument("--html", default=None, help="also dump the rendered HTML")
    parser.add_argument("--no-answer-key", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    manifest_path = args.manifest or resolve_path(cfg, cfg["output"]["manifest"])
    manifest = load_manifest(manifest_path)
    puzzles = build_puzzles(manifest, cfg)
    if not puzzles:
        print("Manifest is empty - run generate_charts.py first.", file=sys.stderr)
        return 1

    pages = build_pages(puzzles, cfg)
    html = render_book_html(pages, cfg)
    if args.html:
        Path(args.html).write_text(html, encoding="utf-8")

    out_path = args.out or resolve_path(cfg, cfg["output"]["pdf"])
    html_to_pdf(html, out_path, base_url=CFG_ROOT)
    print(f"{len(pages)} pages, {len(puzzles)} puzzles -> {out_path}")

    if cfg["output"]["render_answer_key"] and not args.no_answer_key:
        answer_pages = [page for page in pages if page["kind"] == "answer"]
        answer_html = render_book_html(answer_pages, cfg, standalone=True)
        answer_out = resolve_path(cfg, cfg["output"]["answer_key_pdf"])
        html_to_pdf(answer_html, answer_out, base_url=CFG_ROOT)
        print(f"answer key -> {answer_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
