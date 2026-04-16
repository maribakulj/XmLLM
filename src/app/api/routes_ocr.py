"""Image upload route — accepts an image, runs OCR, produces XML."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile

from src.app.api import get_job_service
from src.app.domain.models import RawProviderPayload

router = APIRouter(tags=["ocr"])

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp", ".bmp"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/ocr", status_code=201)
async def ocr_image(image: UploadFile) -> dict[str, Any]:
    """Upload an image, run PaddleOCR, and produce ALTO/PAGE XML.

    This is the main user-facing endpoint — no JSON payload needed.
    """
    if not image.filename:
        raise HTTPException(status_code=422, detail="No filename provided")

    ext = Path(image.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported format '{ext}'. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await image.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 20 MB)")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        from PIL import Image as PILImage
        with PILImage.open(tmp_path) as img:
            image_width, image_height = img.size

        from src.app.ocr import paddle_result_to_payload, run_paddle_ocr
        results = run_paddle_ocr(tmp_path)

        if not results:
            raise HTTPException(
                status_code=422,
                detail="PaddleOCR found no text in this image",
            )

        payload = paddle_result_to_payload(results)

        raw = RawProviderPayload(
            provider_id="paddleocr",
            adapter_id="adapter.word_box_json.v1",
            runtime_type="local",
            payload=payload,
            image_width=image_width,
            image_height=image_height,
        )

        svc = get_job_service()
        job = svc.create_job(
            provider_id="paddleocr",
            provider_family="word_box_json",
            source_filename=image.filename,
        )

        result = svc.run_job(
            job, raw,
            image_width=image_width,
            image_height=image_height,
            image_path=tmp_path,
        )

        return result.to_summary()

    finally:
        tmp_path.unlink(missing_ok=True)
