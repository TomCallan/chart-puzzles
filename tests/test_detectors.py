from puzzlebook.charts import _view
from puzzlebook.patterns import build_detectors, score_matches
from puzzlebook.patterns.base import available


def test_registry_has_expected_patterns():
    names = available()
    for expected in ("bullish_engulfing", "double_bottom", "head_and_shoulders"):
        assert expected in names


def test_double_bottom_is_detected(double_bottom_df, cfg):
    from puzzlebook.patterns.base import get

    matches = get("double_bottom").detect(double_bottom_df, cfg)
    assert matches, "expected at least one double bottom"
    best = max(matches, key=lambda m: m.end_idx)
    assert best.direction == "bullish"
    assert best.end_idx > best.start_idx
    assert "neckline" in best.meta


def test_all_detectors_run_without_error(random_df, cfg):
    for detector in build_detectors(cfg):
        matches = detector.detect(random_df, cfg)
        assert isinstance(matches, list)


def test_scores_are_bounded(random_df, cfg):
    for detector in build_detectors(cfg):
        for match in detector.detect(random_df, cfg):
            score_matches(random_df, [match], cfg)
            assert 0.0 <= match.score <= 100.0


def test_no_lookahead_in_rendered_view(double_bottom_df, cfg):
    """The last rendered bar must be the pattern completion bar."""
    from puzzlebook.patterns.base import get

    matches = get("double_bottom").detect(double_bottom_df, cfg)
    assert matches
    for match in matches:
        view = _view(double_bottom_df, match, cfg)
        assert view.index[-1] == double_bottom_df.index[match.end_idx]
        assert len(view) <= cfg["chart"]["lookback_bars"]
