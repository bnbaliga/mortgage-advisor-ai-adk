# Mac — AI Mortgage Advisor (backend + static frontend) for Cloud Run or any container host.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    OTEL_SDK_DISABLED=true \
    GOOGLE_GENAI_USE_VERTEXAI=FALSE \
    MORTGAGE_PROJECT_ROOT=/app

WORKDIR /app

# Dependencies first so code changes don't bust the layer cache.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY migrations/ migrations/
COPY data/ data/
RUN uv sync --frozen --no-dev

RUN mkdir -p /app/data/mortgage-runtime && useradd --create-home --uid 1000 app && chown -R app /app
USER app

# Cloud Run injects PORT (default 8080).
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn mortgage_advisor.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
