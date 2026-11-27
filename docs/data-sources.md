# Data sources

What the archive is built from, under what license, and what was deliberately left out.
Audit date: 2026-11-27. The rules live in [`backend/src/chiral/ingest/sources.py`](../backend/src/chiral/ingest/sources.py).

## Sources

| Source | Used for | License | Status |
|---|---|---|---|
| [Death Stranding Wiki](https://deathstranding.fandom.com) (Fandom) | Every lore page: characters, places, groups, concepts, episodes | CC BY-SA, as reported by the wiki itself ([fandom.com/licensing](https://www.fandom.com/licensing)) | Collected |
| Wikipedia, *Death Stranding* and *Death Stranding 2: On the Beach* | Plot overviews | CC BY-SA 4.0 | **Not collected.** Wikimedia rate-limited our first request (HTTP 429), and the wiki's 34 episode pages already cover both plots in more detail. Revisit if overviews turn out to be missing. |

Pages are fetched through the wiki's public MediaWiki API (`api.php`), one request at a time with a one-second gap, so a full run makes about 320 requests. The wiki's `robots.txt` sits behind a Cloudflare bot check and couldn't be read from the collector.

## Which pages are collected

The wiki had 1,487 articles at audit time (MediaWiki 1.43.10).

| Group | Pages | Rule |
|---|---|---|
| **Lore (collected)** | 288 | In at least one included category, and in none of the excluded ones |
| **In-game text (left out)** | 634 | Mail (466), SSS Posts (229), Interviews (150), Corpus (17). A page can be in more than one. |
| **Gameplay and wiki pages (skipped)** | 565 | Mostly Orders, Trophies, Weapons, Equipment, Cargo and Items, plus Voice actors and Production staff |

**Why in-game text is left out:** emails, interviews, social posts and Corpus entries are transcripts of text written for the games, so the publisher holds the copyright even when a wiki hosts them. The wiki's own prose already summarizes what they reveal. Adding them is a v2 decision.

**Included categories:**

- **People:** Characters, Death Stranding Characters, Death Stranding 2 Characters, Bridges Personnel, APAC Personnel, Drawbridge Personnel, Fragile Express Personnel, Preppers, Porter, DOOMS, Deceased, Female Characters, Male Characters
- **Places:** Locations, Cities, Destroyed Cities, Distribution Centers, Waystations, Regions, BT territories, Bridges Facilities, APAC Facilities
- **Groups, threats and ideas:** Groups, Enemies, Science, Lore, Technology
- **Story:** Episodes
- **The games and the series:** Death Stranding series, Death Stranding universe

Only direct membership counts. The subcategories of Technology (Cargo, Consumables, Structures, Transportation) are gameplay and stay out.

## Coverage

- **Characters:** 59 tagged for DS1 and 60 for DS2. Twelve appear in both games, and 48 are new in DS2.
- **Episodes:** all 33 have a page. DS1 has its prologue and 15 episodes, and DS2 has 17.
- **Other lore:** 74 locations, 25 groups, 24 science pages, 13 technology pages, 10 enemies and 10 general lore pages.
- **In total:** 288 pages, 1,480 sections and about 215,000 words, plus 254 entities, 822 infobox relations and 164 story events in `data/processed/`.

**Gap: the end of DS2.** Every DS1 episode page has a story write-up except the epilogue (about 29,000 words in all). DS2's Episodes 1–10 do too (about 26,600 words), but **Episodes 11–17 have no story text on the wiki yet**, only a one-line summary. The late DS2 story appears only in pieces inside character and location pages, mostly in sections such as "Sam's Australian Expedition" (61 sections, about 13,000 words). Answers about the end of DS2 will be thin until the wiki catches up or another source fills the gap.

## What's kept from each page

- **Sections:** each heading's text, with its path such as `Story > Meeting Sam`, its anchor and the pages it links to.
- **Infobox fields:** for example *Affiliation*, *Family* and *Region*, split into entries that keep their links and qualifiers, such as `Coffin (mother, deceased)`.
- **Metadata:** the title, the page URL, the URL of the exact revision collected (`?oldid=`), the license, the categories, the page kind and the games it covers.

**Removed:** images, galleries, references, navigation boxes, spoiler notices and quote boxes. These sections are also dropped, along with their subsections:

- **In-game text:** Interviews, SSS Messages, SSS Posts, Mail, Emails, Quotes, Transcript
- **Media and links:** Gallery, Videos, References, See also, External links
- **Gameplay:** Objectives, Walkthrough, Related trophies, Trophies, Connection Rewards

## Known limits

- **Which game a page covers** is exact for characters, which have per-game categories, and for episodes, whose first sentence names the game. Everything else falls back to a rule of thumb: assume DS1 unless the first sentence names only DS2, and add DS2 when the page mentions it. It gets some pages wrong: *Timefall* never mentions DS2 and *Drawbridge* (a DS2 organization) never names the game, so both are tagged DS1 only. Treat `games` as a hint, not a spoiler boundary.
- **Opening summaries are full of spoilers.** They're written with knowledge of both games: Amelie's first sentence calls her "the ka of the sixth extinction entity", and the Ghost Mech page opens with who built them. Phase 4 has to tag these sentence by sentence, not as one section.
- **Infobox fields contain spoilers too.** A character's *Status* or *Cause of death* can give away the ending, so Phase 4 has to tag infobox fields as well as prose.
- **The wiki is a fan wiki.** It contains the occasional error, so answers are only as good as the page they cite.

## Seed test set

[`backend/src/chiral/eval/datasets/seed.jsonl`](../backend/src/chiral/eval/datasets/seed.jsonl) holds 40 questions:

| Type | Count | Notes |
|---|---|---|
| Facts | 16 | |
| Exact names and terms | 5 | |
| Multi-step (two pages) | 4 | |
| Spoiler traps | 10 | Asked at a given episode; each lists the facts the answer must not reveal and where the wiki reveals them |
| Unanswerable | 5 | |

By game, 23 are about DS1, 12 about DS2 and 5 about both.

Each answer cites its evidence as page plus section, and `make test` checks that every citation exists in the collected data. The questions were drafted from the collected text and are marked `verified: false` until a person has checked each one against the wiki. Run `uv run python -m chiral.eval.dataset` in `backend/` for a summary.

## Rebuilding the data

```bash
make collect      # download (skips pages already saved at their current revision)
make build-data   # parse into data/processed/
```

`data/` is not committed. Wiki text is CC BY-SA, so anything that redistributes it must credit the wiki, link to the license and keep the same license.
