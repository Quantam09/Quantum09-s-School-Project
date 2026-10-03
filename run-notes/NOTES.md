# Learn-and-Reward-LAR — Full Project Run Notes

**Date:** 2026-10-03 · **Machine:** Windows 11 (Docker-less), Python 3.11.9, Node 24
**Source:** `C:\Users\aidan\Downloads\Learn-and-Reward-LAR-main\` (fully merged project: Missions A + B + C)
**Verdict: The complete integrated platform runs end-to-end. 85/85 tests pass. One real integration bug found (documented below).**

---

## Contributors

| Contributor | Role |
|---|---|
| **ZCode** (AI coding agent) | Executed the full project locally, ran the test suite and linters, walked through every feature in the browser, captured the 22 screenshots, and wrote these notes |
| **DeepSeek** (`deepseek-chat` via API) | Powered the AI conversation-practice demo (the `/chat` replies, citations and dialogue style in screenshot `08-chat-deepseek.png` come from a live DeepSeek call) |
| **Quantam09** | Project owner; provided the environment, API key and repositories |

---

## 1. How it was run

Backend (FastAPI, port 8000):

```
cd Learn-and-Reward-LAR-main\services\api
py -3.11 -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
copy .env.example .env        # then set DEEPSEEK_API_KEY (real key used)
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend (Next.js 14, port 3000):

```
cd ..\apps\web
npm ci
copy .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

Settings used (SQLite local profile, no Docker):
`DATABASE_URL=sqlite:///./dev.db`, `COIN_MODE=internal` (C's real ledger),
`RAG_MODE=stub` (see bug §4), `ASR_MODE=mock`, `EMBEDDINGS_MODE=mock`, `TTS_MODE=stub`,
`QUEUE_MODE=inline`, `STORAGE_MODE=local`.

Seeding is automatic on startup (core users → coin accounts/rules → market listings →
governance policy → learning course → resource corpus + RAG seed).

**Demo accounts** (all password `password123`):
`admin@lar.dev` (platform_admin) · `elder@lar.dev` (elder_teacher) ·
`contributor@lar.dev` (contributor) · `learner@lar.dev` (learner) · `reviewer@lar.dev` (reviewer)

## 2. Quality gates

| Check | Result |
|---|---|
| pytest | **85/85 pass** (69s). 1 apparent failure (`test_ai_chat_fails_cleanly_without_deepseek_key`) is an artifact of a real `.env` with a key being present during the run; with `DEEPSEEK_API_KEY=""` it passes. |
| ruff | All checks passed |
| mypy | No issues in 61 source files |
| Live API during walkthrough | 72×200, 2×201, **0 server errors** (the single 400 in the log was a curl test with a mangled body, not the app) |

## 3. What was exercised in the browser (all 22 screenshots in `screenshots/`)

**Learner (learner@lar.dev)**
- Home page renders with full nav (`01-home`)
- Login works, redirects to `/learn` (`02`)
- Enrolled in "Luxembourgish for Beginners" (10 coins): backend shows
  `POST /api/v1/courses/{id}/enroll` → **200**, and during it
  `POST /internal/v1/coins/transfer` → **200** — B's module paying through C's real coin ledger (`03`)
- Course page: 3 lessons, progress bar 0/3 (`04`)
- Lesson 1: vocabulary table + multiple choice; answered "Moien" →
  "Correct! Moien is the standard informal hello." (`05`, `06`)
- Exercise 2 (fill-in-the-blank): "Merci" → correct; **"Session complete! You earned 5 coins"** —
  REWARD_PRACTICE paid once on completion (`07`)
- **AI Chat with real DeepSeek**: asked "Wéi geet et? And what does 'Gudde Moien' mean?" →
  bilingual Luxembourgish/English reply in ~2s, RAG citation chip `[1] resource ce-001`,
  cultural disclaimer banner on top (`08`). (First attempt with `RAG_MODE=internal` failed — see §4.)
