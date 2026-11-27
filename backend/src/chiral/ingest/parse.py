"""Turn a raw `action=parse` response into a clean page record.

A record keeps what later phases need: title, URLs (including the exact revision),
license, categories, kind, games, infobox fields and the text of each section.
Noise is removed here: images, galleries, references, navigation boxes, notices,
quote boxes, and the sections listed in `sources.DROP_SECTIONS`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup, Comment, NavigableString, PageElement, Tag

from chiral.ingest.fandom import category_name
from chiral.ingest.sources import (
    DROP_SECTIONS,
    FANDOM_LICENSE,
    FANDOM_LICENSE_URL,
    FANDOM_WIKI_URL,
    GAME_CATEGORIES,
    KIND_BY_CATEGORY,
)

HEADINGS = {"h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
# Whole elements with no lore prose. The infobox is parsed before these are removed.
NOISE = ", ".join(
    [
        "aside",
        "figure",
        "style",
        "script",
        "nav",
        "blockquote",
        ".thumb",
        ".gallery",
        ".wikia-gallery",
        ".navbox",
        ".reflist",
        ".references",
        ".mw-references-wrap",
        ".toc",
        "#toc",
        ".mw-empty-elt",
        ".wds-tabs__wrapper",
    ]
)
INLINE_NOISE = "sup.reference, .reference, .mw-editsection, style, script"
DATA_TABLE_CLASSES = frozenset({"wikitable", "article-table", "fandom-table"})
PLACEHOLDERS = frozenset({"tba", "tbd", "wip"})  # editors' stand-ins for missing text
INLINE_TAGS = frozenset(
    {
        "a",
        "abbr",
        "b",
        "big",
        "br",
        "code",
        "em",
        "font",
        "i",
        "s",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "u",
    }
)
SKIP_LINK_PREFIXES = ("File:", "Category:", "Special:", "Template:", "User:", "Help:", "Talk:")
EPISODE_TITLE = re.compile(r"^(?:Episode (?P<number>\d+)|Prologue):")
DS2_NAME = re.compile(r"Death Stranding 2")
DS1_NAME = re.compile(r"Death Stranding(?! 2)")


@dataclass
class Section:
    level: int
    heading: str | None
    path: list[str]
    anchor: str | None
    paragraphs: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def link_title(a: Tag) -> str | None:
    """The wiki page an <a> points at; None for files, categories, red links and other sites."""
    href = str(a.get("href", "")).removeprefix("https://deathstranding.fandom.com")
    if not href.startswith("/wiki/") or "new" in a.get("class", []):
        return None
    title = a.get("title") or unquote(href.removeprefix("/wiki/").split("#")[0]).replace("_", " ")
    title = str(title)
    return None if title.startswith(SKIP_LINK_PREFIXES) else title


def links_in(tag: Tag) -> list[str]:
    anchors = [tag] if tag.name == "a" else tag.find_all("a")
    return list(dict.fromkeys(t for a in anchors if (t := link_title(a))))


def list_lines(lst: Tag, depth: int = 0) -> list[str]:
    """One line per list item, with nested lists indented under their parent item."""
    lines = []
    for li in lst.find_all("li", recursive=False):
        nested = [n.extract() for n in li.find_all(["ul", "ol"], recursive=False)]
        if text := clean(li.get_text()):
            lines.append(f"{'  ' * depth}- {text}")
        for sublist in nested:
            lines.extend(list_lines(sublist, depth + 1))
    return lines


def block_text(el: Tag) -> str:
    """Readable text for one block: list items and table rows each on their own line."""
    if el.name in ("ul", "ol"):
        return "\n".join(list_lines(el))
    if el.name == "dl":
        return "\n".join(t for x in el.find_all(["dt", "dd"]) if (t := clean(x.get_text())))
    if el.name == "table":
        rows = []
        for tr in el.find_all("tr"):
            cells = [clean(c.get_text()) for c in tr.find_all(["th", "td"], recursive=False)]
            if any(cells):
                rows.append(" | ".join(cells))
        return "\n".join(rows)
    return clean(el.get_text())


def heading_level(el: Tag) -> int:
    if el.name in HEADINGS:
        return HEADINGS[el.name]
    if el.name == "div" and "mw-heading" in el.get("class", []):
        inner = el.find(list(HEADINGS))
        return HEADINGS[inner.name] if inner else 0
    return 0


def heading_parts(el: Tag) -> tuple[str, str | None]:
    h = el if el.name in HEADINGS else el.find(list(HEADINGS))
    with_id = h if h.get("id") else h.find(id=True)
    return clean(h.get_text()), (str(with_id["id"]) if with_id else None)


def inline_block(nodes: list[PageElement]) -> tuple[Any, ...] | None:
    """Merge a run of loose text and inline tags into one paragraph."""
    text = clean(
        "".join(
            "\n"
            if isinstance(n, Tag) and n.name == "br"
            else n.get_text()
            if isinstance(n, Tag)
            else str(n)
            for n in nodes
        )
    )
    links = list(dict.fromkeys(link for n in nodes if isinstance(n, Tag) for link in links_in(n)))
    return ("text", text, links) if text else None


def iter_blocks(container: Tag) -> Iterator[tuple[Any, ...]]:
    """Yield ("heading", level, text, anchor) and ("text", text, links) in document order."""
    inline: list[PageElement] = []  # some pages put prose straight into a div, without <p>
    for el in container.children:
        if isinstance(el, Comment):
            continue
        if isinstance(el, NavigableString) or (isinstance(el, Tag) and el.name in INLINE_TAGS):
            inline.append(el)
            continue
        if not isinstance(el, Tag):
            continue
        if block := inline_block(inline):
            yield block
        inline.clear()
        if level := heading_level(el):
            yield ("heading", level, *heading_parts(el))
        elif el.name == "div":
            yield from iter_blocks(el)  # containers such as tabbers
        elif el.name == "table" and not DATA_TABLE_CLASSES & set(el.get("class", [])):
            continue  # notices, navboxes and quote boxes; only data tables are kept
        else:
            links = links_in(el)  # before block_text, which restructures nested lists
            if text := block_text(el):
                yield ("text", text, links)
    if block := inline_block(inline):
        yield block


def split_sections(root: Tag, drop: frozenset[str] = DROP_SECTIONS) -> list[Section]:
    lead = Section(level=1, heading=None, path=[], anchor=None)
    sections = [lead]
    current: Section | None = lead
    path: list[str] = []
    dropping_below: int | None = None  # level of the dropped heading we're inside
    for block in iter_blocks(root):
        if block[0] == "heading":
            _, level, heading, anchor = block
            if dropping_below is not None and level > dropping_below:
                continue
            dropping_below = None
            path = path[: level - 2] + [heading]
            if heading.casefold() in drop:
                dropping_below, current = level, None
                continue
            current = Section(level=level, heading=heading, path=list(path), anchor=anchor)
            sections.append(current)
        elif current is not None:
            _, text, links = block
            if text and text.casefold() not in PLACEHOLDERS:
                current.paragraphs.append(text)
                current.links.extend(link for link in links if link not in current.links)
    return [s for s in sections if s.paragraphs]


def value_entries(value: Tag) -> list[dict[str, Any]]:
    """Split an infobox value into entries at <br> and list items, keeping each entry's links."""
    children = [c for c in value.children if isinstance(c, Tag) or clean(str(c))]
    while (
        len(children) == 1
        and isinstance(children[0], Tag)
        and children[0].name in ("p", "span", "div")
    ):
        value = children[0]
        children = [c for c in value.children if isinstance(c, Tag) or clean(str(c))]

    entries: list[dict[str, Any]] = []
    parts: list[str] = []
    links: list[str] = []

    def flush() -> None:
        if text := clean("".join(parts)):
            entries.append({"text": text, "links": list(dict.fromkeys(links))})
        parts.clear()
        links.clear()

    for node in value.children:
        if isinstance(node, Comment):
            continue
        if isinstance(node, Tag) and node.name == "br":
            flush()
        elif isinstance(node, Tag) and node.name in ("ul", "ol"):
            flush()
            for li in node.find_all("li"):
                parts.append(li.get_text())
                links.extend(links_in(li))
                flush()
        elif isinstance(node, Tag):
            parts.append(node.get_text())
            links.extend(links_in(node))
        else:
            parts.append(str(node))
    flush()
    return entries


