#!/usr/bin/env python3
"""Render the browser-review HTML into ``public/``.

Produces:
  public/index.html              landing page linking the two views
  public/review.html             full workbook
  public/review_answer_key.html  answer key only
  public/assets -> ../assets     symlink so chart images resolve
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from puzzlebook.config import load_config, resolve_path  # noqa: E402
from puzzlebook.layout import build_pages, build_puzzles, load_manifest  # noqa: E402
from puzzlebook.pdf import render_book_html  # noqa: E402

INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chart Pattern Puzzle Book - review</title>
<style>
  body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#e9e9ec;margin:0;padding:48px 20px;color:#16181d}
  .wrap{max-width:640px;margin:0 auto;background:#fff;border-radius:14px;padding:36px 40px;box-shadow:0 4px 24px rgba(0,0,0,.14)}
  h1{margin:0 0 6px;font-size:24px}
  p.sub{color:#555;margin:0 0 26px}
  a.card{display:block;text-decoration:none;color:inherit;border:1px solid #dcdce2;border-radius:10px;padding:16px 18px;margin-bottom:14px;transition:.15s}
  a.card:hover{border-color:#16181d;box-shadow:0 2px 10px rgba(0,0,0,.08)}
  a.card strong{display:block;font-size:16px;margin-bottom:3px}
  a.card span{font-size:13px;color:#666}
  .note{font-size:12px;color:#888;margin-top:22px;line-height:1.5}
</style>
</head>
<body>
  <div class="wrap">
    <h1>The Chart Pattern Puzzle Book</h1>
    <p class="sub">Browser review build</p>
    <a class="card" href="review.html"><strong>Full workbook &rarr;</strong><span>Front matter, puzzle/workspace spreads and the answer key</span></a>
    <a class="card" href="review_answer_key.html"><strong>Answer key only &rarr;</strong><span>Annotated charts with pattern names, levels and notes</span></a>
    <p class="note">Pages render as 8.5&quot; x 11&quot; sheets. The print PDF lives at <code>output/workbook.pdf</code>.</p>
  </div>
</body>
</html>
"""


def _link_assets(out_dir: Path) -> None:
    link = out_dir / "assets"
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.is_dir():
        shutil.rmtree(link)
    try:
        link.symlink_to(Path("..") / "assets")
    except OSError:  # pragma: no cover - fallback for platforms without symlinks
        shutil.copytree(PROJECT_ROOT / "assets", link)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--manifest", default=None, help="override manifest path")
    parser.add_argument("--out-dir", default="public")
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.manifest or resolve_path(cfg, cfg["output"]["manifest"])
    manifest = load_manifest(manifest_path)
    puzzles = build_puzzles(manifest, cfg)
    pages = build_pages(puzzles, cfg)

    (out_dir / "review.html").write_text(render_book_html(pages, cfg), encoding="utf-8")
    answer_pages = [page for page in pages if page["kind"] == "answer"]
    (out_dir / "review_answer_key.html").write_text(
        render_book_html(answer_pages, cfg, standalone=True), encoding="utf-8"
    )
    (out_dir / "index.html").write_text(INDEX, encoding="utf-8")
    _link_assets(out_dir)

    print(f"{len(pages)} pages, {len(puzzles)} puzzles -> {out_dir}/review.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
