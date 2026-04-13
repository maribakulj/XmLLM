---
title: XmLLM
emoji: "\U0001F4C4"
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: "Document structure engine: OCR output to ALTO XML & PAGE XML"
---

# XmLLM

**Canonical-first document structure engine** that converts OCR/VLM provider outputs into validated **ALTO XML** and **PAGE XML**, via an internal canonical representation.

XmLLM is not tied to any specific OCR model. It is centered on a **canonical document contract** — a normalized, provenance-tracked, geometry-aware internal model that absorbs heterogeneous provider outputs and produces standards-compliant XML exports.

## Key features

- **Dual native export** — ALTO XML v4 and PAGE XML 2019 from the same canonical model
- **Provider-agnostic** — adapters for PaddleOCR (word+polygon), line-level OCR, and text-only mLLM
- **Full provenance** — every node tracks how its data was obtained (native, derived, repaired, manual)
- **Geometry subsystem** — normalization, transforms, quantization, tolerance-based containment
- **Validation pipeline** — structural checks, readiness assessment, export eligibility with configurable policy
- **Enrichment pipeline** — polygon-to-bbox, language propagation, reading order inference, hyphenation detection
- **Job orchestration** — 13-step pipeline with event logging, artifact persistence, state machine
- **REST API** — FastAPI with OpenAPI docs, provider management, job lifecycle, export downloads
- **Deployable anywhere** — same code runs locally, in Docker, and on Hugging Face Spaces

## Architecture

The system is organized in four concentric layers (anneaux):

```
┌─────────────────────────────────────────────────────────┐
│  D — Presentation (frontend, viewer)                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  C — API (FastAPI routes, request/response)       │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  B — Execution (providers, jobs, persistence)│  │  │
│  │  │  ┌───────────────────────────────────────┐  │  │  │
│  │  │  │  A — Domain (models, geometry,        │  │  │  │
│  │  │  │     validators, enrichers, serializers)│  │  │  │
│  │  │  └───────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Dependencies flow inward only.** The domain layer has no dependency on FastAPI, the database, or the frontend.

### Three internal objects

| Object | Role | Never used for |
|---|---|---|
| `RawProviderPayload` | Source truth — raw provider output, stored for audit | Export, rendering |
| `CanonicalDocument` | Business truth — normalized, validated, enriched | Direct UI rendering |
| `ViewerProjection` | Rendering truth — lightweight overlays for the viewer | Validation, export decisions |

### Processing pipeline

```
Input (image / raw JSON)
  → Provider Runtime (local / hub / api)
  → Raw Provider Payload (stored)
  → Adapter / Normalization (provider-specific → canonical)
  → CanonicalDocument
  → Enrichers (polygon→bbox, lang propagation, reading order, hyphenation)
  → Validators (structural, readiness, export eligibility)
  → Document Policy (strict / standard / permissive)
  → ALTO XML Serializer  ─→  alto.xml
  → PAGE XML Serializer  ─→  page.xml
  → Viewer Projection     ─→  viewer.json
  → Persistence (SQLite + filesystem)
```

## Quick start

### Local (Python)

```bash
# Clone and install
git clone https://github.com/maribakulj/XmLLM.git
cd XmLLM
pip install -e ".[dev]"

# Configure
cp .env.example .env

# Run
uvicorn src.app.main:app --host 0.0.0.0 --port 7860

