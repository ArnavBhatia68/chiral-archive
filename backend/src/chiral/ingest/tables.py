"""Build the structured tables the explorer pages need: entities, relations and events."""

from __future__ import annotations

import re
from typing import Any

GAME_ORDER = {"DS1": 0, "DS2": 1}
PARENTHETICAL = re.compile(r"\(([^()]*)\)")


def entity_record(page: dict[str, Any]) -> dict[str, Any]:
    lead = (
        page["sections"][0] if page["sections"] and page["sections"][0]["heading"] is None else None
    )
    fields = {}
    for field in page["infobox"]:
        label = f"{field['label']} ({field['tab']})" if field.get("tab") else field["label"]
        fields[label] = field["text"]
    return {
        "page_id": page["page_id"],
        "name": page["title"],
        "kind": page["kind"],
        "games": page["games"],
        "categories": page["categories"],
        "url": page["url"],
        "summary": lead["text"].split("\n\n")[0] if lead else "",
        "fields": fields,
    }


def relation_records(
    pages: list[dict[str, Any]], redirects: dict[str, str]
) -> list[dict[str, Any]]:
    """One row per link in an infobox value, e.g. Fragile -Family-> Coffin (mother, deceased)."""
    by_title = {page["title"]: page for page in pages}
    rows = []
    for page in pages:
        for field in page["infobox"]:
            for entry in field["entries"]:
                qualifier = PARENTHETICAL.search(entry["text"])
                for link in entry["links"]:
                    target = by_title.get(redirects.get(link, link))
                    rows.append(
                        {
                            "source_id": page["page_id"],
                            "source": page["title"],
                            "field": field["label"],
                            "target_id": target["page_id"] if target else None,
                            "target": target["title"] if target else link,
                            "qualifier": qualifier.group(1).strip() if qualifier else None,
                            "text": entry["text"],
                        }
                    )
    return rows


def episode_order(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Episode pages in story order: DS1 (prologue first), then DS2."""
    episodes = [page for page in pages if page["episode"]]
    return sorted(
        episodes, key=lambda p: (GAME_ORDER[p["episode"]["game"]], p["episode"]["number"])
    )


def event_records(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Story events: each subsection of an episode's Story section, in order.

    `story_index` is the episode's position in story order across both games, the
    scale that spoiler tags will use in Phase 4.
    """
    rows = []
    for story_index, page in enumerate(episode_order(pages)):
        game, number = page["episode"]["game"], page["episode"]["number"]
        story = [s for s in page["sections"] if s["path"] and s["path"][0] == "Story"]
        parts = [s for s in story if s["level"] > 2] or story
        for seq, section in enumerate(parts, 1):
            anchor = f"#{section['anchor']}" if section["anchor"] else ""
            rows.append(
                {
                    "event_id": f"{game}-E{number:02d}-{seq:02d}",
                    "game": game,
                    "episode": number,
                    "episode_title": page["title"],
                    "story_index": story_index,
                    "seq": seq,
                    "title": section["heading"],
                    "text": section["text"],
                    "page_id": page["page_id"],
                    "url": page["url"] + anchor,
                }
            )
    return rows