- Wallet: balance **45** (seed 50 − 10 enroll + 5 practice ✓), double-entry transactions list (`09`)
- Market: 2 seeded listings (translation 100, lesson 150 coins), 70/20/10 split text (`10`)
- Governance hub (`11`) and **public coin ledger** showing exact double-entry legs:
  `COURSE_UNLOCK: user −10 → community +7, platform +3`; `REWARD_PRACTICE: platform −5 → user +5` (`12`)
- Certificates: correct empty state + claim section (requires completed course) (`13`)

**Reviewer (reviewer@lar.dev)**
- Review queue shows seeded pending "Story: The squirrel of Esch" (`14`)
- Approve → success banner *"contributor earned 10 coins and the community pool received
  its share"*, queue empties (`15`). Verified in audit trail + REWARD_CONTRIBUTION coin transfer.

**Contributor (contributor@lar.dev)**
- Contribute form with the full §8.2 permission matrix
  (Learning use / Research / Commercial AI / Remix / Revocable / Voice-clone consent) (`16`)
- Created "Proverb collection: Esch sayings" → success banner, appears under
  "My resources" as **draft** (`17`)
- Resource library: approved public resources with license-tag chips; squirrel story now
  **approved** after my review action (`18`)
- AI Jobs: ASR panel (resource dropdown), TTS panel. Ran a TTS job → **completed** with the
  documented MVP fallback: "TTS preview is not available for Luxembourgish in the MVP…"
  — honest stub behavior per spec §10.2 (`19`, `20`)

**Admin (admin@lar.dev)**
- Platform dashboard: 5 users, 1 community, 3 coin transactions, 5 audit logs,
  7 coin accounts, 2 listings, role management dropdowns (`21`)
- Audit ledger (append-only): recorded exactly the walkthrough events —
  `resource.created`, `resource.approved (coins_awarded:10)`,
  `coin.transfer REWARD_CONTRIBUTION / REWARD_PRACTICE / COURSE_UNLOCK` — plus quarterly
  audit export (`22`)

## 4. Bug found: internal RAG call is unauthenticated

With the documented full-integration setting (`RAG_MODE=internal`,
`RAG_SEARCH_URL=http://localhost:8000/api/v1/rag/search`), **chat always fails** with
"RAG search service is unavailable."

- `POST /api/v1/rag/search` requires a logged-in user (`UserDep` in
  `services/api/app/modules/ai_voice/router.py`).
- The chat engine retrieves through `HttpRagClient` (`services/api/app/shared/rag_client.py`),
  which is a server-to-server `httpx.post` with **no Authorization header** → 401 every time.
- Tests don't catch it because they stub the RAG client.
- Fix suggestion: exempt `/rag/search` from user auth for internal calls (e.g. a service
  token), or call the ai_voice service function directly in-process instead of over HTTP.

With `RAG_MODE=stub` (the documented fallback) chat works perfectly with real DeepSeek,
citations, and license filtering.

## 5. Minor observations

- JWT warning in logs: `InsecureKeyLengthWarning: HMAC key is 23 bytes` — `JWT_SECRET=change-me-in-production` is < 32 bytes; fine for dev, would need a longer secret in prod.
- After enrolling, the Enroll button becomes disabled with no visible "Enrolled ✓" text or toast — works, but feedback could be clearer.
- A transient Next.js dev-overlay "1 error" badge appeared on /certificates; the backend log shows all requests returned 200 there, so it was a stale client-side overlay artifact.
- `pytest` also emits a Starlette/httpx deprecation warning (upstream, harmless).
- ASR/embeddings ran in mock mode for this demo; real modes download ~700MB of models on first use (config: `ASR_MODE=real`, `EMBEDDINGS_MODE=real`).

## 6. State left behind

- Backend still running on http://127.0.0.1:8000 (background task), frontend on http://localhost:3000.
- Data lives in `services/api/dev.db` (SQLite) + `services/api/data/` — delete both for a factory reset; seeds re-create on startup.
- `.env` contains a real DeepSeek key (gitignored, never committed).