# Open http://localhost:7860 for the web UI
# Open http://localhost:7860/docs for the API documentation
```

### Docker

```bash
docker compose up --build
# Open http://localhost:7860
```

### Hugging Face Spaces

The same Docker image runs as a Docker Space. Set persistent storage to enable `/data`:

```
HF_HOME=/data/.huggingface
STORAGE_ROOT=/data
```

The application auto-detects Space mode via the `SPACE_ID` environment variable.

## API reference

All endpoints are documented at `/docs` (Swagger UI) when the server is running.

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Status, version, execution mode |

### Providers

| Method | Path | Description |
|---|---|---|
| `POST` | `/providers` | Register a provider profile |
| `GET` | `/providers` | List all registered providers |
| `GET` | `/providers/{id}` | Get provider details |
| `DELETE` | `/providers/{id}` | Delete a provider |

### Jobs

| Method | Path | Description |
|---|---|---|
| `POST` | `/jobs` | Create and run a job (upload raw payload JSON) |
| `GET` | `/jobs` | List jobs (with pagination) |
| `GET` | `/jobs/{id}` | Get job details and status |
| `GET` | `/jobs/{id}/logs` | Get pipeline event log |

### Exports

| Method | Path | Description |
|---|---|---|
| `GET` | `/jobs/{id}/raw` | Download raw provider payload |
| `GET` | `/jobs/{id}/canonical` | Download canonical document JSON |
| `GET` | `/jobs/{id}/alto` | Download ALTO XML |
| `GET` | `/jobs/{id}/pagexml` | Download PAGE XML |
| `GET` | `/jobs/{id}/viewer` | Get viewer projection JSON |

### Example: run a job via API

```bash
curl -X POST "http://localhost:7860/jobs?provider_id=paddleocr&provider_family=word_box_json&image_width=2480&image_height=3508" \
  -F "raw_payload_file=@paddle_output.json"
```

## Canonical document

The `CanonicalDocument` is the central model. It represents **what the system knows about the page**, not what a specific model produced.

### Hierarchy

```
CanonicalDocument
  └── Page[]
       ├── TextRegion[] (blocks)
       │    └── TextLine[]
       │         └── Word[]
       └── NonTextRegion[] (illustrations, tables, separators)
```

### Every node carries

- **geometry** — `bbox: (x, y, width, height)` + optional `polygon` + `status` (exact / inferred / repaired / unknown)
- **provenance** — `provider`, `adapter`, `source_ref`, `evidence_type` (provider_native / derived / repaired / manual), `derived_from`
- **metadata** — extensible `dict` for future fields without schema changes

### Geometry conventions

| Convention | Value |
|---|---|
| bbox format | `(x, y, width, height)` |
| Coordinate origin | `top_left` |
| Unit | `px` |
| Polygon | `list[tuple[float, float]]` or `None` |

Providers returning `(x1, y1, x2, y2)` are converted in their adapter. No serializer performs implicit geometry conversion.

## Provider system

The provider system separates three concerns:

| Layer | Question | Examples |
|---|---|---|
| **Runtime** | How do I execute it? | `local`, `hub`, `api` |
| **Family** | What shape is the output? | `word_box_json`, `line_box_json`, `text_only` |
| **Profile** | What is this specific instance? | PaddleOCR local at `/models/paddle`, Qwen API at `https://...` |

### Adapter families

| Family | Output shape | Geometry | ALTO export |
|---|---|---|---|
| `word_box_json` | Words with 4-point polygons (PaddleOCR) | Exact | Full |
| `line_box_json` | Lines with bboxes, no word segmentation | Exact (line-level) | Full (1 word per line) |
| `text_only` | Structured text, no coordinates (mLLM) | Unknown | Refused (honest) |

### Capability matrix

Each provider profile declares a `CapabilityMatrix`:

```
block_geometry, line_geometry, word_geometry, polygon_geometry,
baseline, reading_order, text_confidence, language,
non_text_regions, tables, rotation_info
```

## Validation and policy

### Four validators

| Validator | Checks |
|---|---|
| **Schema** | Pydantic v2 model validation with structured error report |
| **Structural** | ID uniqueness, reading order references, bbox containment (configurable tolerance) |
| **Readiness** | Per-page ALTO/PAGE readiness: full, partial, degraded, or none |
| **Export eligibility** | Independent go/no-go for ALTO, PAGE, and viewer |

### Document policy

Three modes controlling what the system may do:

| Mode | Inference | Partial exports | Tolerance |
|---|---|---|---|
| `strict` | No polygon-to-bbox, no lang propagation, no reading order inference | Refused | 5px |
| `standard` (default) | Polygon-to-bbox, lang propagation, reading order, hyphenation | Allowed | 5px |
| `permissive` | All enrichments enabled | Allowed | 10px |

