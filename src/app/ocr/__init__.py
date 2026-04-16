"""PaddleOCR integration — runs OCR on an image and returns word_box_json payload."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ocr_instance = None


def _get_ocr() -> Any:
    """Lazy-load PaddleOCR (heavy import, ~2s first time)."""
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="fr", show_log=False)
    return _ocr_instance


def run_paddle_ocr(image_path: Path) -> list[Any]:
    """Run PaddleOCR on an image file.

    Returns the raw PaddleOCR result in word_box_json format:
        [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ("text", confidence)]
    """
    ocr = _get_ocr()
    results = ocr.ocr(str(image_path), cls=True)
    if not results or not results[0]:
        return []
    return results[0]


def paddle_result_to_payload(results: list[Any]) -> list[Any]:
    """Convert PaddleOCR results to the word_box_json payload format."""
    payload = []
    for item in results:
        points = item[0]
        text, conf = item[1]
        payload.append([points, [text, conf]])
    return payload
