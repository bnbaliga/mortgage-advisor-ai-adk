"""The mortgage advisor backend: browser <-> ADK run_live <-> Gemini Live.

Same loop as the front desk: LiveRequestQueue up, runner.run_live() down,
and the UI fed from the policy door.

WS /ws contract:
  up:   binary 16 kHz PCM · {"type":"text","text":...}
  down: binary 24 kHz PCM · transcript · interrupted · turn_complete · error
        · action (every policy verdict) · tool_result (what each tool returned)
        · usage (running token totals for this call)
"""

import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import RunConfig, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mortgage import events, tools
from mortgage.agent import LIVE_MODEL, VOICE, root_agent
from mortgage.persona import AGENT_NAME
from mortgage.usage import COMPRESSION_TRIGGER, Usage, server_totals
from mortgage.observability import init_langfuse, trace_session, get_langfuse, record_usage, finalize_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Initialize Langfuse observability (if configured)
init_langfuse()
log = logging.getLogger("mortgage")

# Application metadata
APP_NAME = "mortgage-advisor"
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
BUILD_SHA = os.getenv("BUILD_SHA", "local")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
START_TIME = time.time()
START_TIMESTAMP = datetime.now(UTC).isoformat()

GREET = os.getenv("MORTGAGE_GREETING", "1") != "0"
GREETING_CUE = "(The caller's line just connected. Greet them now.)"

# Metrics tracking
_metrics = {
    "calls_total": 0,
    "calls_active": 0,
    "calls_completed": 0,
    "calls_errored": 0,
    "tokens_total": 0,
}

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)

RUN_CONFIG = RunConfig(
    streaming_mode=StreamingMode.BIDI,
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)
        )
    ),
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=COMPRESSION_TRIGGER, sliding_window=types.SlidingWindow(target_tokens=60_000)
    ),
)

app = FastAPI(title="HomeFirst AI Lending · Mac Mortgage Advisor")
FRONTEND = Path(__file__).resolve().parent / "frontend"


# =============================================================================
# Health & Observability Endpoints
# =============================================================================


@app.get("/health")
async def health():
    """Comprehensive health check for load balancers and monitoring."""
    uptime_seconds = time.time() - START_TIME
    checks = {
        "api": "healthy",
        "store": "healthy" if tools.store else "unhealthy",
        "agent": "healthy" if root_agent else "unhealthy",
    }
    all_healthy = all(v == "healthy" for v in checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "uptime_seconds": round(uptime_seconds, 2),
        "version": APP_VERSION,
    }


@app.get("/healthz")
async def healthz():
    """Simple liveness probe for Kubernetes/Cloud Run."""
    return {"ok": True, "model": LIVE_MODEL, "voice": VOICE}


@app.get("/readyz")
async def readyz():
    """Readiness probe - is the service ready to accept traffic?"""
    # Check if critical dependencies are available
    store_ready = tools.store is not None
    if store_ready:
        return {"ready": True}
    return {"ready": False, "reason": "store not initialized"}, 503


