"""File store — abstraction for persisting job artifacts on disk.

Storage layout:
    {STORAGE_ROOT}/
      jobs/
        {job_id}/
          input.{ext}        — original uploaded image
          raw_payload.json   — RawProviderPayload
          canonical.json     — CanonicalDocument
          alto.xml           — ALTO XML export
          page.xml           — PAGE XML export
          viewer.json        — ViewerProjection
          events.json        — job events log
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


class FileStore:
    """Manages artifact persistence for jobs."""

    def __init__(self, storage_root: Path) -> None:
        self._root = storage_root
        self._jobs_dir = storage_root / "jobs"
        self._providers_dir = storage_root / "providers"

    def ensure_dirs(self) -> None:
        """Create required directories."""
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._providers_dir.mkdir(parents=True, exist_ok=True)

    # -- Job directory --------------------------------------------------------

    def job_dir(self, job_id: str) -> Path:
        d = self._jobs_dir / job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    # -- Save artifacts -------------------------------------------------------

    def save_input_image(self, job_id: str, source_path: Path) -> Path:
        """Copy the input image into the job directory."""
        dest = self.job_dir(job_id) / f"input{source_path.suffix}"
        shutil.copy2(source_path, dest)
        return dest

    def save_json(self, job_id: str, filename: str, data: Any) -> Path:
        """Save a JSON-serializable object."""
        dest = self.job_dir(job_id) / filename
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return dest

    def save_bytes(self, job_id: str, filename: str, data: bytes) -> Path:
        """Save raw bytes (e.g. XML)."""
        dest = self.job_dir(job_id) / filename
        dest.write_bytes(data)
        return dest

    def save_raw_payload(self, job_id: str, data: dict) -> Path:
        return self.save_json(job_id, "raw_payload.json", data)

    def save_canonical(self, job_id: str, data: dict) -> Path:
        return self.save_json(job_id, "canonical.json", data)

    def save_alto(self, job_id: str, xml_bytes: bytes) -> Path:
        return self.save_bytes(job_id, "alto.xml", xml_bytes)

    def save_page_xml(self, job_id: str, xml_bytes: bytes) -> Path:
        return self.save_bytes(job_id, "page.xml", xml_bytes)

    def save_viewer(self, job_id: str, data: dict) -> Path:
        return self.save_json(job_id, "viewer.json", data)

    def save_events(self, job_id: str, events: list[dict]) -> Path:
        return self.save_json(job_id, "events.json", events)

    # -- Load artifacts -------------------------------------------------------

    def load_json(self, job_id: str, filename: str) -> Any:
        """Load a JSON file from the job directory. Returns None if not found."""
        path = self._jobs_dir / job_id / filename
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_bytes(self, job_id: str, filename: str) -> bytes | None:
        """Load raw bytes. Returns None if not found."""
        path = self._jobs_dir / job_id / filename
        if not path.exists():
            return None
        return path.read_bytes()

    def load_raw_payload(self, job_id: str) -> dict | None:
        return self.load_json(job_id, "raw_payload.json")

    def load_canonical(self, job_id: str) -> dict | None:
        return self.load_json(job_id, "canonical.json")

    def load_alto(self, job_id: str) -> bytes | None:
        return self.load_bytes(job_id, "alto.xml")

    def load_page_xml(self, job_id: str) -> bytes | None:
        return self.load_bytes(job_id, "page.xml")

    def load_viewer(self, job_id: str) -> dict | None:
        return self.load_json(job_id, "viewer.json")

    def load_events(self, job_id: str) -> list[dict] | None:
        return self.load_json(job_id, "events.json")

    # -- Input image ----------------------------------------------------------

    def get_input_image_path(self, job_id: str) -> Path | None:
        """Find the input image for a job (any extension)."""
        d = self._jobs_dir / job_id
        if not d.exists():
            return None
        for f in d.iterdir():
            if f.stem == "input" and f.suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"):
                return f
        return None

    # -- Provider profiles ----------------------------------------------------

    def save_provider(self, provider_id: str, data: dict) -> Path:
        dest = self._providers_dir / f"{provider_id}.json"
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return dest

    def load_provider(self, provider_id: str) -> dict | None:
        path = self._providers_dir / f"{provider_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_providers(self) -> list[str]:
        if not self._providers_dir.exists():
            return []
        return [f.stem for f in self._providers_dir.glob("*.json")]

    def delete_provider(self, provider_id: str) -> bool:
        path = self._providers_dir / f"{provider_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # -- Listing --------------------------------------------------------------

    def list_jobs(self) -> list[str]:
        if not self._jobs_dir.exists():
            return []
        return sorted(
            [d.name for d in self._jobs_dir.iterdir() if d.is_dir()],
            reverse=True,
        )

    def job_exists(self, job_id: str) -> bool:
        return (self._jobs_dir / job_id).exists()

    def job_has_artifact(self, job_id: str, filename: str) -> bool:
        return (self._jobs_dir / job_id / filename).exists()
