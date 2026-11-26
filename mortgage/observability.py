"""Langfuse observability for LLM tracing.

Provides session-level tracing for all agent interactions, tool calls,
and LLM requests. Dashboard available at Langfuse Cloud or self-hosted.

Setup:
    1. Create account at https://cloud.langfuse.com (free tier available)
    2. Create a new project and get your API keys
    3. Set environment variables in .env:
       LANGFUSE_PUBLIC_KEY=pk-lf-...
       LANGFUSE_SECRET_KEY=sk-lf-...
       OTEL_SDK_DISABLED=false

    OR self-host:
    1. docker-compose -f deployment/docker-compose.langfuse.yml up -d
    2. Access http://localhost:3000, create account
    3. Set LANGFUSE_HOST=http://localhost:3000

Usage:
    # At server startup (already integrated in server.py)
    from mortgage.observability import init_langfuse
    init_langfuse()

    # Traces are automatically captured for:
    # - All tool calls (via ADK's OpenTelemetry)
    # - LLM requests and responses
    # - Token usage and costs
"""

import os
import logging
import atexit
from typing import Optional
from functools import wraps

log = logging.getLogger(__name__)

# Langfuse client singleton
_langfuse_client = None
_otel_configured = False


def _setup_otel_export(public_key: str, secret_key: str, host: str) -> bool:
    """Configure OpenTelemetry to export traces to Langfuse.

    This captures ADK's native OpenTelemetry traces and sends them to Langfuse.
    """
    global _otel_configured

    if _otel_configured:
        log.debug("OpenTelemetry already configured, skipping")
        return True

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        import base64

        # Check if a tracer provider is already set
        current_provider = trace.get_tracer_provider()
        if current_provider and not isinstance(current_provider, trace.ProxyTracerProvider):
            log.debug("TracerProvider already configured by another component")
            _otel_configured = True
            return True

        # Langfuse OTLP endpoint
        otel_endpoint = f"{host}/api/public/otel/v1/traces"

        # Auth header: Basic base64(public_key:secret_key)
        auth_string = f"{public_key}:{secret_key}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()

        # Create resource
        resource = Resource(attributes={
            SERVICE_NAME: "homefirst-ai-mortgage-advisor"
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter with Langfuse auth
        exporter = OTLPSpanExporter(
            endpoint=otel_endpoint,
            headers={
                "Authorization": f"Basic {auth_bytes}",
            },
        )

        # Add batch processor
        provider.add_span_processor(BatchSpanProcessor(exporter))

        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        _otel_configured = True

        log.info("OpenTelemetry configured to export to Langfuse: %s", otel_endpoint)
        return True

    except ImportError as e:
        log.warning("OpenTelemetry packages not available: %s", e)
        return False
    except Exception as e:
        log.warning("Failed to configure OpenTelemetry export: %s", e)
        return False


def init_langfuse() -> bool:
    """Initialize Langfuse observability.

    Call this once at server startup. Returns True if successfully configured.

    Environment Variables:
        LANGFUSE_PUBLIC_KEY: Your Langfuse public key (required)
        LANGFUSE_SECRET_KEY: Your Langfuse secret key (required)
        LANGFUSE_HOST: Langfuse host (default: https://cloud.langfuse.com)
        OTEL_SDK_DISABLED: Must be 'false' to enable tracing
    """
    global _langfuse_client

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    # Support both LANGFUSE_HOST and LANGFUSE_BASE_URL
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    # Check if tracing is disabled
    if os.getenv("OTEL_SDK_DISABLED", "true").lower() == "true":
        log.info("Langfuse disabled (OTEL_SDK_DISABLED=true)")
        return False

    if not public_key or not secret_key:
        log.info(
            "Langfuse not configured. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
            "to enable observability. Get keys at https://cloud.langfuse.com"
        )
        return False

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

        # Verify connection with auth check
        try:
            _langfuse_client.auth_check()
            log.info("Langfuse auth verified successfully")
        except Exception as auth_err:
            log.warning("Langfuse auth check failed: %s", auth_err)

        # Also configure OpenTelemetry to export to Langfuse
        # This captures ADK's native OTel traces
        _setup_otel_export(public_key, secret_key, host)

        # Flush traces on shutdown
        atexit.register(shutdown_langfuse)

        log.info("Langfuse observability enabled: %s", host)
        return True

    except ImportError:
        log.warning("langfuse package not installed. Run: uv add langfuse")
        return False
    except Exception as e:
        log.error("Failed to initialize Langfuse: %s", e)
        return False


def shutdown_langfuse():
    """Flush and shutdown Langfuse client."""
    global _langfuse_client
    if _langfuse_client:
        try:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
            log.info("Langfuse traces flushed and shutdown")
        except Exception as e:
            log.warning("Error shutting down Langfuse: %s", e)


def get_langfuse():
    """Get the Langfuse client singleton."""
    return _langfuse_client


def _to_langfuse_trace_id(session_id: str) -> str:
    """Convert a session ID to a valid Langfuse trace_id.

    Langfuse requires trace_id to be 32 lowercase hex characters.
    """
    import hashlib
    # Hash the session_id to get a consistent 32-char hex string
    return hashlib.md5(session_id.encode()).hexdigest()


class SessionTrace:
    """Wrapper for Langfuse v4 trace context."""

    def __init__(self, session_id: str, trace_id: str, metadata: Optional[dict] = None):
        self.session_id = session_id  # Original session ID
        self.trace_id = trace_id  # Langfuse-compatible trace ID
        self.metadata = metadata or {}
        self._observations = []

    def get_trace_context(self) -> dict:
        """Get TraceContext dict for Langfuse v4 API."""
        return {"trace_id": self.trace_id}

    def update(self, metadata: Optional[dict] = None):
        """Update trace metadata by adding a summary event."""
        if metadata:
            self.metadata.update(metadata)
        if _langfuse_client and metadata:
            try:
                # Record final session summary as an event
                _langfuse_client.create_event(
                    trace_context=self.get_trace_context(),
                    name="session_summary",
                    metadata=metadata,
                )
            except Exception as e:
                log.debug("Failed to record trace summary: %s", e)


def trace_session(session_id: str, user_id: Optional[str] = None, metadata: Optional[dict] = None):
    """Create a trace for a voice session.

    Args:
        session_id: Unique session/call identifier
        user_id: Optional user identifier (e.g., verified_customer_id)
        metadata: Optional metadata dict

    Returns:
        SessionTrace wrapper, or None if not configured
    """
    if not _langfuse_client:
        return None

    try:
        # Convert session_id to valid Langfuse trace_id format
        trace_id = _to_langfuse_trace_id(session_id)

        # Create the trace wrapper
        trace = SessionTrace(session_id=session_id, trace_id=trace_id, metadata=metadata)

        # In Langfuse v4, we create an event to start the trace
        full_metadata = metadata.copy() if metadata else {}
        full_metadata["session_id"] = session_id  # Store original ID
        if user_id:
            full_metadata["user_id"] = user_id
        full_metadata["tags"] = ["mortgage-advisor", "voice"]

        _langfuse_client.create_event(
            trace_context=trace.get_trace_context(),
            name="voice_session_start",
            metadata=full_metadata,
        )
        log.debug("Created Langfuse trace: %s -> %s", session_id[:8], trace_id[:8])
        return trace
    except Exception as e:
        log.warning("Failed to create Langfuse trace: %s", e)
        return None


def trace_tool_call(
    trace: Optional[SessionTrace],
    tool_name: str,
    input_args: dict,
    output: dict,
    duration_ms: Optional[float] = None,
    status: str = "ok",
):
    """Record a tool call in the trace.

    Args:
        trace: SessionTrace from trace_session()
        tool_name: Name of the tool called
        input_args: Tool input arguments (will be sanitized)
        output: Tool output
        duration_ms: Execution duration in milliseconds
        status: "ok", "blocked", or "error"
    """
    if not trace or not _langfuse_client:
        return

    try:
        # Sanitize PII from inputs
        safe_input = _redact_pii(input_args)

        _langfuse_client.start_observation(
            trace_context=trace.get_trace_context(),
            name=tool_name,
            as_type="tool",
            input=safe_input,
            output=output,
            metadata={
                "status": status,
                "duration_ms": duration_ms,
            },
        ).end()
    except Exception as e:
        log.warning("Failed to record tool call: %s", e)


def trace_generation(
    trace: Optional[SessionTrace],
    model: str,
    input_text: str,
    output_text: str,
    usage: Optional[dict] = None,
    duration_ms: Optional[float] = None,
):
    """Record an LLM generation in the trace.

    Args:
        trace: SessionTrace object
        model: Model name (e.g., "gemini-2.0-flash")
        input_text: Prompt/input text
        output_text: Generated response
        usage: Token usage dict with input/output counts
        duration_ms: Generation duration
    """
    if not trace or not _langfuse_client:
        return

    try:
        _langfuse_client.start_observation(
            trace_context=trace.get_trace_context(),
            name="llm_generation",
            as_type="generation",
            model=model,
            input=input_text[:1000],  # Truncate for dashboard
            output=output_text[:1000],
            usage_details=usage,
            metadata={"duration_ms": duration_ms},
        ).end()
    except Exception as e:
        log.warning("Failed to record generation: %s", e)


def record_usage(
    trace: Optional[SessionTrace],
    model: str,
    input_tokens: int,
    output_tokens: int,
    turn_number: int = 1,
    cost_usd: Optional[float] = None,
    by_modality: Optional[dict] = None,
):
    """Record token usage as a generation observation.

    This creates a generation observation that Langfuse can use to calculate
    costs and display in the Model Usage dashboard.

    Args:
        trace: SessionTrace object
        model: Model name (e.g., "gemini-2.0-flash-live-001")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        turn_number: Turn number for naming
        cost_usd: Pre-calculated cost in USD
        by_modality: Token breakdown by modality (audio, text)
    """
    if not trace or not _langfuse_client:
        return

    try:
        # Langfuse expects usage in this format for cost calculation
        usage_data = {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
            "unit": "TOKENS",
        }

        metadata = {"turn": turn_number}
        if by_modality:
            metadata["by_modality"] = by_modality
        if cost_usd is not None:
            metadata["cost_usd_calculated"] = cost_usd

        # Create generation observation with usage data
        _langfuse_client.generation(
            trace_id=trace.trace_id,
            name=f"turn_{turn_number}",
            model=model,
            usage=usage_data,
            metadata=metadata,
        )
        log.debug("Recorded usage for turn %d: %d in / %d out", turn_number, input_tokens, output_tokens)
    except Exception as e:
        log.warning("Failed to record usage: %s", e)


def score_session(trace: Optional[SessionTrace], name: str, value: float, comment: Optional[str] = None):
    """Add a score to the session (e.g., user satisfaction, task completion).

    Args:
        trace: SessionTrace object
        name: Score name (e.g., "call_completion", "verification_success")
        value: Score value (0.0 to 1.0)
        comment: Optional comment
    """
    if not trace or not _langfuse_client:
        return

    try:
        # Use Langfuse's proper score API
        _langfuse_client.score(
            trace_id=trace.trace_id,
            name=name,
            value=value,
            comment=comment,
        )
        log.debug("Recorded score %s: %.2f", name, value)
    except Exception as e:
        log.warning("Failed to add score: %s", e)


def finalize_session(
    trace: Optional[SessionTrace],
    model: str,
    total_tokens: int,
    input_tokens: int,
    output_tokens: int,
    cost_usd: Optional[float] = None,
    turns: int = 0,
    errored: bool = False,
    by_modality: Optional[dict] = None,
):
    """Finalize a session trace with summary metrics and scores.

    Call this when the call ends to record final statistics.

    Args:
        trace: SessionTrace object
        model: Model name used
        total_tokens: Total tokens consumed
        input_tokens: Input tokens consumed
        output_tokens: Output tokens consumed
        cost_usd: Total estimated cost
        turns: Number of conversation turns
        errored: Whether the call ended in error
        by_modality: Token breakdown by modality
    """
    if not trace or not _langfuse_client:
        return

    try:
        # Record final generation with cumulative usage
        usage_data = {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens,
            "unit": "TOKENS",
        }

        metadata = {
            "turns": turns,
            "errored": errored,
            "session_id": trace.session_id,
        }
        if by_modality:
            metadata["by_modality"] = by_modality
        if cost_usd is not None:
            metadata["cost_usd"] = cost_usd

        # Create a final summary generation observation
        _langfuse_client.generation(
            trace_id=trace.trace_id,
            name="session_summary",
            model=model,
            usage=usage_data,
            metadata=metadata,
        )

        # Add scores based on call outcome
        # Score: call_completion (1.0 = completed normally, 0.0 = errored)
        score_session(
            trace,
            name="call_completion",
            value=0.0 if errored else 1.0,
            comment="Call ended with error" if errored else "Call completed normally",
        )

        # Score: conversation_depth based on number of turns
        # More turns indicate a more engaged conversation
        depth_score = min(1.0, turns / 10.0)  # Cap at 10 turns = 1.0
        score_session(
            trace,
            name="conversation_depth",
            value=depth_score,
            comment=f"{turns} conversation turns",
        )

        log.debug(
            "Finalized session trace: %d tokens, %d turns, cost $%.4f",
            total_tokens, turns, cost_usd or 0
        )
    except Exception as e:
        log.warning("Failed to finalize session: %s", e)


# PII fields to redact
_SENSITIVE_FIELDS = {
    "full_name", "name", "phone", "phone_last_4", "email",
    "ssn", "dob", "date_of_birth", "account_number", "card_number",
}


def _redact_pii(data: dict) -> dict:
    """Redact sensitive fields from a dictionary."""
    if not isinstance(data, dict):
        return data

    return {
        k: "***REDACTED***" if k.lower() in _SENSITIVE_FIELDS else v
        for k, v in data.items()
    }


# Decorator for tracing async functions
def observe(name: Optional[str] = None):
    """Decorator to trace a function call with Langfuse.

    Usage:
        @observe("check_eligibility")
        async def check_heloc_eligibility(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not _langfuse_client:
                return await func(*args, **kwargs)

            span_name = name or func.__name__

            try:
                from langfuse.decorators import observe as lf_observe
                decorated = lf_observe(name=span_name)(func)
                return await decorated(*args, **kwargs)
            except Exception:
                # Fallback if decorator fails
                return await func(*args, **kwargs)

        return wrapper
    return decorator
