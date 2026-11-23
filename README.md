# Mac — AI Mortgage Advisor

A real-time, interruptible voice agent for mortgage origination and servicing, built on **Google ADK** and the **Gemini Live API**.

- **Mac** (origination): products, rate estimates, HELOC eligibility with state rules, option comparison, regulation questions with citations, leads, loan officer transfer.
- **Ivy** (servicing): identity verification, balance and payoff, payment history, due-date changes, autopay, payments and payment methods.
- A **policy door** checks every tool call in code: verification levels, lockout, payment authorisation, fail-closed state rules and disclaimers.

## Project layout

```
mortgage-advisor-ai-adk/
├── pyproject.toml            # package + dependencies (uv)
├── uv.lock
├── README.md
├── .python-version
├── .env.example              # copy to .env
├── Dockerfile
├── compose.yaml
├── src/
│   ├── backend/
│   │   └── mortgage_advisor/
│   │       ├── __init__.py
│   │       ├── main.py               # FastAPI app; serves src/frontend
│   │       ├── api/
│   │       │   ├── dependencies.py   # ADK runner, sessions, live config
│   │       │   └── routes.py         # /healthz, /api/*, WebSocket /ws
│   │       ├── core/
│   │       │   ├── config.py         # paths and settings from the environment
│   │       │   ├── logging.py
│   │       │   └── errors.py
│   │       ├── db/
│   │       │   ├── models.py         # dataclasses: origination, call state, servicing
│   │       │   ├── session.py        # SQLite connections + migrations
│   │       │   └── repositories.py   # ServicingDatabase
│   │       ├── services/
│   │       │   ├── origination.py    # MortgageStore: rules, pricing, comparison, officers
│   │       │   ├── events.py         # per-call event bus to the browser
│   │       │   ├── usage.py          # token and cost tracking
│   │       │   └── knowledge/        # regulation ingestion, approval and search
│   │       └── agent/
│   │           ├── agent.py          # ADK root_agent
│   │           ├── tools.py          # Mac's tools
│   │           ├── servicing_tools.py# Ivy's tools
│   │           ├── policy.py         # policy door (before/after every tool)
│   │           ├── persona.py        # picks the active persona's instructions
│   │           ├── personas/         # Mac and Ivy instructions
│   │           ├── graph.py          # persona routing (Mac <-> Ivy)
│   │           └── observer.py       # talking-point suggestions from tool results
│   └── frontend/                     # static web client; config.js sets the backend URL
├── data/mortgage/            # seed data: products, rules, rate sheet, servicing loans
├── migrations/               # SQL schema for the servicing database
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docs/                     # reviews, requirements, diagrams
└── archive/                  # earlier demos this project grew from (DJ, clinic front desk)
```

## Quick start

```bash
uv sync
cp .env.example .env          # set GOOGLE_API_KEY (AI Studio key, not Vertex)
uv run uvicorn mortgage_advisor.main:app --reload --port 8000
```

Open http://localhost:8000 and press **Call Mac**. Headphones help.

Run the agent in the ADK developer UI instead:

```bash
uv run adk web src/backend
```

## Tests

```bash
uv run pytest                 # unit + integration
uv run pytest tests/unit
uv run pytest tests/integration
```

Tests write their databases to a temporary folder, never to `data/`.

## Regulation knowledge

```bash
uv run python -m mortgage_advisor.services.knowledge.ingest          # fetch approved sources
uv run python -m mortgage_advisor.services.knowledge.ingest status
uv run python -m mortgage_advisor.services.knowledge.ingest approve <source_id>
```

Sources are listed in `src/backend/mortgage_advisor/services/knowledge/sources.yaml`. Only approved passages are searchable.

## Container

```bash
docker compose up --build     # http://localhost:8080
```

The image runs `uvicorn mortgage_advisor.main:app` on `$PORT` (8080 by default), as Cloud Run expects. Runtime databases live in a named volume.

## Deploy to Google Cloud (free tier)

Backend on Cloud Run, frontend on Firebase Hosting: see [docs/deploy-gcp.md](docs/deploy-gcp.md).
When the frontend is hosted separately, set `backendUrl` in `src/frontend/config.js` and
`ALLOWED_ORIGINS` on the backend.

## Configuration

All settings come from environment variables; see `.env.example`. Paths for data, frontend, migrations and databases can be overridden with `MORTGAGE_*` variables.

## Data

`data/mortgage/` holds sample seed data for a fictional lender (HomeFirst AI Lending): products, Texas/California/Florida rules, a sample rate sheet, loan officers and demo customers. Rates and market benchmarks are illustrative only.
