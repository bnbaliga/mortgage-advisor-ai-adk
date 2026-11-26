# Mortgage advisor voice agent (mortgage.server) for Cloud Run.
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

# OTEL_SDK_DISABLED defaults to true in code if not set
# Set OTEL_SDK_DISABLED=false and LANGFUSE_* vars at deploy time to enable observability
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    GOOGLE_GENAI_USE_VERTEXAI=FALSE

WORKDIR /app

# Dependencies first so code changes don't bust the layer cache.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY mortgage/ mortgage/
COPY assets/mortgage/ assets/mortgage/

RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

# Cloud Run injects PORT (default 8080).
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn mortgage.server:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
