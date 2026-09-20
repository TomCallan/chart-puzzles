from pathlib import Path
from puzzlebook.charts import render_chart
from puzzlebook.layout import build_pages, build_puzzles
from puzzlebook.pdf import html_to_pdf, render_book_html
from puzzlebook.patterns.base import get


def test_full_book_pdf_is_print_ready(double_bottom_df, cfg, tmp_path: Path):
    cfg["book"]["max_puzzles"] = 1
    cfg["chart"]["dpi"] = 72  # keep the test fast

    match = get("double_bottom").detect(double_bottom_df, cfg)[0]
    match.symbol = "SPY"
    puzzle_png = tmp_path / "puzzle.png"
    answer_png = tmp_path / "answer.png"
    render_chart(double_bottom_df, match, cfg, puzzle_png, mode="puzzle")
    render_chart(double_bottom_df, match, cfg, answer_png, mode="answer")
    assert puzzle_png.exists() and answer_png.exists()

    manifest = [
        {
            "symbol": "SPY",
            "name": "double_bottom",
            "direction": "bullish",
            "score": 90.0,
            "bars": match.bar_count,
            "chart": "puzzle.png",
            "answer_chart": "answer.png",
        }
    ]
    pages = build_pages(build_puzzles(manifest, cfg), cfg)
    html = render_book_html(pages, cfg)
    out = tmp_path / "book.pdf"
    html_to_pdf(html, out, base_url=tmp_path)
    assert out.exists()

    from weasyprint import HTML

    document = HTML(string=html, base_url=str(tmp_path)).render()
    assert len(document.pages) == len(pages)
    first = document.pages[0]
    assert round(first.width / 96, 2) == 8.5
    assert round(first.height / 96, 2) == 11.0
