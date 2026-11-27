"""Collect lore pages from the Death Stranding Wiki into data/raw/fandom/.

Usage: uv run python -m chiral.ingest.collect [--limit N] [--min-interval SECONDS]

Safe to stop and re-run: pages already saved at their current revision are skipped.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime

import httpx

from chiral.config import get_settings
from chiral.ingest.fandom import fetch_page, is_selected, list_articles, redirect_map
from chiral.ingest.mediawiki import MediaWikiClient, MediaWikiError
from chiral.ingest.sources import FANDOM_API_URL


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Collect lore pages from the Death Stranding Wiki."
    )
    parser.add_argument("--limit", type=int, help="fetch at most this many pages (a quick trial)")
    parser.add_argument(
        "--min-interval", type=float, default=1.0, help="seconds between requests (default: 1)"
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    raw_dir = settings.data_dir / "raw" / "fandom"
    raw_dir.mkdir(parents=True, exist_ok=True)

    with MediaWikiClient(
        FANDOM_API_URL, settings.collector_user_agent, min_interval=args.min_interval
    ) as client:
        site = client.get(action="query", meta="siteinfo", siprop="general|statistics|rightsinfo")
        articles = list_articles(client)
        redirects = redirect_map(articles)
        selected = [article for article in articles if is_selected(article)]
        catalog = {
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "api_url": FANDOM_API_URL,
            "generator": site["query"]["general"]["generator"],
            "statistics": site["query"]["statistics"],
            "license": site["query"]["rightsinfo"],
            "articles": [asdict(a) | {"selected": is_selected(a)} for a in articles],
            "redirects": redirects,
        }
        (raw_dir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1))
        print(
            f"{len(articles)} articles, {len(selected)} selected as lore, "
            f"{len(redirects)} redirects",
            flush=True,
        )

        todo = selected[: args.limit] if args.limit else selected
        downloaded = current = failed = 0
        for done, article in enumerate(todo, 1):
            try:
                if fetch_page(client, article, raw_dir):
                    downloaded += 1
                else:
                    current += 1
            except (MediaWikiError, httpx.HTTPError) as exc:
                failed += 1
                print(f"  skipped {article.title!r}: {exc}", flush=True)
            if done % 25 == 0 or done == len(todo):
                print(
                    f"{done}/{len(todo)} pages: {downloaded} downloaded, "
                    f"{current} already current, {failed} failed",
                    flush=True,
                )


if __name__ == "__main__":
    main()
