"""Provenance model — tracks how every piece of data was produced.

Every node in the CanonicalDocument must carry a Provenance.  This is
the foundation of the system's explainability and auditability.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.app.domain.models.status import EvidenceType


class Provenance(BaseModel):
    """Tracks the origin and derivation chain of a canonical node."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(min_length=1)
    adapter: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    evidence_type: EvidenceType
    derived_from: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_derivation_consistency(self) -> Provenance:
        """provider_native data cannot have derivation parents."""
        if self.evidence_type == EvidenceType.PROVIDER_NATIVE and self.derived_from:
            raise ValueError(
                "provider_native evidence must have an empty derived_from list, "
                f"got {self.derived_from}"
            )
        return self
