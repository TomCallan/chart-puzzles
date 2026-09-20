from puzzlebook.layout import build_pages, build_puzzles


def _manifest(n: int) -> list[dict]:
    return [
        {
            "symbol": "SPY",
            "name": "double_bottom",
            "direction": "bullish",
            "score": 90.0,
            "bars": 30,
            "chart": f"assets/charts/p{i}.png",
            "answer_chart": f"assets/charts/a{i}.png",
        }
        for i in range(n)
    ]


def test_front_matter_is_odd_so_puzzle_one_is_on_the_left(cfg):
    pages = build_pages(build_puzzles(_manifest(3), cfg), cfg)
    front = [p for p in pages if p["kind"] in ("front", "blank")]
    assert len(front) % 2 == 1

    first_puzzle = next(p for p in pages if p["kind"] == "puzzle")
    assert first_puzzle["number"] % 2 == 0, "puzzle 1 must land on a verso page"


def test_puzzles_are_followed_by_workspace(cfg):
    pages = build_pages(build_puzzles(_manifest(2), cfg), cfg)
    kinds = [p["kind"] for p in pages]
    start = kinds.index("puzzle")
    assert kinds[start : start + 4] == ["puzzle", "workspace", "puzzle", "workspace"]


def test_answer_key_has_title_on_first_page(cfg):
    pages = build_pages(build_puzzles(_manifest(3), cfg), cfg)
    answers = [p for p in pages if p["kind"] == "answer"]
    assert answers[0]["title"] == "Answer Key"
    assert all(p["title"] is None for p in answers[1:])
