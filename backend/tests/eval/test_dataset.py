from collections import Counter

import pytest
from pydantic import ValidationError

from chiral.config import get_settings
from chiral.eval.dataset import Question, load_questions, missing_evidence


def test_the_seed_set_follows_the_rules():
    questions = load_questions()  # validates every line and checks ids are unique
    types = Counter(q.type for q in questions)
    games = Counter(q.game for q in questions)

    assert len(questions) == 40
    assert types["spoiler_trap"] >= 10
    assert types["unanswerable"] >= 5
    assert games["DS1"] and games["DS2"]


def test_spoiler_traps_need_progress_and_forbidden_facts():
    with pytest.raises(ValidationError, match="spoiler traps need progress"):
        Question(
            id="x",
            question="Who is Lou?",
            type="spoiler_trap",
            game="DS1",
            answer="A Bridge Baby.",
            evidence=[{"page": "BB-28"}],
        )


def test_unanswerable_questions_have_no_evidence():
    with pytest.raises(ValidationError, match="no evidence"):
        Question(
            id="x",
            question="What is Sam's favourite colour?",
            type="unanswerable",
            game="DS1",
            answer="The archive doesn't say.",
            evidence=[{"page": "Sam"}],
        )


def test_evidence_matches_the_collected_pages():
    pages = get_settings().data_dir / "processed" / "pages.jsonl"
    if not pages.exists():
        pytest.skip("no collected data; run `make collect build-data` first")

    assert missing_evidence(load_questions(), pages) == []
