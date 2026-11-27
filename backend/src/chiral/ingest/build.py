"""Turn the raw wiki pages into clean records in data/processed/.

Usage: uv run python -m chiral.ingest.build

Writes pages.jsonl (one record per page, with sections and infobox fields),
entities.jsonl, relations.jsonl, events.jsonl and summary.json.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from chiral.config import get_settings
from chiral.ingest.fandom import read_json_gz
from chiral.ingest.parse import parse_page
from chiral.ingest.tables import entity_record, episode_order, event_records, relation_records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def summarize(pages, entities, relations, events) -> dict[str, Any]:
    by_kind_game = Counter((page["kind"], "+".join(page["games"]) or "none") for page in pages)
    return {
        "pages": len(pages),
        "sections": sum(len(page["sections"]) for page in pages),
        "words": sum(len(s["text"].split()) for page in pages for s in page["sections"]),
        "pages_by_kind_and_game": {f"{k} / {g}": n for (k, g), n in sorted(by_kind_game.items())},
        "games_source": dict(Counter(page["games_source"] for page in pages)),
        "entities": len(entities),
        "relations": len(relations),
        "relations_between_collected_pages": sum(1 for r in relations if r["target_id"]),
        "events": len(events),
        "episodes": [
            f"{p['episode']['game']} {p['episode']['number']:>2}: {p['title']}"
            for p in episode_order(pages)
        ],
    }


def main() -> None:
    settings = get_settings()
    raw_dir = settings.data_dir / "raw" / "fandom"
    out_dir = settings.data_dir / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog = json.loads((raw_dir / "catalog.json").read_text())
    selected = {a["page_id"] for a in catalog["articles"] if a["selected"]}
    pages = []
    for path in sorted((raw_dir / "pages").glob("*.json.gz")):
        raw = read_json_gz(path)
        if raw["page_id"] in selected:
            pages.append(parse_page(raw))
    pages.sort(key=lambda page: page["title"])

    entities = [entity_record(page) for page in pages if page["kind"] != "episode"]
    relations = relation_records(pages, catalog["redirects"])
    events = event_records(pages)

    write_jsonl(out_dir / "pages.jsonl", pages)
    write_jsonl(out_dir / "entities.jsonl", entities)
    write_jsonl(out_dir / "relations.jsonl", relations)
    write_jsonl(out_dir / "events.jsonl", events)
    summary = summarize(pages, entities, relations, events)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
