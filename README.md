# The Chiral Archive

An AI knowledge assistant for the lore of *Death Stranding* and *Death Stranding 2: On the Beach*. Answers cite their sources, and a spoiler filter hides anything past the episode you've reached.

**Status:** Phase 0, project setup. See the [roadmap](docs/ROADMAP.md).

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
make lint              # ruff
make test              # pytest
```

Run `make` on its own to list every command.

## Notes

This is a fan project. It isn't affiliated with Kojima Productions or Sony Interactive Entertainment.
