"""XmLLM — Document Structure Engine.

FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.app.api import init_services, shutdown_services
from src.app.api.routes_exports import router as exports_router
from src.app.api.routes_health import router as health_router
from src.app.api.routes_jobs import router as jobs_router
from src.app.api.routes_providers import router as providers_router
from src.app.api.routes_viewer import router as viewer_router
from src.app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    settings = get_settings()
    settings.ensure_directories()
    init_services(settings)
    yield
    shutdown_services()


app = FastAPI(
    title="XmLLM",
    description="Document structure engine: image → canonical model → ALTO XML / PAGE XML",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Register routers --------------------------------------------------------

app.include_router(health_router)
app.include_router(providers_router)
app.include_router(jobs_router)
app.include_router(exports_router)
app.include_router(viewer_router)

# -- Static frontend ----------------------------------------------------------

_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "static"

if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_frontend() -> FileResponse:
        return FileResponse(str(_FRONTEND_DIR / "index.html"))
