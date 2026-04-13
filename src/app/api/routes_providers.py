"""Provider management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.app.api import get_db, get_file_store

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderCreateRequest(BaseModel):
    provider_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    runtime_type: str = Field(min_length=1)
    model_id_or_path: str = Field(min_length=1)
    family: str = Field(min_length=1)
    endpoint: str | None = None
    auth_mode: str = "none"
    timeout: int = Field(default=120, gt=0)
    prompt_template: str | None = None


class ProviderResponse(BaseModel):
    provider_id: str
    data: dict[str, Any]


@router.post("", status_code=201)
async def register_provider(req: ProviderCreateRequest) -> ProviderResponse:
    """Register a new provider profile."""
    db = get_db()
    store = get_file_store()

    data = req.model_dump()
    db.save_provider_record(req.provider_id, data)
    store.save_provider(req.provider_id, data)

    return ProviderResponse(provider_id=req.provider_id, data=data)


@router.get("")
async def list_providers() -> list[dict[str, Any]]:
    """List all registered providers."""
    db = get_db()
    return db.list_provider_records()


@router.get("/{provider_id}")
async def get_provider(provider_id: str) -> dict[str, Any]:
    """Get a provider by ID."""
    db = get_db()
    record = db.get_provider_record(provider_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    return record


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: str) -> None:
    """Delete a provider."""
    db = get_db()
    store = get_file_store()

    if not db.delete_provider_record(provider_id):
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    store.delete_provider(provider_id)
