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

### Running on Colab

`colab_build.py` installs the system + Python deps and runs the whole pipeline
on a Colab VM (faster than a small VM for the full universe). One-time setup:

```bash
pip install google-colab-cli
gcloud auth application-default login \
  --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory
```

Then run the full detection and push the refreshed catalog back:

```bash
colab --auth adc new --session book
GITHUB_TOKEN=<pat> colab --auth adc exec -s book -f colab_build.py
colab --auth adc stop -s book
```

`GITHUB_TOKEN` needs write access to repo contents (classic PAT with `repo`
scope, or a fine-grained token with *Contents: read and write*). The driver runs
`generate_charts.py → build_pdf.py → make_catalog.py`, then commits the updated
`README.md` catalog section and `CATALOG.md` and pushes to `main`. Set
`COMMIT_OUTPUTS=1` to also commit the generated PDFs. Without a token it still
builds and prints the download commands.

The driver clones the repo over HTTPS by default. To keep the repo private,
upload a tarball instead (`colab upload chart-puzzles.tar.gz /content/...`), or
set `REPO_URL=git@github.com:TomCallan/chart-puzzles.git` and upload a read-only
deploy key to `/content/deploy_key`. `PROJECT_DIR`, `TARBALL`, `REPO_URL` and
`GIT_SSH_KEY` override the defaults. One-shot: `colab --auth adc run --gpu T4
colab_build.py`.

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

## Patterns

All 44 candlestick patterns from the PineScript reference
(`pinescript_examples.md`) are implemented, plus four chart patterns. The exact
conditions live in `src/puzzlebook/patterns/candlestick.py` and mirror the
PineScript variables (`C_Body`, `C_BodyAvg`, `C_DownTrend`, ...) one-for-one.

| Group | Patterns |
| --- | --- |
| Single candle | hammer, hanging man, shooting star, inverted hammer, marubozu (white/black), doji, gravestone doji, dragonfly doji, long lower/upper shadow, spinning top (white/black) |
| Two candles | on neck, rising/falling window, tweezer top/bottom, dark cloud cover, piercing, bullish/bearish engulfing, doji star (bullish/bearish), harami (bullish/bearish), harami cross (bullish/bearish), kicking (bullish/bearish) |
| Three candles | morning/evening star, morning/evening doji star, three white soldiers, three black crows, abandoned baby (bullish/bearish), tri-star (bullish/bearish), downside/upside tasuki gap |
| Five candles | falling/rising three methods |
| Chart | double top, double bottom, head & shoulders, inverse head & shoulders |

The trend gate follows the PineScript "Detect Trend Based On" input
(`patterns.trend_rule`: `sma50`, `sma50_200` or `none`).

## Catalog

<!-- CATALOG:START -->
_Generated from the latest `generate_charts.py` run._

- **Universe**: 172 symbols
- **Score threshold**: > 85.0
- **Resolution window**: 25 bars
- **Detections**: 419,911 total · 11,645 above threshold · 5,144 winning examples available · 516 selected for the sample
- **Resolved outcome**: 222 as expected · 294 against

#### Patterns

| Pattern | Direction | Detected | Above threshold | Hits available | Selected |
| --- | --- | ---: | ---: | ---: | ---: |
| `double_top` | bearish | 44,525 | 4,371 | 1746 | 167 |
| `double_bottom` | bullish | 51,810 | 1,427 | 876 | 52 |
| `rising_window` | bullish | 27,278 | 1,391 | 752 | 6 |
| `bearish_engulfing` | bearish | 11,974 | 791 | 338 | 159 |
| `falling_window` | bearish | 16,721 | 892 | 306 | 4 |
| `bullish_engulfing` | bullish | 7,213 | 451 | 265 | 64 |
| `head_and_shoulders` | bearish | 18,021 | 608 | 208 | 4 |
| `marubozu_white` | bullish | 9,666 | 177 | 110 | 1 |
| `inverse_head_and_shoulders` | bullish | 19,629 | 160 | 93 | 1 |
| `long_lower_shadow` | bullish | 38,330 | 91 | 52 | 0 |
| `dark_cloud_cover` | bearish | 2,690 | 82 | 41 | 1 |
| `long_upper_shadow` | bearish | 34,153 | 83 | 34 | 1 |
| `doji_star_bearish` | bearish | 5,228 | 75 | 33 | 1 |
| `marubozu_black` | bearish | 8,586 | 97 | 32 | 0 |
| `piercing_line` | bullish | 1,739 | 58 | 30 | 1 |
| `doji_star_bullish` | bullish | 4,078 | 48 | 26 | 0 |
| `dragonfly_doji` | bullish | 2,818 | 39 | 22 | 3 |
| `tweezer_top` | bearish | 3,859 | 43 | 21 | 1 |
| `harami_bullish` | bullish | 2,683 | 27 | 18 | 0 |
| `upside_tasuki_gap` | bullish | 1,924 | 30 | 18 | 0 |
| `tweezer_bottom` | bullish | 2,788 | 20 | 16 | 0 |
| `hammer` | bullish | 2,992 | 28 | 15 | 1 |
| `harami_bearish` | bearish | 3,020 | 37 | 13 | 0 |
| `morning_star` | bullish | 377 | 16 | 12 | 1 |
| `gravestone_doji` | bearish | 2,612 | 33 | 11 | 2 |
| `shooting_star` | bearish | 3,210 | 30 | 10 | 2 |
| `downside_tasuki_gap` | bearish | 1,191 | 18 | 7 | 0 |
| `evening_star` | bearish | 411 | 13 | 7 | 1 |
| `on_neck` | bearish | 530 | 11 | 7 | 1 |
| `evening_doji_star` | bearish | 75 | 6 | 4 | 0 |
| `hanging_man` | bearish | 4,382 | 5 | 4 | 0 |
| `inverted_hammer` | bullish | 2,580 | 6 | 4 | 0 |
| `rising_three_methods` | bullish | 192 | 6 | 4 | 0 |
| `falling_three_methods` | bearish | 115 | 4 | 3 | 0 |
| `harami_cross_bullish` | bullish | 262 | 4 | 2 | 0 |
| `morning_doji_star` | bullish | 69 | 4 | 2 | 0 |
| `kicking_bearish` | bearish | 9 | 1 | 1 | 0 |
| `three_white_soldiers` | bullish | 30 | 2 | 1 | 0 |
| `abandoned_baby_bearish` | bearish | 30 | 0 | 0 | 0 |
| `abandoned_baby_bullish` | bullish | 39 | 1 | 0 | 0 |
| `doji` | neutral | 32,034 | 344 | 0 | 42 |
| `harami_cross_bearish` | bearish | 346 | 4 | 0 | 0 |
| `kicking_bullish` | bullish | 9 | 1 | 0 | 0 |
| `spinning_top_black` | neutral | 24,819 | 49 | 0 | 0 |
| `spinning_top_white` | neutral | 24,655 | 60 | 0 | 0 |
| `three_black_crows` | bearish | 24 | 1 | 0 | 0 |
| `tri_star_bearish` | bearish | 77 | 0 | 0 | 0 |
| `tri_star_bullish` | bullish | 108 | 0 | 0 | 0 |

