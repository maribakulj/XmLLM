# AGENTS.md — XmLLM Project Rules

## What this project is

XmLLM is a **canonical-first document structure engine** that converts images (and
later PDFs) into structured ALTO XML and PAGE XML, via an internal canonical
representation (`CanonicalDocument`).

## Architecture invariants

These rules are **non-negotiable**. Any code change that violates them must be
rejected.

### 1. Canonical-first

- The system is **never** provider-first, ALTO-first, PAGE-first, or viewer-first.
- All processing flows through `CanonicalDocument`.
- ALTO XML and PAGE XML are **output serializations**, not internal representations.

### 2. Three internal objects

| Object              | Role               | Never used for               |
|---------------------|--------------------|------------------------------|
| `RawProviderPayload`| Source truth        | Export, rendering            |
| `CanonicalDocument` | Business truth      | Direct UI rendering          |
| `ViewerProjection`  | Rendering truth     | Validation, export decisions |

### 3. Domain independence

- Anneau A (domain) **must not** depend on FastAPI, frontend, or OpenSeadragon.
- Anneau B (execution) may depend on domain.
- Anneau C (API) may depend on domain and execution.
- Anneau D (presentation) may depend on the API layer only.

### 4. Provenance on every node

Every node in `CanonicalDocument` **must** carry a `provenance` with:
- `provider`: source engine name
- `adapter`: adapter version
- `source_ref`: path in the raw output
- `evidence_type`: `provider_native | derived | repaired | manual`
- `derived_from`: list of canonical IDs (empty if native)

### 5. Geometry conventions

- **bbox format**: `[x, y, width, height]` — always. `x` = left edge, `y` = top edge.
- **coordinate origin**: `top_left` — always in internal representation.
- **unit**: `px` — always in the canonical model.
- **polygon**: `list[tuple[float, float]] | None` — optional, preserved when available.
- **Providers returning `[x1, y1, x2, y2]`** must be converted in their adapter.
- **No serializer** may perform implicit heavy geometry conversion. All geometry
  must be normalized before it reaches a serializer.

### 6. Serializer rules

Serializers (ALTO, PAGE) **must not**:
- Call any model or provider
- Reconstruct segmentation
- Correct text
- Invent coordinates
- Make export eligibility decisions

They receive a validated `CanonicalDocument` and produce deterministic XML.

### 7. Export eligibility

- Every export decision must pass through validators + document policy.
- A serializer is **never** called when export eligibility is `none`.
- ALTO and PAGE eligibility are computed **independently**.

### 8. Enricher rules

Every enricher **must**:
- Set `provenance.evidence_type` to `derived` or `inferred`
- Update `geometry.status` if geometry was modified
- Add warnings to the document when appropriate
- Respect the active `DocumentPolicy`

Enrichers **must not**:
- Hallucinate text
- Invent fine-grained coordinates without geometric basis
- Claim `provider_native` evidence

### 9. Viewer rules

- The viewer **never** parses ALTO or PAGE XML.
- It works exclusively from `ViewerProjection`.
- No business logic in the presentation layer.

### 10. Single codebase

The same code runs:
- Locally (bare Python)
- In Docker
- On Hugging Face Spaces

The only difference is `STORAGE_ROOT` and environment detection.

## Bbox containment tolerance

Bbox containment checks (child within parent) use a configurable tolerance
(default: 5px). This is set via `BBOX_CONTAINMENT_TOLERANCE` in the environment.

## Coding conventions

- Python 3.11+
- Pydantic v2 for all models
- `lxml` for XML serialization
- Type hints everywhere
- No `Any` types in domain models
- Tests alongside implementation — no sprint ships without tests
