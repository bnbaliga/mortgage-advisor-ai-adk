"""HTTP and WebSocket routes.

WS /ws contract:
  up:   binary 16 kHz PCM · {"type":"text","text":...}
  down: binary 24 kHz PCM · transcript · interrupted · turn_complete · error
        · action (every policy verdict) · tool_result (what each tool returned)
        · usage (running token totals for this call)
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.agents import LiveRequestQueue
from google.genai import types

from mortgage_advisor.agent import tools
from mortgage_advisor.agent.persona import AGENT_NAME
from mortgage_advisor.api.dependencies import RUN_CONFIG, get_store, runner, session_service
from mortgage_advisor.core.config import ALLOWED_ORIGINS, APP_NAME, GREET_ON_CONNECT, LIVE_MODEL, VOICE
from mortgage_advisor.services import events
from mortgage_advisor.services.usage import Usage, server_totals

log = logging.getLogger("mortgage")

GREETING_CUE = "(The caller's line just connected. Greet them now.)"

router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {"ok": True, "model": LIVE_MODEL, "voice": VOICE}


@router.get("/api/company")
async def company():
    store = get_store()
    return {
        "company": store.info["name"],
        "agent": AGENT_NAME,
        "phone": store.info["phone"],
        "nmls": store.info.get("nmls_id", ""),
        "tagline": store.info.get("tagline", "")
    }


@router.get("/api/products")
async def products():
    return {"products": list(get_store().products.keys())}


@router.get("/api/usage")
async def usage_totals():
    """Tokens used by every finished call since this server started."""
    return server_totals.snapshot()


def _friendly(exc: BaseException) -> str:
    s = f"{type(exc).__name__}: {exc}"
    if "API key" in s or "API_KEY" in s or "401" in s or "403" in s:
        return "The Gemini API key was rejected — check GOOGLE_API_KEY in .env (AI Studio key, not Vertex)."
    if "404" in s and "model" in s.lower():
        return f"The live model '{LIVE_MODEL}' wasn't found — check LIVE_MODEL in .env."
    return s


def origin_allowed(origin: str | None, host: str | None) -> bool:
    """Same-origin pages are always allowed; other sites only if listed in ALLOWED_ORIGINS.
    Browsers can't fake the Origin header, so this stops other websites from opening calls."""
    if not origin:
        return True  # non-browser clients (tests, tools) send no Origin
    origin = origin.rstrip("/")
    if origin.split("://", 1)[-1] == (host or ""):
        return True
    return origin in ALLOWED_ORIGINS


@router.websocket("/ws")
async def ws(websocket: WebSocket):
    if not origin_allowed(websocket.headers.get("origin"), websocket.headers.get("host")):
        log.warning("rejected /ws from origin %s", websocket.headers.get("origin"))
        await websocket.close(code=1008)
        return
    await websocket.accept()
    session = await session_service.create_session(app_name=APP_NAME, user_id="caller")
    call_id = session.id
    feed_q = events.subscribe(call_id)
    queue = LiveRequestQueue()
    usage = Usage()
    log.info("call %s connected (model=%s, voice=%s)", call_id[:8], LIVE_MODEL, VOICE)

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
                    await send({"type": "transcript", "role": "user", "text": text, "final": True, "typed": True})
                    queue.send_content(types.Content(role="user", parts=[types.Part.from_text(text=text)]))

    async def downstream():
        async for event in runner.run_live(user_id=session.user_id, session_id=call_id,
                                           live_request_queue=queue, run_config=RUN_CONFIG):
            for role, attr in (("user", "input_transcription"), ("agent", "output_transcription")):
                t = getattr(event, attr, None)
                if t and getattr(t, "text", None):
                    await send({"type": "transcript", "role": role, "text": t.text,
                                "final": bool(getattr(t, "finished", False))})
            content = getattr(event, "content", None)
            for part in (getattr(content, "parts", None) or []):
                idata = getattr(part, "inline_data", None)
                if idata and getattr(idata, "data", None) and (idata.mime_type or "").startswith("audio"):
                    await websocket.send_bytes(idata.data)
            if getattr(event, "interrupted", None):
                await send({"type": "interrupted"})
            if getattr(event, "turn_complete", None):
                await send({"type": "turn_complete"})
            um = getattr(event, "usage_metadata", None)
            if um:
                usage.add(um)
                await send({"type": "usage", **usage.snapshot()})

    async def feed():
        while True:
            await send(await feed_q.get())

    if GREET_ON_CONNECT:
        queue.send_content(types.Content(role="user", parts=[types.Part.from_text(text=GREETING_CUE)]))

    up = asyncio.create_task(upstream(), name="upstream")
    down = asyncio.create_task(downstream(), name="downstream")
    fd = asyncio.create_task(feed(), name="feed")
    try:
        done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
        queue.close()
        for t in done:
            exc = t.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                log.error("call %s: %s failed: %r", call_id[:8], t.get_name(), exc)
                try:
                    await send({"type": "error", "message": _friendly(exc)})
                except Exception:
                    pass
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    finally:
        fd.cancel()
        await asyncio.gather(fd, return_exceptions=True)
        queue.close()
        events.unsubscribe(call_id)
        tools.store.end_call(call_id)
        server_totals.add_call(usage)
        cost = usage.cost_usd()
        log.info("call %s ended — tokens: %d total (%d in / %d out) over %d turns%s; by modality %s",
                 call_id[:8], usage.total, usage.input, usage.output, usage.reports,
                 f", est. ${cost:.4f}" if cost is not None else "", usage.by)
