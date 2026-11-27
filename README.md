# The Chiral Archive

An AI knowledge assistant for the lore of *Death Stranding* and *Death Stranding 2: On the Beach*. Answers cite their sources, and a spoiler filter hides anything past the episode you've reached.

**Status:** Phase 1 done. The lore dataset and a 40-question seed test set are built. See the [roadmap](docs/ROADMAP.md) and [data sources](docs/data-sources.md).

## Layout

| Path | Contents |
|---|---|
| `backend/src/chiral/` | Python package: `ingest`, `rag`, `app` (FastAPI), `eval`, `db` |
| `backend/migrations/` | Plain-SQL database migrations, applied in filename order |
| `backend/tests/` | Pytest suite |
| `frontend/` | Next.js website (Phase 5) |
| `data/` | Collected lore (not committed) |
| `docs/` | Roadmap and design docs |

## Local setup

You need [Docker](https://docs.docker.com/get-docker/), [uv](https://docs.astral.sh/uv/) and `make`.

```bash
cp .env.example .env   # optional until Phase 3: the defaults match docker-compose.yml
make up                # start Postgres (with pgvector) and Redis
make migrate           # apply database migrations
make collect           # download the lore pages from the wiki (about 6 minutes)
make build-data        # turn them into clean records in data/processed/
make lint              # ruff
make test              # pytest
```

Run `make` on its own to list every command.

## Notes

This is a fan project. It isn't affiliated with Kojima Productions or Sony Interactive Entertainment.

Lore text comes from the [Death Stranding Wiki](https://deathstranding.fandom.com) and is licensed [CC BY-SA](https://www.fandom.com/licensing). The archive records the page and revision each passage came from, so answers can cite them.