@app.get("/info")
async def info():
    """Application information for debugging and monitoring."""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "build_sha": BUILD_SHA,
        "environment": ENVIRONMENT,
        "model": LIVE_MODEL,
        "voice": VOICE,
        "started_at": START_TIMESTAMP,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "python_version": os.popen("python --version 2>&1").read().strip(),
    }


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics for monitoring dashboards."""
    uptime = time.time() - START_TIME
    usage = server_totals.snapshot()
    return {
        "uptime_seconds": round(uptime, 2),
        "calls": {
            "total": _metrics["calls_total"],
            "active": _metrics["calls_active"],
            "completed": _metrics["calls_completed"],
            "errored": _metrics["calls_errored"],
        },
        "tokens": {
            "total": usage.get("total", 0),
            "input": usage.get("input", 0),
            "output": usage.get("output", 0),
        },
        "cost_usd": usage.get("cost_usd", 0),
    }


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/api/company")
async def company():
    return {
        "company": tools.store.info["name"],
        "agent": AGENT_NAME,
        "phone": tools.store.info["phone"],
        "nmls": tools.store.info.get("nmls_id", ""),
        "tagline": tools.store.info.get("tagline", ""),
    }


@app.get("/api/products")
async def products():
    return {"products": list(tools.store.products.keys())}


@app.get("/api/usage")
async def usage_totals():
    """Tokens used by every finished call since this server started."""
    return server_totals.snapshot()


def _friendly(exc: BaseException) -> tuple[str, str]:
    """Return (friendly_message, technical_details) for an exception."""
    full_error = f"{type(exc).__name__}: {exc}"

    # Import traceback for detailed error info
    import traceback
    stack_trace = traceback.format_exc()

    if "API key" in full_error or "API_KEY" in full_error or "401" in full_error or "403" in full_error:
        return (
            "The Gemini API key was rejected — check GOOGLE_API_KEY in .env (AI Studio key, not Vertex).",
            stack_trace
        )
    if "404" in full_error and "model" in full_error.lower():
        return (
            f"The live model '{LIVE_MODEL}' wasn't found — check LIVE_MODEL in .env.",
            stack_trace
        )
    if "KeyError" in full_error:
        return (
            "An internal error occurred while processing your request. Our team has been notified.",
            f"Missing key in data structure:\n{full_error}\n\n{stack_trace}"
        )

    return (
        "An unexpected error occurred during the call.",
        f"{full_error}\n\n{stack_trace}"
    )


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    session = await session_service.create_session(app_name=APP_NAME, user_id="caller")
    call_id = session.id
    feed_q = events.subscribe(call_id)
    queue = LiveRequestQueue()
    usage = Usage()
    call_errored = False

    # Track metrics
    _metrics["calls_total"] += 1
    _metrics["calls_active"] += 1
    log.info("call %s connected (model=%s, voice=%s)", call_id[:8], LIVE_MODEL, VOICE)

    # Create Langfuse trace for this session
    lf_trace = trace_session(
        session_id=call_id,
        metadata={"model": LIVE_MODEL, "voice": VOICE, "environment": ENVIRONMENT}
    )

    async def send(obj: dict):
        await websocket.send_text(json.dumps(obj, default=str))

    async def upstream():
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                return
            if msg.get("bytes"):
                queue.send_realtime(types.Blob(data=msg["bytes"], mime_type="audio/pcm;rate=16000"))
            elif msg.get("text"):
                try:
                    m = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                if m.get("type") == "text" and str(m.get("text", "")).strip():
                    text = str(m["text"]).strip()[:1000]
                    await send(
                        {
                            "type": "transcript",
                            "role": "user",
                            "text": text,
                            "final": True,
                            "typed": True,
                        }
                    )
                    queue.send_content(
                        types.Content(role="user", parts=[types.Part.from_text(text=text)])
                    )

    async def downstream():
        async for event in runner.run_live(
            user_id=session.user_id,
            session_id=call_id,
            live_request_queue=queue,
            run_config=RUN_CONFIG,
        ):
            for role, attr in (("user", "input_transcription"), ("agent", "output_transcription")):
                t = getattr(event, attr, None)
                if t and getattr(t, "text", None):
                    await send(
                        {
                            "type": "transcript",
                            "role": role,
                            "text": t.text,
                            "final": bool(getattr(t, "finished", False)),
                        }
                    )
            content = getattr(event, "content", None)
            for part in getattr(content, "parts", None) or []:
                idata = getattr(part, "inline_data", None)
                if (
                    idata
                    and getattr(idata, "data", None)
                    and (idata.mime_type or "").startswith("audio")
                ):
                    await websocket.send_bytes(idata.data)
            if getattr(event, "interrupted", None):
                await send({"type": "interrupted"})
            if getattr(event, "turn_complete", None):
                await send({"type": "turn_complete"})
            um = getattr(event, "usage_metadata", None)
            if um:
                usage.add(um)
                await send({"type": "usage", **usage.snapshot()})
                # Record usage to Langfuse on each turn
                if lf_trace:
                    record_usage(
                        trace=lf_trace,
                        model=LIVE_MODEL,
                        input_tokens=usage.input,
                        output_tokens=usage.output,
                        turn_number=usage.reports,
                        cost_usd=usage.cost_usd(),
                        by_modality=usage.by,
                    )

    async def feed():
        while True:
            await send(await feed_q.get())

    if GREET:
        queue.send_content(
            types.Content(role="user", parts=[types.Part.from_text(text=GREETING_CUE)])
        )

    up = asyncio.create_task(upstream(), name="upstream")
    down = asyncio.create_task(downstream(), name="downstream")
    fd = asyncio.create_task(feed(), name="feed")
    try:
        done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
        queue.close()
        for t in done:
            exc = t.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                call_errored = True
                log.error("call %s: %s failed: %r", call_id[:8], t.get_name(), exc)
                try:
                    friendly_msg, details = _friendly(exc)
                    await send({"type": "error", "message": friendly_msg, "details": details})
                except Exception:
                    pass
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    finally:
        # Update metrics
        _metrics["calls_active"] -= 1
        if call_errored:
            _metrics["calls_errored"] += 1
        else:
            _metrics["calls_completed"] += 1

        fd.cancel()
        await asyncio.gather(fd, return_exceptions=True)
        queue.close()
        events.unsubscribe(call_id)
        tools.store.end_call(call_id)
        server_totals.add_call(usage)
        cost = usage.cost_usd()
        log.info(
            "call %s ended — tokens: %d total (%d in / %d out) over %d turns%s; by modality %s",
            call_id[:8],
            usage.total,
            usage.input,
            usage.output,
            usage.reports,
            f", est. ${cost:.4f}" if cost is not None else "",
            usage.by,
        )

        # Finalize Langfuse trace with usage data and scores
        if lf_trace:
            try:
                finalize_session(
                    trace=lf_trace,
                    model=LIVE_MODEL,
                    total_tokens=usage.total,
                    input_tokens=usage.input,
                    output_tokens=usage.output,
                    cost_usd=cost,
                    turns=usage.reports,
                    errored=call_errored,
                    by_modality=usage.by,
                )
                # Flush is handled by atexit, but we can force it
                langfuse = get_langfuse()
                if langfuse:
                    langfuse.flush()
            except Exception as e:
                log.debug("Failed to finalize Langfuse trace: %s", e)


if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
