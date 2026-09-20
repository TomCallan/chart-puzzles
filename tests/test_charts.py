from puzzlebook.charts import _answer_view, _puzzle_view
from puzzlebook.levels import trade_levels
from puzzlebook.patterns.base import get


def test_puzzle_view_hides_future_bars(double_bottom_df, cfg):
    match = get("double_bottom").detect(double_bottom_df, cfg)[0]
    view = _puzzle_view(double_bottom_df, match, cfg)
    assert view.index[-1] == double_bottom_df.index[match.end_idx]


def test_answer_view_reveals_resolution(double_bottom_df, cfg):
    match = get("double_bottom").detect(double_bottom_df, cfg)[0]
    answer = _answer_view(double_bottom_df, match, cfg)
    puzzle = _puzzle_view(double_bottom_df, match, cfg)
    assert len(answer) >= len(puzzle)
    assert answer.index[-1] > double_bottom_df.index[match.end_idx]


def test_trade_levels_ordering_for_bullish(double_bottom_df, cfg):
    match = get("double_bottom").detect(double_bottom_df, cfg)[0]
    levels = trade_levels(double_bottom_df, match, cfg)
    assert levels["stop"] < levels["entry"] < levels["target"]
    assert levels["risk"] > 0
