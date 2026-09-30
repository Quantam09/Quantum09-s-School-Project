# Learn-and-Reward-LAR — Missions A + B (Developer A and B scopes)

Implementation of **Developer A's** (resource layer + voice AI, README §7.1) and
**Developer B's** (learning layer + dialogue AI, README §7.2) scopes, following the
platform spec: modular monolith, per-module database schemas, OpenAPI-first, English
UI/API/DB content with Luxembourgish only as learning content.

```
apps/web/                 Next.js 14 (App Router, TS, Tailwind, TanStack Query)
services/api/             FastAPI modular monolith
  app/modules/resource/   resources, files, review flow, voice consents  (resource schema)
  app/modules/ai_voice/   ASR/TTS/embedding providers, job queue, RAG index  (ai_voice schema)
  app/modules/learning/   courses, lessons, exercises, enrollments, practice,
                          chat_messages, certificates  (learning schema)
  app/modules/ai_chat/    DeepSeek adapter, RAG-augmented chat engine
  app/core/               PLACEHOLDER auth (Developer C scope) — see below
  app/shared/             config, errors, pagination, storage, coin + RAG adapters
  alembic/versions/       per-module migrations (core, learning, resource, ai_voice)
  tests/                  pytest suite (47 tests, in-memory SQLite, mock AI providers)
infra/docker-compose.yml  PostgreSQL 16 + pgvector, Redis, MinIO, api, RQ worker, web
docs/contracts/           exported OpenAPI contract
```

## Run locally (no Docker required)

Backend (SQLite fallback + auto-created tables + seed data):

```bash
cd services/api
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # Linux/macOS: .venv/bin/pip ...
cp .env.example .env                          # set DEEPSEEK_API_KEY
.venv/Scripts/uvicorn app.main:app --port 8000
```

First real ASR/embedding use downloads `whisper-small` (~244MB) and
`multilingual-e5-small` (~470MB) once, in background threads; set `ASR_MODE=mock`
/ `EMBEDDINGS_MODE=mock` to stay fully offline.

Frontend:

```bash
cd apps/web
npm install
npm run dev            # http://localhost:3000
```

Full stack (PostgreSQL + pgvector, Redis + RQ worker, MinIO, Alembic migrations):

```bash
cd infra
cp ../.env.example ../.env    # set DEEPSEEK_API_KEY
docker compose up --build
```

## Mission A — resource layer + voice AI

**APIs** (`resource` + `ai_voice` schemas): `POST /resources` (license-tag
template per README §8.2), `POST /resources/{id}/files` (multipart, type/size
whitelist), `POST /resources/{id}/submit`, `POST /reviews/{id}/approve|reject`
(reviewer role; approval pays `REWARD_CONTRIBUTION` +10 contributor / +5 community
through the coin adapter), `POST /voice-consents` (+ revoke; recording/audit only —
no voice cloning per §10.5), `GET /resources?scope=library|mine|review`,
`POST /resources/{id}/transcript` (human proofreading → RAG indexing),
`POST /resources/{id}/revoke` (cascades `revoked_at` into `rag_chunks`),
`POST /ai/asr/jobs`, `POST /ai/tts/jobs`, `GET /ai/jobs/{id}`, `POST /rag/search`.

**Pipeline** (§10.1/10.3): upload → license + voice-consent gate → ASR job
(faster-whisper; `lb` is not in Whisper's language set, so auto-detect + Luxembourgish
prompt) → **human proofreading** → chunk + embed (multilingual-e5-small) →
`ai_voice.rag_chunks` (pgvector on PostgreSQL, numpy fallback on SQLite) → vector
search filtered by license tags and `revoked_at`.

**Frontend routes**: `/contribute` (upload + license tags + consent), `/resources` +
`/resources/[id]` (library, audio, transcript editing, ASR/TTS triggers, revoke),
`/review` (approve/reject queue), `/ai-jobs` (live job status).

**Demo accounts** (seeded, password `demo12345`): `contributor@lar.dev`,
`reviewer@lar.dev`, `admin@lar.dev`.

## Mission B — learning layer + dialogue AI

APIs: courses/enroll (coin debit `COURSE_UNLOCK` −price user, +70% community, +30%
platform), lessons (enrollment-gated), practice sessions (deterministic scoring;
`REWARD_PRACTICE` +5 on completion, paid once), certificates with public
verification, `POST /ai/chat` (DeepSeek with RAG context, citations, cultural
disclaimer per §10.4). Frontend: `/learn`, `/practice`, `/chat`, `/certificates`
(+ `/certificates/verify`).

## The two missions connect

Mission B's chat consumes retrieval through `shared/rag_client.py`. Switching
`RAG_MODE=internal` and `RAG_SEARCH_URL=http://localhost:8000/api/v1/rag/search`
routes the chat over Mission A's real pgvector index (with the license/revocation
filters) instead of the local seed fixture.

## Stubs and seams (to be replaced when other missions merge)

| Placeholder | Owner | Replace with |
|---|---|---|
| `app/core/` (register/login/JWT shim, `core.users`) | Developer C | Real core module: users, communities, roles, members |
| `shared/coin_client.py` `StubCoinClient` | Developer C | `HttpCoinClient` → `POST /internal/v1/coins/transfer` (`COIN_MODE=internal`) |
| `ai_voice` stub TTS provider | — | Real Luxembourgish TTS (out of MVP scope by README §10.2) |
| `apps/web` shell + `/login` | Developer C | Shared Next.js shell and auth pages |

## Environment

`services/api/.env` (see `.env.example`): `DATABASE_URL`, `JWT_SECRET`,
`DEEPSEEK_API_KEY`, `ASR_MODE`/`ASR_MODEL_SIZE`, `EMBEDDINGS_MODE`, `TTS_MODE`,
`QUEUE_MODE` (inline/rq/sync), `STORAGE_MODE` (local/s3), `COIN_MODE`, `RAG_MODE`.

Note: a `DEEPSEEK_API_KEY` exported in your shell takes precedence over `.env`
(pydantic-settings precedence).

## Tests / checks

```bash
cd services/api
.venv/Scripts/python -m pytest        # 47 passed
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m mypy app
cd ../../apps/web && npm run build    # type-checked production build
```

The suite runs on in-memory SQLite with `QUEUE_MODE=sync` and mock AI providers —
no external services, keys, or model downloads needed.