All modes enforce: **no text invention**, **no bbox invention**.

## Enrichers

Enrichers run after normalization, before validation. Each produces a new immutable document.

| Enricher | What it does | Provenance |
|---|---|---|
| `polygon_to_bbox` | Derives bbox from polygon when geometry is `unknown` | `inferred` |
| `bbox_repair_light` | Clips bboxes overflowing page boundaries | `repaired` |
| `lang_propagation` | Propagates language from region/line to child nodes | unchanged |
| `reading_order_simple` | Infers reading order by spatial position (top-to-bottom, left-to-right) | `inferred` |
| `hyphenation_basic` | Detects word-ending `-` at line boundary with lowercase continuation | `inferred` |
| `text_consistency` | Warns on blank or suspiciously long words (>100 chars) | warnings only |

## Export formats

### ALTO XML v4

- Namespace: `http://www.loc.gov/standards/alto/ns-v4#`
- Mapping: `Page` / `TextBlock` / `TextLine` / `String`
- Attributes: `HPOS`, `VPOS`, `WIDTH`, `HEIGHT` (integer), `CONTENT`, `WC`, `LANG`
- Hyphenation: `SUBS_TYPE` (HypPart1/HypPart2), `SUBS_CONTENT`
- Includes `<Description>` with measurement unit, filename, processing software

### PAGE XML 2019

- Namespace: `http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15`
- Mapping: `TextRegion` / `TextLine` / `Word`
- Coordinates: `<Coords points="x1,y1 x2,y2 ...">` — preserves polygons when available
- `<TextEquiv><Unicode>` at region, line, and word levels
- `<ReadingOrder>` / `<OrderedGroup>` / `<RegionRefIndexed>`
- Region `@type` mapped from block role (paragraph, heading, footnote, etc.)

### Key difference

ALTO uses axis-aligned bounding boxes (integers). PAGE XML uses polygons (preserves original quadrilateral geometry from providers like PaddleOCR).

## Project structure

