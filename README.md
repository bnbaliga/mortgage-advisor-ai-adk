# Mortgage Advisor VoiceAI

A voice-powered mortgage advisor built on the **Gemini Live API** and **Google ADK**. Talk naturally about mortgage options, rates, and lending products — and interrupt mid-sentence when you have questions.

## Quick start

```bash
uv sync
cp .env.example .env          # paste your GOOGLE_API_KEY (Gemini Developer API / AI Studio, not Vertex)

uv run uvicorn mortgage.server:app --port 8000     # open http://localhost:8000
```

Open <http://localhost:8000>, tap the microphone and start talking about your mortgage needs.

## Project structure

| Folder | Description |
|---|---|
| `mortgage/` | Main application — voice agent, tools, policies, and frontend |
| `assets/mortgage/` | Mortgage product data and knowledge base |
| `tests/` | Test suite |
| `wiki/` | Requirements documentation |

## Commands

| Command | Description |
|---|---|
| `uv run uvicorn mortgage.server:app --port 8000` | Start the mortgage advisor |
| `uv run pytest` | Run tests |

## Notes

- **Voice** uses Gemini Live native voices (`LIVE_VOICE`, default `Aoede`)
- **Barge-in** is client-side for instant response when you interrupt
- Requires a Gemini API key from AI Studio (not Vertex)
