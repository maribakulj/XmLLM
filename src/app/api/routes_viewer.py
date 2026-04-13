"""Viewer projection route."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.app.api import get_file_store

router = APIRouter(prefix="/jobs", tags=["viewer"])


@router.get("/{job_id}/viewer")
async def get_viewer_projection(job_id: str) -> dict[str, Any]:
    """Get the viewer projection JSON for a job.

    Returns a lightweight structure for the front-end viewer.
    Falls back to canonical document if viewer projection not yet built.
    """
    store = get_file_store()

    # Try viewer projection first
    viewer = store.load_viewer(job_id)
    if viewer is not None:
        return viewer

    # Fall back: return a minimal projection from canonical
    canonical = store.load_canonical(job_id)
    if canonical is None:
        raise HTTPException(
            status_code=404,
            detail=f"No viewer data available for job '{job_id}'",
        )

    # Build a minimal viewer-like response from canonical
    pages = canonical.get("pages", [])
    if not pages:
        raise HTTPException(status_code=404, detail="No pages in canonical document")

    page = pages[0]
    return {
        "image_ref": canonical.get("source", {}).get("filename", ""),
        "image_width": page.get("width", 0),
        "image_height": page.get("height", 0),
        "block_overlays": [],
        "line_overlays": [],
        "word_overlays": [],
        "non_text_overlays": [],
        "inspection_index": {},
        "validation_flags": [],
        "export_status": {
            "alto_export": "none",
            "page_export": "none",
            "viewer_render": "none",
        },
    }
