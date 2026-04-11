"""Job management routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile

from src.app.api import get_file_store, get_job_service
from src.app.domain.models import RawProviderPayload

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", status_code=201)
async def create_job(
    provider_id: str,
    provider_family: str,
    image_width: int,
    image_height: int,
    raw_payload_file: UploadFile,
    source_filename: str | None = None,
) -> dict[str, Any]:
    """Create and run a job.

    Accepts a raw provider payload JSON file and image dimensions.
    Runs the full pipeline synchronously (V1).
    """
    svc = get_job_service()

    # Read raw payload
    content = await raw_payload_file.read()
    try:
        payload_data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON payload: {e}")

    raw = RawProviderPayload(
        provider_id=provider_id,
        adapter_id=f"adapter.{provider_family}.v1",
        runtime_type="local",
        payload=payload_data,
        image_width=image_width,
        image_height=image_height,
    )

    job = svc.create_job(
        provider_id=provider_id,
        provider_family=provider_family,
        source_filename=source_filename or raw_payload_file.filename,
    )

    result = svc.run_job(
        job, raw, image_width=image_width, image_height=image_height
    )

    return result.to_summary()


@router.get("")
async def list_jobs(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """List all jobs."""
    svc = get_job_service()
    jobs = svc.list_jobs(limit=limit, offset=offset)
    return [j.to_summary() for j in jobs]


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    """Get job details."""
    svc = get_job_service()
    job = svc.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.model_dump(mode="json")


@router.get("/{job_id}/logs")
async def get_job_logs(job_id: str) -> list[dict]:
    """Get event logs for a job."""
    store = get_file_store()
    events = store.load_events(job_id)
    if events is None:
        raise HTTPException(status_code=404, detail=f"No logs for job '{job_id}'")
    return events
