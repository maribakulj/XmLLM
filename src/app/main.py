"""XmLLM — Document Structure Engine.

FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    settings: Settings = get_settings()
    settings.ensure_directories()
    yield


app = FastAPI(
    title="XmLLM",
    description="Document structure engine: image → canonical model → ALTO XML / PAGE XML",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Health route (always available) ------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": "0.1.0",
        "mode": settings.app_mode.value,
    }