```
XmLLM/
  pyproject.toml              # Dependencies and build config
  Dockerfile                  # Deployable container
  docker-compose.yml          # Local dev with volume
  AGENTS.md                   # Architecture rules (non-negotiable)
  .env.example                # Configuration reference

  src/app/
    main.py                   # FastAPI app entry point
    settings.py               # SettingsService (auto-detects local vs Space)

    api/                      # Anneau C — HTTP routes
      routes_health.py
      routes_providers.py
      routes_jobs.py
      routes_exports.py
      routes_viewer.py

    domain/                   # Anneau A — Pure domain
      models/
        canonical_document.py # CanonicalDocument, Word, TextLine, TextRegion, Page
        geometry.py           # Point, BBox, Polygon, Baseline, Geometry, GeometryContext
        provenance.py         # Provenance with conditional validation
        readiness.py          # AltoReadiness, PageXmlReadiness, ExportEligibility
        status.py             # 12 domain enums
        raw_payload.py        # RawProviderPayload
        viewer_projection.py  # OverlayItem, InspectionData, ViewerProjection
      errors/                 # ValidationReport, ValidationEntry, Severity

    geometry/                 # Geometric operations
      bbox.py                 # contains, intersects, union, iou, expand (12 ops)
      polygon.py              # polygon<->bbox, area, centroid, validation (7 ops)
      baseline.py             # length, angle, interpolation
      transforms.py           # rescale, clip, rotate, translate
      normalization.py        # xyxy->xywh, 4-point->bbox, pixel<->normalized
      quantization.py         # float->int strategies, tolerance checks

    providers/                # Anneau B — Provider system
      registry.py             # Central adapter + runtime index
      resolver.py             # Profile -> runtime + adapter
      profiles.py             # ProviderProfile model
      capabilities.py         # CapabilityMatrix
      runtimes/
        base.py               # BaseRuntime ABC
        local_runtime.py
        hub_runtime.py
        api_runtime.py
      adapters/
        base.py               # BaseAdapter ABC
        word_box_json.py      # PaddleOCR format
        line_box_json.py      # Line-level OCR
        text_only.py          # mLLM without geometry

    normalization/
      pipeline.py             # Raw -> CanonicalDocument orchestration
      canonical_builder.py    # Fluent builder for CanonicalDocument

    enrichers/
      __init__.py             # BaseEnricher ABC + EnricherPipeline
      polygon_to_bbox.py
      bbox_repair_light.py
      lang_propagation.py
      reading_order_simple.py
      hyphenation_basic.py
      text_consistency.py

    validators/
      schema_validator.py
      structural_validator.py
      readiness_validator.py
      export_eligibility_validator.py

    policies/
      document_policy.py      # Strict / standard / permissive modes
      export_policy.py        # Per-format go/no-go decisions

    serializers/
      alto_xml.py             # CanonicalDocument -> ALTO XML v4
      page_xml.py             # CanonicalDocument -> PAGE XML 2019

    viewer/
      projection_builder.py   # CanonicalDocument -> ViewerProjection
      overlays.py             # Node -> OverlayItem/InspectionData

    jobs/
      models.py               # Job model (5-state machine)
      events.py               # EventLog with timed steps
      service.py              # JobService (13-step pipeline orchestrator)

    persistence/
      db.py                   # SQLite (jobs + providers)
      file_store.py           # Filesystem artifact store

  frontend/static/
    index.html                # Single-page web UI

  tests/
    fixtures/                 # 7 test fixtures (simple, columns, noisy, etc.)
    unit/                     # 24 unit test modules
    integration/              # 5 integration test modules
```

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `APP_MODE` | `local` | `local` or `space` (auto-detected from `SPACE_ID`) |
| `STORAGE_ROOT` | `./data` | Root for all persistent data |
| `DB_NAME` | `app.db` | SQLite database filename |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `7860` | Server port |
| `MAX_UPLOAD_SIZE` | `52428800` | Max upload size in bytes (50 MB) |
| `ALLOWED_MIME_TYPES` | `image/png,jpeg,tiff,webp` | Accepted upload types |
| `PROVIDER_TIMEOUT` | `120` | Provider execution timeout (seconds) |
| `BBOX_CONTAINMENT_TOLERANCE` | `5` | Pixels of allowed bbox overflow |

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=term-missing

# Only unit tests
pytest tests/unit/

# Only integration tests
pytest tests/integration/
```

**497 tests** covering:
- Domain models (validation, rejection, JSON round-trips)
- Geometry operations (all transforms, containment, quantization)
- Adapters (PaddleOCR, line-box, text-only formats)
- Serializers (ALTO structure, PAGE structure, hyphenation, polygons)
- Validators (structural, readiness, export eligibility)
- Enrichers (all 6 enrichers + pipeline + policy control)
- Persistence (file store, SQLite CRUD)
- API routes (providers, jobs, exports, viewer)
- End-to-end fixtures (simple page, double column, noisy page, title+body, hyphenation, text-only)

## V1 scope

### Included

- Single image input
- Local, Hub, and API runtimes (skeleton — raw payloads provided directly in V1)
- 3 adapter families (word_box_json, line_box_json, text_only)
- Full CanonicalDocument with provenance and geometry
- ALTO XML v4 and PAGE XML 2019 native export
- 6 enrichers with policy control
- 4 validators with configurable tolerance
- Job orchestration with event logging
- SQLite + filesystem persistence
- REST API with OpenAPI docs
- Web UI for upload, job management, and export download
- Docker deployment

### Excluded (V2+)

- PDF multipage input
- Live model execution (currently raw payloads are provided externally)
- Manual editing of canonical documents
- Multi-user collaboration
- Batch processing
- Fine-tuning
- Advanced table extraction
- OpenSeadragon interactive viewer with overlays
- Authentication

## License

Apache 2.0 — see [LICENSE](LICENSE).
