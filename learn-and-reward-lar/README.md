# Learn-and-Reward-LAR — Mission B (Learning Layer + Dialogue AI)

Implementation of **Developer B's scope** from the repo README (section 7.2 and the
Week-3 milestone): the `learning` + `ai_chat` backend modules and the learner-facing
frontend routes. Built to the platform spec: modular monolith, per-module database
schemas, OpenAPI-first, English UI/API/DB content with Luxembourgish only as
learning content.

```
apps/web/                 Next.js 14 (App Router, TS, Tailwind, TanStack Query)
services/api/             FastAPI modular monolith
  app/modules/learning/   courses, lessons, exercises, enrollments, practice,
                          chat_messages, certificates  (learning schema)
  app/modules/ai_chat/    DeepSeek adapter, RAG-augmented chat engine
  app/core/               PLACEHOLDER auth (Developer C scope) — see below
  app/shared/             config, errors, pagination, coin + RAG adapters
  alembic/versions/       per-module migrations (core placeholder, learning)
  tests/                  pytest suite (33 tests, in-memory SQLite)
infra/docker-compose.yml  PostgreSQL 16 + pgvector, Redis, api, web
docs/contracts/           exported OpenAPI contract (openapi-mission-b.json)
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

Frontend:

```bash
cd apps/web
npm install
npm run dev            # http://localhost:3000
```

Full stack (PostgreSQL + pgvector, Alembic migrations, no auto-create):

```bash
cd infra
cp ../.env.example ../.env    # set DEEPSEEK_API_KEY
docker compose up --build
```

## What Mission B delivers

**APIs** (base `/api/v1`, Bearer JWT, `limit`/`offset` pagination, unified
`{"error": {code, message, details}}` bodies — README section 9):

| Endpoint | Purpose |
|---|---|
| `GET /courses`, `GET /courses/{id}` | Catalog + lesson list/progress |
| `POST /courses/{id}/enroll` | Coin debit (COURSE_UNLOCK: −price user, +70% community, +30% platform), idempotent |
| `GET /lessons/{id}` | Lesson + exercises (enrollment-gated, answers never leak) |
| `POST /practice/sessions`, `GET /practice/sessions/{id}` | Lesson-exercise or free-conversation sessions |
| `POST /practice/sessions/{id}/messages` | Exercise submission (deterministic scoring, AI hint on missed translations) or free-chat message |
| `POST /ai/chat` | RAG-filtered context + DeepSeek reply + citations + cultural disclaimer |
| `POST /certificates/claim`, `GET /certificates`, `GET /certificates/{code}/verify` | Micro-certificates with public verification |

**Dialogue principles** (README section 10.4) are baked into the system prompt:
practice partner only, not a cultural authority, cites reviewed resources as `[n]`,
refuses unauthorised voice cloning, and every response carries the cultural
disclaimer.

**Compliance gate**: RAG chunks carry license tags; the engine drops chunks that are
revoked or not licensed for learning/research before building context (verified in
tests with a revoked seed chunk).

**Coin flows** all go through the `CoinClient` adapter with idempotency keys —
double-entry (REWARD_PRACTICE +5 per completed session; COURSE_UNLOCK splits
70/20/… per README section 11.2).

## Stubs and seams (to be replaced when other missions merge)

| Placeholder | Owner | Replace with |
|---|---|---|
| `app/core/` (register/login/JWT shim, `core.users`) | Developer C | Real core module: users, communities, roles, members |
| `app/shared/coin_client.py` `StubCoinClient` | Developer C | `HttpCoinClient` → `POST /internal/v1/coins/transfer` (`COIN_MODE=internal`) |
| `app/shared/rag_client.py` `StubRagClient` (seed chunks in `rag_seed.json`) | Developer A | `HttpRagClient` → `POST /api/v1/rag/search` (`RAG_MODE=internal`) |
| `apps/web` shell + `/login` | Developer C | Shared Next.js shell and auth pages |

## Environment

`services/api/.env` (see `.env.example`): `DATABASE_URL` (SQLite locally,
`postgresql+psycopg://…` in compose), `JWT_SECRET`, `DEEPSEEK_API_KEY`,
`DEEPSEEK_MODEL`, `COIN_MODE`, `RAG_MODE`, `AUTO_CREATE_TABLES`.

Note: a `DEEPSEEK_API_KEY` exported in your shell takes precedence over `.env`
(pydantic-settings precedence).

## Tests / checks

```bash
cd services/api
.venv/Scripts/python -m pytest        # 33 passed
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m mypy app
cd ../../apps/web && npm run build    # type-checked production build
```

The test suite runs on in-memory SQLite with the DeepSeek adapter replaced by
fakes, so no external services or API keys are needed.
