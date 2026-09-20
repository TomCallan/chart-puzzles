from collections import Counter

from puzzlebook.questions import (
    assign_clues,
    build_question_schedule,
    normalize_mix,
    resolve_clue,
)


def test_question_mix_respects_proportions():
    schedule = build_question_schedule(
        {"identify": 40, "direction": 30, "levels": 30}, 100
    )
    assert Counter(schedule) == {"identify": 40, "direction": 30, "levels": 30}


def test_invalid_clue_combinations_are_resolved():
    # a price clue would reveal where price went
    assert resolve_clue("levels", "price") == "none"
    assert resolve_clue("direction", "price") == "none"
    # a volume clue is fine everywhere
    assert resolve_clue("levels", "volume") == "volume"
    assert resolve_clue("direction", "volume") == "volume"
    assert resolve_clue("identify", "price") == "price"


def test_invalid_questions_are_ignored():
    assert normalize_mix({"identify": 1, "nonsense": 9}) == {"identify": 1.0}


def test_assign_clues_honours_mix_and_validity():
    questions = build_question_schedule(
        {"identify": 40, "direction": 30, "levels": 30}, 60
    )
    clues = assign_clues(questions, {"none": 30, "volume": 30, "price": 30})
    assert Counter(clues) == {"none": 20, "volume": 20, "price": 20}
    # price clues only ever land on identify puzzles
    assert all(c != "price" or q == "identify" for q, c in zip(questions, clues))
    # and no question type is stuck with a single clue
    for question in ("identify", "direction", "levels"):
        used = {c for q, c in zip(questions, clues) if q == question}
        assert len(used) >= 2, (question, used)
