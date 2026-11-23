"""Mac — AI Mortgage Advisor: FastAPI entry point.

Browser <-> WebSocket <-> ADK run_live <-> Gemini Live. Serves the frontend
from src/frontend.

Run locally:  uv run uvicorn mortgage_advisor.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from mortgage_advisor.api.routes import router
from mortgage_advisor.core.config import ALLOWED_ORIGINS, FRONTEND_DIR
from mortgage_advisor.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="HomeFirst AI Lending · Mac Mortgage Advisor")
    if ALLOWED_ORIGINS:
        app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                           allow_methods=["GET"], allow_headers=["*"])
    app.include_router(router)
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    return app


app = create_app()