Patterns with fewer than 12 winning examples available (24): `abandoned_baby_bearish`, `abandoned_baby_bullish`, `doji`, `downside_tasuki_gap`, `evening_doji_star`, `evening_star`, `falling_three_methods`, `gravestone_doji`, `hanging_man`, `harami_cross_bearish`, `harami_cross_bullish`, `inverted_hammer`, `kicking_bearish`, `kicking_bullish`, `morning_doji_star`, `on_neck`, `rising_three_methods`, `shooting_star`, `spinning_top_black`, `spinning_top_white`, `three_black_crows`, `three_white_soldiers`, `tri_star_bearish`, `tri_star_bullish`

#### Question types

| Question | The reader... | Selected |
| --- | --- | ---: |
| `identify` | A pattern is completing at the dashed line. Name it, then turn the page and mark the neckline plus your entry, stop-loss and first target. | 13 |
| `direction` | A pattern is completing at the dashed line. Decide whether price will move up or down from here, then turn the page and mark your entry, stop-loss and first target. | 2 |
| `levels` | A pattern is completing at the dashed line. Turn the page and mark your entry, stop-loss and first target for the setup. | 45 |

#### Clue modes

| Clue | Puzzle chart after the dash | Selected |
| --- | --- | ---: |
| `none` | Blank space after the dash | 21 |
| `volume` | Volume bars shown after the dash | 28 |
| `price` | Price bars shown after the dash | 11 |

<!-- CATALOG:END -->

## Filling the pool (getting ≥12 examples per pattern)

The catalog reports **hits available** per pattern: detections that score above
`patterns.min_score` *and* resolve in the pattern's expected direction within
`chart.resolution_bars`. The target is ≥12 per pattern so the final edition can
sample evenly. `make_catalog.py` lists any pattern still below 12.

If a pattern is short, in rough order of impact:

1. **Widen the universe.** Gap-based patterns (abandoned baby, tri-star,
   kicking, three methods, three white soldiers/crows) are rare in liquid large
   caps. Add small caps, emerging-market ADRs, forex pairs (weekend gaps) and
   more crypto to `universe`. The default list is already ~280 symbols across
   asset classes; extending it is the most reliable lever.
2. **Lower `patterns.min_score`.** 75 is the default; 70 roughly doubles the
   pool. Quality drops, so a common pattern is to keep the book at a higher
   threshold and only widen the pool for sampling.
3. **Extend history.** `data.start: "1995-01-01"` gives more bars; most stocks
   and forex pairs go back that far.
4. **Raise `patterns.max_per_symbol`** so one ticker can contribute more than
   three examples.
5. **Raise `book.max_puzzles`** if the sample should include more puzzles.

Then regenerate and refresh the catalog:

```bash
.venv/bin/python generate_charts.py
.venv/bin/python build_pdf.py
.venv/bin/python make_catalog.py
.venv/bin/python make_review.py
```

**Performance.** Detection dominates; the full ~280-symbol universe takes about
an hour on a small VM. OHLCV data is cached in `.cache/ohlcv`, so re-runs are
much faster. Use `--symbols ... --limit N` to iterate on a subset, and
`--min-score` to try thresholds without editing `config.yaml`.

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
- **Pattern drawing** – the answer chart also draws the pattern itself:
  labelled pivots and connecting lines for chart patterns (`H1`/`N`/`H2`,
  `LS`/`H`/`RS`, neckline) and a shaded span over the candles involved for
  candlestick patterns.
- **Measured-move targets** – chart-pattern targets are the pattern's height
  projected from the neckline; candlesticks use `chart.target_r` × risk.

### Page parity

KDP page 1 is a right-hand (recto) page. Front matter is padded to an **odd**
page count so puzzle 1 lands on a left-hand (verso) page and each puzzle faces
its workspace when the book is open.

### Cleanliness scoring

Patterns are kept only if they score above `patterns.min_score` (default 75).
The score blends five factors (weights in `config.yaml`): trend magnitude
discounted by smoothness (R²), volume confirmation, size relative to ATR,
pattern geometry (including swing prominence), and available clean history.
The threshold trades pool size against quality: raise it for a stricter book,
lower it when you need more examples of a rare pattern. `make_catalog.py`
reports how many winning examples exist per pattern at the configured
threshold.

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
