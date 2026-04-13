"""Domain errors for validation and export."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    """Severity level for validation entries."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationEntry(BaseModel):
    """A single validation finding."""

    model_config = ConfigDict(frozen=True)

    validator: str = Field(min_length=1)
    severity: Severity
    path: str = Field(
        min_length=1,
        description="Path in the document, e.g. pages[0].text_regions[1].lines[3]",
    )
    message: str = Field(min_length=1)
    code: str | None = None


class ValidationReport(BaseModel):
    """Aggregated results from all validators."""

    entries: list[ValidationEntry] = Field(default_factory=list)

    @property
    def errors(self) -> list[ValidationEntry]:
        return [e for e in self.entries if e.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationEntry]:
        return [e for e in self.entries if e.severity == Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def add(self, entry: ValidationEntry) -> None:
        self.entries.append(entry)

    def merge(self, other: ValidationReport) -> None:
        self.entries.extend(other.entries)
