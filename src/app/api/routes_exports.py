"""Export download routes — ALTO, PAGE XML, raw payload, canonical JSON."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.app.api import get_file_store

router = APIRouter(prefix="/jobs", tags=["exports"])


@router.get("/{job_id}/raw")
async def get_raw_payload(job_id: str) -> dict[str, Any]:
    """Download the raw provider payload."""
    store = get_file_store()
    data = store.load_raw_payload(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Raw payload not found for job '{job_id}'")
    return data


@router.get("/{job_id}/canonical")
async def get_canonical(job_id: str) -> dict[str, Any]:
    """Download the canonical document JSON."""
    store = get_file_store()
    data = store.load_canonical(job_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Canonical document not found for job '{job_id}'",
        )
    return data


@router.get("/{job_id}/alto")
async def get_alto(job_id: str) -> Response:
    """Download the ALTO XML file."""
    store = get_file_store()
    data = store.load_alto(job_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"ALTO XML not available for job '{job_id}' — export may not have been eligible",
        )
    return Response(
        content=data,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_alto.xml"'},
    )


@router.get("/{job_id}/pagexml")
async def get_page_xml(job_id: str) -> Response:
    """Download the PAGE XML file."""
    store = get_file_store()
    data = store.load_page_xml(job_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"PAGE XML not available for job '{job_id}' — export may not have been eligible",
        )
    return Response(
        content=data,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_page.xml"'},
    )
