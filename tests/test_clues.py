from collections import Counter

from puzzlebook.clues import build_clue_schedule, normalize_mix


def test_equal_mix_splits_evenly():
    schedule = build_clue_schedule({"none": 30, "volume": 30, "price": 30}, 60)
    assert len(schedule) == 60
    assert Counter(schedule) == {"none": 20, "volume": 20, "price": 20}


def test_weighted_mix_respects_proportions():
    schedule = build_clue_schedule({"none": 70, "volume": 15, "price": 15}, 20)
    counts = Counter(schedule)
    assert counts["none"] == 14
    assert counts["volume"] == 3
    assert counts["price"] == 3


def test_empty_mix_returns_no_schedule():
    assert build_clue_schedule(None, 10) == []
    assert build_clue_schedule({}, 10) == []


def test_invalid_weights_are_ignored():
    assert normalize_mix({"none": 1, "bogus": 5, "price": -2}) == {"none": 1.0}
