"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter

from src.app.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": "0.1.0",
        "mode": settings.app_mode.value,
        "hf_token_set": bool(settings.hf_token),
        "storage_root": str(settings.storage_root),
    }
