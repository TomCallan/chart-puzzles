# The Chart Pattern Puzzle Book

A programmatic generator for a print-ready trading-education workbook. It
fetches market data, detects chart patterns, renders clean black-and-white
charts, and assembles them into an Amazon KDP-ready PDF using **HTML/CSS +
WeasyPrint**.

```
yfinance ──▶ pattern detection ──▶ cleanliness score ──▶ B&W PNG (300 DPI)
        ──▶ Jinja2 HTML ──▶ WeasyPrint ──▶ workbook.pdf
```

Each puzzle is a price chart that ends at a dashed line — the exact moment a
pattern completes. The reader works on the facing page; the answer key reveals
what actually happened next, shaded apart from the question data, with ideal
entry / stop / target lines.

## What you get

| File | Purpose |
| --- | --- |
| `generate_charts.py` | fetch data, detect + score patterns, render puzzle & answer PNGs, write the manifest and catalog |
| `build_pdf.py` | render the Jinja2 template and produce `output/workbook.pdf` + `output/answer_key.pdf` |
| `make_review.py` | render a browser-review build into `public/` |
| `make_catalog.py` | update the catalog section below and write `CATALOG.md` |
| `serve_review.py` | serve `public/` over HTTP with caching disabled |
| `templates/styles.css` | complete print-ready CSS (KDP 8.5" × 11", gutter margins, page breaks) |
| `templates/book_template.html` | Jinja2 template: front matter, puzzle/workspace spreads, answer key |
| `src/puzzlebook/` | the modular library behind the scripts |
| `requirements.txt` | all Python dependencies |

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python generate_charts.py   # fetch + detect + render
.venv/bin/python build_pdf.py         # assemble the PDF
.venv/bin/python make_catalog.py      # refresh the catalog below
.venv/bin/python make_review.py       # optional: browser review build
```

> **System packages:** WeasyPrint needs Pango/Cairo. On Debian/Ubuntu:
> `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 libgdk-pixbuf-2.0-0`

## Practice question types

Set the mix under `book.question_mix` in `config.yaml`. The types are spread
evenly through the book by a deficit round-robin.

| Question | The reader... | Default weight |
| --- | --- | ---: |
| `identify` | names the pattern completing at the dashed line | 40 |
| `direction` | decides whether the next move is up or down | 30 |
| `levels` | marks the entry, stop-loss and first target | 30 |

Every puzzle also draws ideal entry / stop / target lines in the answer key
(`target = chart.target_r` × risk, default 2R).

### Clue modes

Set under `chart.puzzle_clue_mix`. The clue controls what is revealed after the
dashed line on the **puzzle** chart.

| Clue | Puzzle chart after the dash | Default weight |
| --- | --- | ---: |
| `none` | blank drawing space | 30 |
| `volume` | volume bars only (infer price from volume) | 30 |
| `price` | price bars only (infer volume from price) | 30 |

Invalid combinations are downgraded automatically: `direction` never uses a
`price` clue (it would reveal the answer) and `levels` always uses `none`.

## Catalog

<!-- CATALOG:START -->
_Generated from the latest `generate_charts.py` run._

- **Universe**: 20 symbols
- **Score threshold**: > 85.0
- **Resolution window**: 25 bars
- **Detections**: 156,610 total · 1,250 above threshold · 60 selected for the sample
- **Resolved outcome**: 17 as expected · 43 against

#### Patterns

| Pattern | Direction | Detected | Above threshold | Selected | Resolved as expected |
| --- | --- | ---: | ---: | ---: | ---: |
| `double_top` | bearish | 7,297 | 447 | 15 | 3 / 15 |
| `bearish_engulfing` | bearish | 2,164 | 106 | 12 | 3 / 12 |
| `evening_star` | bearish | 1,396 | 54 | 11 | 3 / 11 |
| `double_bottom` | bullish | 11,880 | 129 | 8 | 4 / 8 |
| `morning_star` | bullish | 1,478 | 25 | 6 | 2 / 6 |
| `doji` | neutral | 5,693 | 52 | 3 | 0 / 3 |
| `hammer` | bullish | 3,523 | 18 | 2 | 1 / 2 |
| `shooting_star` | bearish | 2,987 | 15 | 2 | 0 / 2 |
| `bullish_engulfing` | bullish | 1,827 | 35 | 1 | 1 / 1 |
| `bearish_harami` | bearish | 1,679 | 12 | 0 | — |
| `bullish_harami` | bullish | 1,909 | 7 | 0 | — |
| `dark_cloud_cover` | bearish | 667 | 11 | 0 | — |
| `head_and_shoulders` | bearish | 45,220 | 274 | 0 | — |
| `inverse_head_and_shoulders` | bullish | 65,528 | 28 | 0 | — |
| `piercing_line` | bullish | 537 | 3 | 0 | — |
| `three_black_crows` | bearish | 1,349 | 18 | 0 | — |
| `three_white_soldiers` | bullish | 1,476 | 16 | 0 | — |

#### Question types

| Question | The reader... | Selected |
| --- | --- | ---: |
| `identify` | A pattern is completing at the dashed line. Name it, then turn the page and mark the neckline plus your entry, stop-loss and first target. | 24 |
| `direction` | A pattern is completing at the dashed line. Decide whether price will move up or down from here, then turn the page and mark your entry, stop-loss and first target. | 18 |
| `levels` | A pattern is completing at the dashed line. Turn the page and mark your entry, stop-loss and first target for the setup. | 18 |

#### Clue modes

| Clue | Puzzle chart after the dash | Selected |
| --- | --- | ---: |
| `none` | Blank space after the dash | 20 |
| `volume` | Volume bars shown after the dash | 20 |
| `price` | Price bars shown after the dash | 20 |

<!-- CATALOG:END -->

## Configuration

Everything lives in `config.yaml`, merged over the defaults in
`src/puzzlebook/config.py`.

| Section | What it controls |
| --- | --- |
| `universe` | tickers to mine |
| `data` | source (`yfinance`/`alpaca`), date range, interval, cache |
| `patterns` | score threshold, pivot window, enabled detectors, scoring weights |
| `chart` | DPI, lookback/resolution bars, target R, clue mix, B&W options |
| `book` | title/author, trim size, KDP margins, question mix, page count |
| `output` | where charts, manifest and PDFs are written |

### KDP margins

`book.margins.inside` is the binding/gutter margin and depends on the final
page count:

| Page count | Inside (gutter) |
| --- | --- |
| 24–150 | 0.375" |
| 151–300 | 0.625" |
| 301–500 | 0.875" |

The default is the 24–150 pp value. Outside/top/bottom default to the KDP
no-bleed minimum of 0.25". `build_pdf.py` injects these into the `@page` rules,
so changing the config is enough. Re-check against KDP's current margin
calculator before publishing.

## How it works

### Anti-look-ahead by construction

Puzzle charts are sliced with `df.iloc[:end_idx + 1].tail(lookback)`, so the last
rendered bar is the pattern's **completion bar**. Tests assert that no future
bar can leak into a puzzle chart.

### Puzzle vs. answer charts

- **Puzzle chart** – candles stop at the puzzle moment; the axis reserves
  `chart.resolution_bars` of space to the right for the reader's work (or shows
  the clue selected by the clue mix).
- **Answer chart** – the same candles plus `chart.resolution_bars` of future
  bars. The future region is shaded and labelled "answer", and the ideal entry
  / stop / target lines are drawn with a legend. Both charts share the same
  x-scale, so the dashed lines line up.

### Page parity

KDP page 1 is a right-hand (recto) page. Front matter is padded to an **odd**
page count so puzzle 1 lands on a left-hand (verso) page and each puzzle faces
its workspace when the book is open.

### Cleanliness scoring

Patterns are kept only if they score **> 85/100**. The score blends five
factors (weights in `config.yaml`): trend magnitude discounted by smoothness
(R²), volume confirmation, size relative to ATR, pattern geometry (including
swing prominence), and available clean history. On SPY, the median detection
scores ~48/100 and only ~2% clear the threshold.

## Extending with new patterns

1. Write a detector (see `src/puzzlebook/patterns/candlestick.py` or `chart.py`).
2. `register(...)` it.
3. Add its name to `patterns.candlestick.names` or `patterns.chart.names`.

New question types live in `src/puzzlebook/questions.py`; add a prompt, label,
title and checklist, then list it in `book.question_mix`.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Covers the detector registry, the no-look-ahead invariant, score bounds, page
parity, clue/question scheduling and validity, and an end-to-end PDF render
that asserts the page size is 8.5" × 11" and the page count matches the layout.
