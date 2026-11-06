# Melooha: Show Your Work

Melooha answers questions from a person's birth chart, but its mobile app never shows the chart. This project adds a free, interactive birth chart and makes every answer point back to the chart facts it came from. A new user can see the proof, tap it, and decide whether to trust the answer.

- **Live app:** https://melooha-chi.vercel.app (open it on a phone)
- **Backend API:** https://melooha-backend.onrender.com (free tier: the first request after idle can take about a minute, and the app shows a "waking up" screen)
- **Repo:** https://github.com/sachinyadav7/melooha

## The idea in one paragraph

**Who it is for:** new users who get one free question and then meet the paywall, many of them first-time astrology-app users. **The one metric:** the share of users who tap "Add questions" within 24 hours of their first free answer. **Why it should move it:** the answers cite planets and houses the app never shows, so users must take them on faith. A chart computed in code costs no LLM tokens, so trust can be built without giving away more free questions. **How the build tracks it:** half of users (by a fixed formula on their user ID) see the chart and the tappable evidence, the other half see the current flow. `GET /stats/conversion` reports both groups.

## What is in it

- **Birth chart in code.** North Indian style chart (Lahiri sidereal zodiac, whole-sign houses) computed with `pyswisseph`. Tap a planet or house for a plain-language meaning.
- **Question balance.** Each question spends from a ledger. "Add questions" tops it up (no real payment). Every change carries a `request_id`, so a double tap or retry is never charged twice. A failed answer refunds the question.
- **Grounded answers.** The model sees only stored chart facts, each with an ID such as `P_SATURN_H3`, and cites them. Code then checks the finished answer: every cited ID exists, every planet named is cited, and signs and houses match the chart. A failed check gets one rewrite, then a plain message and a refund.
- **Reliable model calls.** Gemini first, Groq as fallback. The user never sees a raw error.
- **Streaming.** Answers stream as server-sent events. Cited facts appear as tappable chips that open a "Why this answer?" sheet with the chart highlighted.
- **Experiment and tracking.** A/B split, an events table, and a conversion endpoint.
- **Mobile-first UI.** Loading, waking-server, validation, empty-balance, failed-answer and offline states are all designed.
- **Stretch areas:** an evaluation harness and cost control (see below).

## Run it locally with one command

You need Docker Desktop.

```bash
cp .env.example .env        # then add your GEMINI_API_KEY and GROQ_API_KEY
docker compose up --build
```

- App: http://localhost:3000
- API and docs: http://localhost:8000/docs

This starts Postgres, the backend and the frontend. Without API keys the app still runs, but answers fail gracefully and the question is refunded.

### Without Docker

```bash
# backend (needs a Postgres connection string in DATABASE_URL, see .env.example)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

`pyswisseph` compiles during install, so on Windows and Linux you need a C compiler (the Docker image installs one).

## Tests and CI

```bash
cd backend && python -m pytest -q     # 99 tests, no network or API keys needed
cd frontend && npm test               # 12 tests
```

GitHub Actions runs both, plus a frontend production build, on every push. The backend tests use fake model providers, so they cover streaming, fallback, refunds, grounding and the experiment without calling a real API.

## Deployment

| Part | Where | Settings |
|---|---|---|
| Frontend | Vercel | `NEXT_PUBLIC_API_URL` = the backend URL |
| Backend | Render | `DATABASE_URL`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `FRONTEND_ORIGIN` (must match the Vercel URL), optional `GEMINI_MODEL` and `GROQ_MODEL` |
| Database | Neon (Postgres) | free tier |

Model names change often. `.env.example` lists the ones this project uses; override them if a provider retires one.

## API overview

| Endpoint | What it does |
|---|---|
| `POST /users`, `GET /users/{id}` | Create or read a user, with balance and experiment group |
| `PUT /users/{id}/chart`, `GET /users/{id}/chart` | Save birth details and compute the chart, or read it |
| `POST /users/{id}/ask` | Spend one question and stream a grounded answer (events: `meta`, `token`, `reset`, `done`, `failed`) |
| `POST /users/{id}/add-questions` | Top up the balance (demo, no payment) |
| `POST /users/{id}/events` | The app reports `chart_viewed`, `evidence_tapped`, `paywall_viewed` |
| `GET /stats/conversion` | Conversion for the chart group and the control group |
| `GET /cities`, `GET /health` | Supported birth cities, health check |

## Evaluation harness and cost control

`backend/evalkit/` scores answer quality on 20 fixed questions across 3 fixed birth charts: code checks (grounded on the first try, no dates, no guarantees, length, prompt-injection resistance, a doctor or advisor mentioned for health and money-risk questions) plus an LLM judge (Groq scoring Gemini's answers) for relevance, clarity, honesty and tone. It also records tokens, cost and time per answer.

```bash
cd backend
python scripts/run_eval.py --variant baseline --label before
python scripts/run_eval.py --variant lean --label after
python scripts/run_eval.py --compare evalkit/results/before.json evalkit/results/after.json
```

The "lean" prompt sends only the chart facts related to the question, shorter rules and a 90-word limit. Results from my run (raw files are in `backend/evalkit/results/`):

| Metric | Baseline | Lean | Change |
|---|---|---|---|
| Average input tokens | 670.6 | 428.8 | -36% |
| Average output tokens | 151.6 | 97.8 | -35% |
| Median answer time | 17.5 s | 13.4 s | -23% |
| Grounded on first try | 95% | 90% | -5 pts |
| Judge relevance (of 5) | 4.80 | 4.10 | -15% |
| Judge tone (of 5) | 4.75 | 4.15 | -13% |

The cheaper prompt lowered relevance and tone scores, so the live app keeps the baseline prompt (`DEFAULT_VARIANT` in `backend/app/prompt.py`). Twenty answers and one judge model is a small sample, so treat small differences as noise. Dollar figures in `pricing.json` use placeholder prices. Token counts are measured.

## Project layout

```
backend/app/        FastAPI app: chart engine, ledger, grounding check, LLM providers, events, stats
backend/evalkit/    evaluation harness and results
backend/tests/      backend tests
frontend/app/       Next.js pages and styles (design tokens in globals.css)
frontend/components/  screens and chart components
frontend/lib/       API client, chart geometry, fact parsing (with tests)
docker-compose.yml  one-command local setup
```

## Known limits

- English only; no login (a user is an id kept in the browser).
- 35 bundled Indian cities, all on Indian time; the exact birth time is required.
- The grounding check catches wrong facts, not wrong interpretations. It also requires at least one cited fact, so an off-topic question or a prompt-injection attempt gets a plain message and a refund instead of a reply.
- The first request after idle is slow on Render's free tier, and answers took about 17 seconds at the median in my evaluation run on the free Gemini tier.

## Reused code and AI tools

I wrote no code for this before the challenge, and nothing here is copied from an earlier project of mine. The problems I built around (no chart in the app, one free question, an interface that is hard for first-time users) came from my own use of Melooha and a competitor app. I used Claude to plan the build, write most of the code and documents, and a coding agent in my editor to run, test and deploy it. I ran, read and tested what they produced, and I can explain each part.
