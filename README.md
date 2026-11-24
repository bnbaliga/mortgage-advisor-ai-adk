# Mortgage Advisor VoiceAI

A voice-powered mortgage advisor built on the **Gemini Live API** and **Google ADK**. Talk naturally about mortgage options, rates, and lending products — and interrupt mid-sentence when you have questions.

## Quick Start

```bash
uv sync
cp .env.example .env          # paste your GOOGLE_API_KEY (Gemini Developer API / AI Studio, not Vertex)

uv run uvicorn mortgage.server:app --port 8000     # open http://localhost:8000
```

Open <http://localhost:8000>, tap the microphone and start talking about your mortgage needs.

## Project Structure

| Folder | Description |
|--------|-------------|
| `mortgage/` | Main application — voice agent, tools, policies, and frontend |
| `assets/mortgage/` | Mortgage product data and knowledge base |
| `tests/` | Test suite (200 automated tests) |
| `docs/` | All documentation (requirements, user stories, ADRs, architecture) |
| `deployment/` | Docker and deployment configurations |
| `.github/workflows/` | CI/CD pipelines |

## Documentation

All documentation is available in HTML and DOCX formats in the `docs/` folder.

| Document | Description |
|----------|-------------|
| [docs/01-business-requirements.html](docs/01-business-requirements.html) | Business Requirements Document |
| [docs/02-user-stories.html](docs/02-user-stories.html) | User Stories and Acceptance Criteria |
| [docs/03-demo-guide.html](docs/03-demo-guide.html) | Demo Walkthrough Guide |
| [docs/04-example-conversations.html](docs/04-example-conversations.html) | Example Conversation Transcripts |
| [docs/05-non-functional-requirements.html](docs/05-non-functional-requirements.html) | Non-Functional Requirements (SLOs, SLAs) |
| [docs/adr/](docs/adr/) | Architecture Decision Records (HTML & DOCX) |
| [docs/wiki/](docs/wiki/) | Technical Architecture Documentation |

## Commands

| Command | Description |
|---------|-------------|
| `uv run uvicorn mortgage.server:app --port 8000` | Start the mortgage advisor |
| `uv run pytest` | Run tests with coverage |
| `uv run ruff check mortgage/` | Lint code |
| `uv run ruff format mortgage/` | Format code |
| `uv run mypy mortgage/` | Type check |
| `pre-commit run --all-files` | Run all pre-commit checks |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Comprehensive health check |
| `GET /healthz` | Liveness probe |
| `GET /readyz` | Readiness probe |
| `GET /info` | Application info |
| `GET /metrics` | Metrics for monitoring |
| `WS /ws` | Voice WebSocket |

## Key Features

- **Multi-Agent System**: Three specialized personas (Sam, Mac, Ivy)
- **Policy Door**: Every tool call validated for compliance
- **State Rules**: Texas, California, Florida HELOC regulations enforced
- **Two-Level Verification**: Basic and strong identity checks
- **Payment Authorization**: Three-step flow with explicit consent
- **Fail-Closed Design**: Unknown states route to human

## Notes

- **Voice** uses Gemini Live native voices (`LIVE_VOICE`, default `Aoede`)
- **Barge-in** is client-side for instant response when you interrupt
- Requires a Gemini API key from AI Studio (not Vertex)
