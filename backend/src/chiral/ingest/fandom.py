"""Catalog the Death Stranding Wiki and download its lore pages, resumably."""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chiral.ingest.mediawiki import MediaWikiClient
from chiral.ingest.sources import EXCLUDE_CATEGORIES, INCLUDE_CATEGORIES

PARSE_PROPS = "text|sections|categories|revid|displaytitle"


def category_name(raw: str) -> str:
    """'Category:Female_Characters' and 'Female_Characters' both become 'Female Characters'."""
    return raw.removeprefix("Category:").replace("_", " ").strip()


@dataclass
class Article:
    page_id: int
    title: str
    revision_id: int
    length: int = 0
    categories: list[str] = field(default_factory=list)
    redirects: list[str] = field(default_factory=list)  # titles that redirect here


def list_articles(client: MediaWikiClient) -> list[Article]:
    """Every article (namespace 0, not redirects) with its latest revision, visible
    categories, and the titles that redirect to it."""
    articles: dict[int, Article] = {}
    for data in client.query_all(
        generator="allpages",
        gapnamespace=0,
        gapfilterredir="nonredirects",
        gaplimit=50,
        prop="info|categories|redirects",
        cllimit="max",
        clshow="!hidden",
        rdlimit="max",
        rdnamespace=0,
        rdprop="title",
    ):
        for page in data.get("query", {}).get("pages", []):
            article = articles.setdefault(
                page["pageid"], Article(page_id=page["pageid"], title=page["title"], revision_id=0)
            )
            # With continuation, a page can come back in several responses.
            article.revision_id = page.get("lastrevid") or article.revision_id
            article.length = page.get("length") or article.length
            for category in page.get("categories", []):
                name = category_name(category["title"])
                if name not in article.categories:
                    article.categories.append(name)
            for redirect in page.get("redirects", []):
                if redirect["title"] not in article.redirects:
                    article.redirects.append(redirect["title"])
    return sorted(articles.values(), key=lambda a: a.title)


def redirect_map(articles: list[Article]) -> dict[str, str]:
    """Map each redirect title to the article it points at."""
    return {redirect: a.title for a in articles for redirect in a.redirects}


def is_selected(
    article: Article,
    include: frozenset[str] = INCLUDE_CATEGORIES,
    exclude: frozenset[str] = EXCLUDE_CATEGORIES,
) -> bool:
    """Lore pages: in an included category and in no excluded one (exclusion wins)."""
    categories = set(article.categories)
    return bool(categories & include) and not categories & exclude


def raw_page_path(raw_dir: Path, page_id: int) -> Path:
    return raw_dir / "pages" / f"{page_id}.json.gz"


def read_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_json_gz(path: Path, data: Any) -> None:
    """Write atomically, so an interrupted run never leaves a half-written file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def fetch_page(client: MediaWikiClient, article: Article, raw_dir: Path) -> bool:
    """Save the page's parsed HTML unless the saved copy is already at this revision.

    Returns True when it downloaded the page.
    """
    path = raw_page_path(raw_dir, article.page_id)
    if path.exists() and read_json_gz(path)["revision_id"] == article.revision_id:
        return False
    data = client.get(
        action="parse",
        pageid=article.page_id,
        prop=PARSE_PROPS,
        disableeditsection=1,
        disabletoc=1,
    )
    write_json_gz(
        path,
        {
            "page_id": article.page_id,
            "revision_id": data["parse"]["revid"],
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "api_url": client.api_url,
            "response": data,
        },
    )
    return True