def parse_infobox(root: Tag) -> list[dict[str, Any]]:
    box = root.select_one("aside.portable-infobox")
    if box is None:
        return []
    for noise in box.select(INLINE_NOISE):
        noise.decompose()
    tab_labels = {t.get("data-ref"): clean(t.get_text()) for t in box.select(".pi-section-tab")}
    fields: list[dict[str, Any]] = []
    group: str | None = None
    for item in box.select(".pi-item"):
        classes = item.get("class", [])
        if "pi-header" in classes:
            group = clean(item.get_text()) or None
            continue
        value = item.select_one(".pi-data-value") if "pi-data" in classes else None
        if value is None:
            continue
        entries = value_entries(value)
        if not entries:
            continue
        label = item.select_one(".pi-data-label")
        panel = item.find_parent(class_="pi-section-content")
        fields.append(
            {
                "key": item.get("data-source"),
                "label": clean(label.get_text()) if label else item.get("data-source"),
                "group": group,
                "tab": tab_labels.get(panel.get("data-ref")) if panel else None,
                "text": "; ".join(entry["text"] for entry in entries),
                "entries": entries,
            }
        )
    return fields


def page_kind(categories: list[str]) -> str:
    for kind, names in KIND_BY_CATEGORY:
        if names.intersection(categories):
            return kind
    return "other"


