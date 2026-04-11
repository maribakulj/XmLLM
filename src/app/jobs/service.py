"""Job service — orchestrates the full processing pipeline.

Pipeline steps (§23.1):
  1. receive file
  2. create execution context
  3. resolve provider
  4. execute runtime (skipped in V1 — raw payload provided externally)
  5. save raw payload
  6. normalize
  7. enrich
  8. validate
  9. compute readiness
  10. export ALTO
  11. export PAGE
  12. build viewer projection
  13. persist
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.app.domain.models import CanonicalDocument, RawProviderPayload
from src.app.domain.models.geometry import GeometryContext
from src.app.enrichers import EnricherPipeline
from src.app.enrichers.bbox_repair_light import BboxRepairLightEnricher
from src.app.enrichers.hyphenation_basic import HyphenationBasicEnricher
from src.app.enrichers.lang_propagation import LangPropagationEnricher
from src.app.enrichers.polygon_to_bbox import PolygonToBboxEnricher
from src.app.enrichers.reading_order_simple import ReadingOrderSimpleEnricher
from src.app.enrichers.text_consistency import TextConsistencyEnricher
from src.app.jobs.events import EventLog, JobStep
from src.app.jobs.models import Job, JobStatus
from src.app.normalization.pipeline import normalize
from src.app.persistence.db import Database
from src.app.persistence.file_store import FileStore
from src.app.policies.document_policy import DocumentPolicy
from src.app.policies.export_policy import check_alto_export, check_page_export
from src.app.serializers.alto_xml import serialize_alto
from src.app.serializers.page_xml import serialize_page_xml
from src.app.validators.export_eligibility_validator import compute_export_eligibility
from src.app.validators.structural_validator import validate_structure
from src.app.viewer.projection_builder import build_projection


def _default_enricher_pipeline() -> EnricherPipeline:
    return EnricherPipeline([
        PolygonToBboxEnricher(),
        BboxRepairLightEnricher(),
        LangPropagationEnricher(),
        ReadingOrderSimpleEnricher(),
        HyphenationBasicEnricher(),
        TextConsistencyEnricher(),
    ])


class JobService:
    """Orchestrates the full document processing pipeline."""

    def __init__(self, db: Database, file_store: FileStore) -> None:
        self._db = db
        self._store = file_store

    def create_job(
        self,
        provider_id: str,
        provider_family: str,
        source_filename: str | None = None,
    ) -> Job:
        """Create a new job record."""
        job = Job(
            job_id=f"job_{uuid.uuid4().hex[:12]}",
            provider_id=provider_id,
            provider_family=provider_family,
            source_filename=source_filename,
        )
        self._db.save_job(job)
        return job

    def run_job(
        self,
        job: Job,
        raw_payload: RawProviderPayload,
        image_width: int,
        image_height: int,
        *,
        image_path: Path | None = None,
        policy: DocumentPolicy | None = None,
        enricher_pipeline: EnricherPipeline | None = None,
    ) -> Job:
        """Execute the full pipeline for a job.

        In V1, the raw_payload is provided externally (runtime execution
        is not yet integrated). The pipeline runs synchronously.
        """
        if policy is None:
            policy = DocumentPolicy()
        if enricher_pipeline is None:
            enricher_pipeline = _default_enricher_pipeline()

        events = EventLog()
        job = job.model_copy(update={
            "status": JobStatus.RUNNING,
            "started_at": datetime.now(timezone.utc),
            "image_width": image_width,
            "image_height": image_height,
        })
        self._db.save_job(job)

        canonical: CanonicalDocument | None = None
        warnings: list[str] = []

        try:
            # Step 1: receive file
            with events.step(JobStep.RECEIVE_FILE):
                if image_path and image_path.exists():
                    self._store.save_input_image(job.job_id, image_path)

            # Step 5: save raw payload
            with events.step(JobStep.SAVE_RAW):
                self._store.save_raw_payload(
                    job.job_id, raw_payload.model_dump(mode="json")
                )
                job = job.model_copy(update={"has_raw_payload": True})

            # Step 6: normalize
            with events.step(JobStep.NORMALIZE):
                geo_ctx = GeometryContext(
                    source_width=image_width, source_height=image_height
                )
                canonical = normalize(
                    raw_payload,
                    family=job.provider_family,
                    geometry_context=geo_ctx,
                    document_id=job.job_id,
                    source_filename=job.source_filename,
                )

            # Step 7: enrich
            with events.step(JobStep.ENRICH):
                canonical = enricher_pipeline.run(canonical, policy)

            # Step 8: validate
            with events.step(JobStep.VALIDATE):
                struct_report = validate_structure(
                    canonical, bbox_tolerance=policy.bbox_containment_tolerance
                )
                for entry in struct_report.warnings:
                    warnings.append(f"[structural] {entry.path}: {entry.message}")
                for entry in struct_report.errors:
                    warnings.append(f"[structural:ERROR] {entry.path}: {entry.message}")

            # Step 9: compute readiness + export eligibility
            with events.step(JobStep.COMPUTE_READINESS):
                eligibility = compute_export_eligibility(canonical, policy)

            # Save canonical
            self._store.save_canonical(
                job.job_id, canonical.model_dump(mode="json")
            )
            job = job.model_copy(update={"has_canonical": True})

            # Step 10: export ALTO
            alto_decision = check_alto_export(eligibility, policy)
            if alto_decision.allowed:
                with events.step(JobStep.EXPORT_ALTO):
                    alto_bytes = serialize_alto(canonical)
                    self._store.save_alto(job.job_id, alto_bytes)
                    job = job.model_copy(update={"has_alto": True})
            else:
                events.skip(JobStep.EXPORT_ALTO, alto_decision.reason)

            # Step 11: export PAGE
            page_decision = check_page_export(eligibility, policy)
            if page_decision.allowed:
                with events.step(JobStep.EXPORT_PAGE):
                    page_bytes = serialize_page_xml(canonical)
                    self._store.save_page_xml(job.job_id, page_bytes)
                    job = job.model_copy(update={"has_page_xml": True})
            else:
                events.skip(JobStep.EXPORT_PAGE, page_decision.reason)

            # Step 12: build viewer projection
            with events.step(JobStep.BUILD_VIEWER):
                vp = build_projection(canonical, export_status=eligibility)
                self._store.save_viewer(job.job_id, vp.model_dump(mode="json"))
                job = job.model_copy(update={"has_viewer": True})

            # Step 13: persist final state
            with events.step(JobStep.PERSIST):
                self._store.save_events(job.job_id, events.to_dicts())

            # Determine final status
            if job.has_alto or job.has_page_xml:
                if job.has_alto and job.has_page_xml:
                    final_status = JobStatus.SUCCEEDED
                else:
                    final_status = JobStatus.PARTIAL_SUCCESS
            else:
                final_status = JobStatus.PARTIAL_SUCCESS

            job = job.model_copy(update={
                "status": final_status,
                "completed_at": datetime.now(timezone.utc),
                "warnings": warnings,
            })

        except Exception as exc:
            job = job.model_copy(update={
                "status": JobStatus.FAILED,
                "completed_at": datetime.now(timezone.utc),
                "error": str(exc),
                "warnings": warnings,
            })
            # Save events even on failure
            self._store.save_events(job.job_id, events.to_dicts())

        self._db.save_job(job)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._db.get_job(job_id)

    def list_jobs(self, limit: int = 100, offset: int = 0) -> list[Job]:
        return self._db.list_jobs(limit, offset)
