"""The question sets used to evaluate the archive, and the rules every question must follow.

Each line of a dataset file is one JSON question. `evidence` points at the wiki
sections that support the answer, as page title plus section path (an empty path
means the page's opening summary). Pointing at sections rather than chunks keeps
the labels valid when the chunking changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DATASETS_DIR = Path(__file__).parent / "datasets"
SEED_PATH = DATASETS_DIR / "seed.jsonl"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: str
    section: list[str] = Field(default_factory=list)  # [] means the page's opening summary


class Progress(BaseModel):
    """How far the asker has played. Episode 0 is the DS1 prologue."""

    model_config = ConfigDict(extra="forbid")

    game: Literal["DS1", "DS2"]
    episode: int = Field(ge=0)


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    type: Literal["fact", "name", "multi_hop", "spoiler_trap", "unanswerable"]
    game: Literal["DS1", "DS2", "both"]
    # None means the asker has finished both games, so nothing is a spoiler.
    progress: Progress | None = None
    # The expected answer. For unanswerable questions, what a good refusal says.
    answer: str
    evidence: list[Evidence] = Field(default_factory=list)
    # Spoiler traps: facts the answer must not reveal at this progress, and where
    # the wiki reveals them (so Phase 4's spoiler tags can be checked against it).
    must_not_mention: list[str] = Field(default_factory=list)
    spoiler_evidence: list[Evidence] = Field(default_factory=list)
    # Drafted questions start unverified; a person checks each one against the wiki.
    verified: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def follow_the_rules_for_its_type(self) -> Question:
        if self.type == "unanswerable":
            if self.evidence:
                raise ValueError(f"{self.id}: unanswerable questions have no evidence")
        elif not self.evidence:
            raise ValueError(f"{self.id}: needs evidence")
        is_trap = self.type == "spoiler_trap"
        if is_trap and (self.progress is None or not self.must_not_mention):
            raise ValueError(f"{self.id}: spoiler traps need progress and must_not_mention")
        if is_trap and not self.spoiler_evidence:
            raise ValueError(f"{self.id}: spoiler traps need spoiler_evidence")
        if not is_trap and (self.must_not_mention or self.spoiler_evidence):
            raise ValueError(f"{self.id}: only spoiler traps list forbidden facts")
        return self


def missing_evidence(questions: list[Question], pages_path: Path) -> list[str]:
    """Evidence that doesn't match a page and section in data/processed/pages.jsonl."""
    sections: dict[str, set[tuple[str, ...]]] = {}
    with pages_path.open(encoding="utf-8") as f:
        for line in f:
            page = json.loads(line)
            sections[page["title"]] = {tuple(s["path"]) for s in page["sections"]}
    problems = []
    for q in questions:
        for evidence in [*q.evidence, *q.spoiler_evidence]:
            paths = sections.get(evidence.page)
            if paths is None:
                problems.append(f"{q.id}: no page {evidence.page!r}")
            elif tuple(evidence.section) not in paths:
                problems.append(f"{q.id}: {evidence.page!r} has no section {evidence.section}")
    return problems


def main() -> None:
    """Validate the seed set and check its evidence against the collected data."""
    from collections import Counter

    from chiral.config import get_settings

    questions = load_questions()
    print(f"{len(questions)} questions")
    print("by type:", dict(Counter(q.type for q in questions)))
    print("by game:", dict(Counter(q.game for q in questions)))
    print("verified:", sum(q.verified for q in questions))
    pages_path = get_settings().data_dir / "processed" / "pages.jsonl"
    if not pages_path.exists():
        print(
            "data/processed/pages.jsonl not found; run `make collect build-data` to check evidence"
        )
        return
    problems = missing_evidence(questions, pages_path)
    print("evidence problems:", problems or "none")
    if problems:
        raise SystemExit(1)


def load_questions(path: Path = SEED_PATH) -> list[Question]:
    questions = [
        Question.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ids = [q.id for q in questions]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate question ids: {duplicates}")
    return questions


if __name__ == "__main__":
    main()