def infer_games(kind: str, categories: list[str], lead: str, text: str) -> tuple[list[str], str]:
    """Which games a page covers, and how we know: "category", "lead" or "heuristic"."""
    by_category = [
        game for game, names in GAME_CATEGORIES.items() if names.intersection(categories)
    ]
    if by_category:
        return by_category, "category"
    if kind == "episode":
        return (["DS2"] if DS2_NAME.search(lead) else ["DS1"]), "lead"
    # Most pages predate DS2, so DS1 is the default. A lead that names only DS2
    # marks a DS2-only page; any mention of DS2 adds it.
    ds2_only = bool(DS2_NAME.search(lead)) and not DS1_NAME.search(lead)
    games = ([] if ds2_only else ["DS1"]) + (["DS2"] if DS2_NAME.search(text) else [])
    return games, "heuristic"


def episode_info(title: str, lead: str) -> dict[str, Any] | None:
    match = EPISODE_TITLE.match(title)
    if not match:
        return None
    number = int(match["number"]) if match["number"] else 0  # the prologue is episode 0
    return {"game": "DS2" if DS2_NAME.search(lead) else "DS1", "number": number}


def page_url(title: str, wiki_url: str = FANDOM_WIKI_URL) -> str:
    return wiki_url + quote(title.replace(" ", "_"), safe=":/()',!")


def parse_page(raw: dict[str, Any]) -> dict[str, Any]:
    parsed = raw["response"]["parse"]
    soup = BeautifulSoup(parsed["text"], "html.parser")
    root = soup.select_one("div.mw-parser-output") or soup

    infobox = parse_infobox(root)
    for noise in root.select(f"{NOISE}, {INLINE_NOISE}"):
        noise.decompose()
    sections = split_sections(root)

    title = parsed["title"]
    categories = [
        category_name(c["category"]) for c in parsed.get("categories", []) if not c.get("hidden")
    ]
    lead = sections[0].paragraphs[0] if sections and sections[0].heading is None else ""
    all_text = " ".join(p for s in sections for p in s.paragraphs)
    all_text += " " + " ".join(f["text"] for f in infobox)
    kind = page_kind(categories)
    games, games_source = infer_games(kind, categories, lead, all_text)
    url = page_url(title)
    return {
        "page_id": raw["page_id"],
        "title": title,
        "url": url,
        "revision_id": parsed["revid"],
        "revision_url": f"{url}?oldid={parsed['revid']}",
        "fetched_at": raw["fetched_at"],
        "license": FANDOM_LICENSE,
        "license_url": FANDOM_LICENSE_URL,
        "kind": kind,
        "games": games,
        "games_source": games_source,
        "categories": categories,
        "episode": episode_info(title, lead) if kind == "episode" else None,
        "infobox": infobox,
        "sections": [
            {
                "heading": s.heading,
                "level": s.level,
                "path": s.path,
                "anchor": s.anchor,
                "text": "\n\n".join(s.paragraphs),
                "links": s.links,
            }
            for s in sections
        ],
    }
