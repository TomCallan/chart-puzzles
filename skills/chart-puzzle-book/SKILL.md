---
name: Chart Puzzle Book
description: >-
  Use when building a print-ready chart-pattern puzzle book, workbook or
  practice book from market data, or any HTML/CSS-to-PDF workbook using the
  chart-puzzles pipeline. Covers cloning the repo, configuring the universe and
  puzzle mix, generating patterns and black-and-white charts, assembling the
  KDP 8.5x11 PDF with WeasyPrint, refreshing the catalog and review site, and
  the print-formatting rules that must be followed.
---

# Chart Puzzle Book

Build a physical trading-education workbook from market data. The pipeline
fetches OHLCV data, detects chart patterns, scores them for cleanliness,
renders pure black-and-white charts, and assembles a print-ready PDF with
Jinja2 + WeasyPrint.

Repository: `git@github.com:TomCallan/chart-puzzles.git`

## When to use

- The user wants a chart-pattern practice book, workbook or puzzle book.
- The user wants market charts turned into printable practice material.
- The user wants an HTML/CSS-to-PDF print product with KDP constraints.

## Pipeline

```
yfinance -> detection -> cleanliness score -> B&W PNG (300 DPI)
        -> Jinja2 HTML -> WeasyPrint -> workbook.pdf
```

Each puzzle is a chart that ends at a dashed line (the pattern completion).
The reader works on the facing page; the answer key reveals the resolution.

## 1. Set up

```bash
git clone git@github.com:TomCallan/chart-puzzles.git
cd chart-puzzles
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

WeasyPrint needs system libraries (Debian/Ubuntu):

```bash
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
  libcairo2 libgdk-pixbuf-2.0-0
```

## 2. Configure `config.yaml`

| Key | Meaning |
| --- | --- |
| `universe` | tickers to mine |
| `data.source` | `yfinance` (default) or `alpaca` |
| `patterns.min_score` | cleanliness threshold, default 75 |
| `patterns.require_hit` | keep only patterns that resolved as expected |
| `patterns.max_per_symbol` | cap charts taken from one ticker |
| `chart.lookback_bars` | bars shown before the puzzle moment |
| `chart.resolution_bars` | future bars revealed on the answer chart |
| `chart.target_r` | target distance as a multiple of risk (default 2R) |
| `chart.puzzle_clue_mix` | clue weights: `none` / `volume` / `price` |
| `book.question_mix` | question weights: `identify` / `direction` / `levels` |
| `book.margins` | KDP gutter and outside margins |
| `book.max_puzzles` | size of the sample |

## 3. Build

```bash
.venv/bin/python generate_charts.py     # fetch, detect, score, render, catalog
.venv/bin/python build_pdf.py           # output/workbook.pdf + answer_key.pdf
.venv/bin/python make_catalog.py        # refresh the catalog in README.md
.venv/bin/python make_review.py         # optional browser review build in public/
```

Useful flags: `--symbols SPY AAPL MSFT`, `--min-score 80`, `--require-hit`,
`--limit 20`, `--no-cache`.

To review in a browser on another device:

```bash
.venv/bin/python serve_review.py --port 8000 --bind 0.0.0.0
# open http://<host>:8000/
```

## 4. Print formatting rules (do not break these)

- Trim size is 8.5 x 11 in, **no bleed**.
- Page 1 is a right-hand (recto) page. Front matter must occupy an **odd** page
  count so puzzle 1 lands on a left-hand (verso) page and faces its workspace.
- Gutter (inside margin) depends on final page count: 24-150 pp → 0.375",
  151-300 pp → 0.625", 301-500 pp → 0.875". Outside/top/bottom ≥ 0.25".
  Re-check against KDP's current margin calculator before publishing.
- Set `@page` margins explicitly (`build_pdf.py` injects them from config).
  Never rely on default browser/print margins.
- Charts sit in a fixed-height container with `object-fit: contain` so they
  never stretch or distort.
- The workspace dot grid stays light (`#dcdcdc`) so pencil marks remain visible.

## 5. Puzzle anatomy

- **Puzzle chart** – candles stop at the dashed line. No future bars are ever
  rendered. The axis reserves blank space (or shows the configured clue).
- **Answer chart** – the same candles plus `chart.resolution_bars` future bars.
  The future region is shaded and labelled "answer"; ideal entry / stop / target
  lines are drawn with a legend. The detected pattern itself is drawn too:
  labelled pivots and connecting lines for chart patterns (`H1`/`N`/`H2`,
  `LS`/`H`/`RS`, neckline) and a shaded span over the candles for candlestick
  patterns. Chart-pattern targets use the measured move; candlesticks use
  `chart.target_r` × risk.
- **Question types** – `identify` (name the pattern), `direction` (up or down),
  `levels` (mark entry / stop / target).
- **Clue modes** – `none` (blank space), `volume` (volume only), `price` (price
  only). Invalid pairings are resolved automatically: a `price` clue is never
  used for `direction` or `levels`.

## 5b. Pattern library

44 candlestick patterns (ported from `pinescript_examples.md`) plus double
top/bottom and head & shoulders. The trend gate is `patterns.trend_rule`
(`sma50` / `sma50_200` / `none`). The universe should span several asset
classes — equities, small caps, crypto, forex, commodities and ETFs — because
gap-based patterns (abandoned baby, tri-star, kicking, three methods) are rare
in liquid large caps. `make_catalog.py` reports *hits available* per pattern so
you can confirm there are enough winning examples to sample from.

## 6. Extending

- **New pattern**: write a detector in `src/puzzlebook/patterns/`, `register`
  it, and list its name in `patterns.candlestick.names` or
  `patterns.chart.names`.
- **New question type**: add a prompt, label, title and checklist in
  `src/puzzlebook/questions.py`, then list it in `book.question_mix`.

## 7. Verify before publishing

```bash
.venv/bin/python -m pytest -q          # all tests green
pdfinfo output/workbook.pdf            # must report 612 x 792 pts (8.5 x 11 in)
```

- Confirm puzzle charts show no bars after the dashed line.
- Confirm the page count and page parity (puzzle on verso, workspace on recto).
- Confirm `README.md`'s catalog section matches the current build.

## Troubleshooting

- `ImportError: weasyprint` → missing Pango/Cairo system libraries.
- Empty manifest → lower `patterns.min_score`, or turn off `require_hit`.
- Too few puzzles → widen the universe or raise `patterns.max_per_symbol`.
- Stale browser review → `serve_review.py` disables caching; hard-refresh once.
