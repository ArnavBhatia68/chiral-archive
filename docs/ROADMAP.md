# The Chiral Archive: Roadmap

## Phase 0: Setup
- [x] Create the GitHub repo with `backend/` (ingest, rag, app, eval, tests), `frontend/`, `data/` (not committed) and `docs/`
- [x] Set up Python with `uv`, `ruff` and `pytest`
- [x] Add GitHub Actions to run lint and tests on every push
- [x] Add `docker-compose.yml` with Postgres + pgvector and Redis
- [ ] Get an Anthropic API key and set a monthly spend limit

**Deliverable:** A repo with passing CI and a local database.

## Phase 1: Data collection
- [x] Confirm sources and licenses: the Death Stranding Wiki (Fandom, CC BY-SA) as the main source, Wikipedia (CC BY-SA 4.0) for plot overviews
- [x] Leave in-game email, interview and Corpus transcripts out of v1 because the publisher holds the copyright; add fan theories later
- [x] Count how many pages cover DS2 in each category, and choose which categories to include (skip gameplay pages)
- [x] Build a collector that uses the wiki's MediaWiki API: rate-limited, able to resume after a failure, with raw responses saved to disk
- [x] Store each page with its title, URL, revision ID, categories, sections, infobox fields and license
- [x] Extract structured tables: `entities`, `relations`, `events`
- [x] Write a seed test set of 40 questions with answers and their source page and section, including spoiler traps and questions the archive can't answer

**Deliverable:** A DS1 + DS2 dataset with sources and licenses, plus a seed test set.

**Results** ([details](data-sources.md)):
- **Collected:** 288 lore pages (about 215,000 words), with 254 entities, 822 relations and 164 story events.
- **Wikipedia:** left out, because it rate-limited every request. The wiki's episode pages cover the plot instead.
- **Gap:** DS2 Episodes 11–17 have no story text on the wiki yet.
- **Seed questions:** all 40 are drafts (`verified: false`) until someone checks them against the wiki.

## Phase 2: Data processing and embeddings
- [x] Clean the text: strip markup, navigation boxes and references, but keep the sections (done by the Phase 1 parser)
- [ ] Split each section into chunks of about 350 tokens with 50 tokens of overlap, and start each chunk with `Page > Section`
- [ ] Embed the chunks with `BAAI/bge-small-en-v1.5`, which reads up to 512 tokens (`all-MiniLM-L6-v2` cuts off at 256)
- [ ] Create the tables: `documents`, `chunks` (vector, full-text index, spoiler columns), `entities`, `relations`, `events`
- [ ] Implement exact vector search first, then add an HNSW index and compare recall
- [ ] Measure Recall@5 on the seed set and compare chunk sizes

Chunk record (example values):
```json
{
  "chunk_id": "the-beach#03",
  "doc_title": "The Beach",
  "section": "The Beach > Overview",
  "games": ["DS1", "DS2"],
  "category": "Concept",
  "content": "...",
  "source_url": "https://deathstranding.fandom.com/wiki/The_Beach?oldid=<revision>",
  "license": "CC BY-SA",
  "canon": true,
  "reveal": {"game": "DS1", "episode": 3},
  "reveal_index": 3,
  "spoiler_source": "llm",
  "embedding_model": "bge-small-en-v1.5"
}
```
`reveal_index` is the chunk's position in story order: DS1 episodes first, then DS2. Chunks that haven't been tagged get the highest value, so they stay hidden.

**Deliverable:** A searchable vector database with measured retrieval quality.

## Phase 3: Core RAG pipeline
- [ ] Embed each question and retrieve the top 5 chunks (accept a progress argument, but don't filter yet)
- [ ] Generate answers with `claude-opus-5-5` (`effort: "low"`), using only the retrieved chunks
- [ ] Pass the chunks as `search_result` blocks with citations turned on, and link each citation to its source URL
- [ ] Handle refusals, timeouts and retries
- [ ] Create the FastAPI endpoints `POST /api/ask` and `GET /api/health`
- [ ] Log every request: chunks, scores, time per step, tokens and cost
- [ ] Write tests for chunking, retrieval and the API, with Claude mocked

**Deliverable:** A working RAG assistant that returns cited answers through an API. This is your first functional version.

## Phase 4: Advanced RAG and spoiler engine
**Retrieval**
- [ ] Add Postgres full-text search and merge its results with vector search (Reciprocal Rank Fusion)
- [ ] Rerank the top ~30 results down to 5 with `cross-encoder/ms-marco-MiniLM-L-6-v2`
- [ ] Check that both models fit in your hosting's memory; if they don't, run them with ONNX (e.g. `fastembed`)
- [ ] Reply "not in the archive" when the best rerank score is below a threshold

**Spoilers**
- [ ] Write a short synopsis of each episode and a list of the biggest twists
- [ ] Tag each section with the episode that reveals it: use the page's episode headings where they exist and have Claude tag the rest in a batch job
- [ ] Tag opening summaries and infobox fields sentence by sentence, since they're written with knowledge of both games
- [ ] Review twist-related sections by hand, plus a random sample
- [ ] Apply the progress filter inside both searches, before merging and reranking
- [ ] Check every answer for spoilers with a twist-list scan and a Claude judge; if it fails, regenerate it or return a safe answer
- [ ] When the filter removed the answer, reply "covered later in the story"

**Conversation, streaming and caching**
- [ ] Rewrite follow-up questions so they make sense on their own
- [ ] Stream answers only to users who have finished both games; check everyone else's answer before sending it
- [ ] Cache answers in Redis, keyed on the question, progress, index version, prompt version and model

**Deliverable:** A spoiler-aware RAG engine with hybrid search and reranking.

## Phase 5: Frontend
- [ ] Set up Next.js + Tailwind with a dark, cinematic, minimal design that uses only original visuals
- [ ] Build the progress selector (game + episode) and send it with every request
- [ ] Build Archive Chat with streaming and expandable citation cards
- [ ] Build the Home page with spoiler-free suggested questions
- [ ] Build the Concepts and Characters pages, filtered by progress
- [ ] Add share links that show recipients a spoiler warning first
- [ ] Build the Timeline page (stretch goal)

**Deliverable:** A polished, usable website.

## Phase 6: Evaluation and testing
- [ ] Grow the test set to ~200 questions (Claude drafts them, you verify each one)
- [ ] Compare four setups: no RAG, vector search, hybrid, and hybrid + rerank
- [ ] Measure Recall@5, accuracy, whether citations support the answer, hallucination rate, spoiler leakage, p50/p95 latency and cost per answer
- [ ] Check the Claude grader against ~30 answers you grade by hand
- [ ] Run eval jobs through the Message Batches API
- [ ] Report results by game and question type
- [ ] Add a CI check that fails if Recall@5 drops

**Deliverable:** An evaluation report anyone can reproduce.

## Phase 7: Deployment and documentation
- [ ] Dockerize the backend with the model files included
- [ ] Deploy Postgres + pgvector on Supabase
- [ ] Deploy the backend on Render and the frontend on Vercel
- [ ] Set up Redis on Upstash or Render Key Value
- [ ] Add rate limits, CORS rules, input length limits and Sentry
- [ ] Write the README (demo, architecture, eval results, setup, data attribution) and the architecture docs

**Deliverable:** A public website and a documented GitHub repo.
