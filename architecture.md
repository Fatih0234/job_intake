# architecture.compact.md

## Intent
Build a **small, high-signal personal job intake pipeline** optimized for:
- clarity
- maintainability
- inspectability
- relevance quality
- clean Notion review flow

Not optimized for:
- broad market coverage
- multi-platform orchestration
- map/UI complexity
- heavy scheduling infrastructure
- large-scale analytics

## System flow
```text
configs
→ search definitions
→ LinkedIn discovery
→ LinkedIn details
→ normalize + upsert to Supabase
→ classify (student-fit + role-family)
→ shortlist
→ Notion sync (subset only)
```

## Core architecture decisions
- **Supabase is canonical** for raw data, normalized jobs, classifications, and sync state.
- **LinkedIn is the only adapter in v1.**
- **Scraping, matching, shortlist, and sync are separate layers.**
- **Notion receives only a curated subset.**

## Layers
### 1) Search Definition Layer
Purpose: represent the search universe declaratively.

Inputs:
- target cities
- role-family keywords
- student-job keywords
- optional LinkedIn filters
- German + English query variants

Example config:
```yaml
search_profiles:
  - name: berlin_data_engineering_werkstudent
    city: Berlin
    role_family: data_engineering
    keywords:
      - "data engineer werkstudent"
      - "working student data engineering"
    enabled: true
```

Rule: keep searches in config, not hardcoded in scraping scripts.

### 2) LinkedIn Adapter Layer
Purpose: handle LinkedIn-specific scraping.

Responsibilities:
- generate/resolve search URLs
- fetch list pages
- parse job cards
- fetch detail pages
- parse details
- normalize LinkedIn identifiers

Non-responsibilities:
- role-family logic
- student-fit scoring
- Notion sync decisions

Suggested module split:
```text
src/adapters/linkedin/
├── search.py
├── parser_list.py
├── parser_detail.py
├── models.py
└── spider.py
```

### 3) Storage Layer
Purpose: persist raw and canonical data in Supabase/Postgres.

Recommended logical tables:
- `search_definitions`
- `job_discoveries`
- `jobs`
- `job_classifications`
- `notion_sync_state`
- `pipeline_runs`

Canonical key rule:
- preferred: `linkedin:{external_job_id}`
- fallback: deterministic normalized URL key

### 4) Classification Layer
Purpose: assign:
- `student_fit`
- `role_family`

Suggested modules:
```text
src/classifiers/
├── student_fit.py
├── role_family.py
├── shortlist.py
└── keyword_rules.py
```

Recommended labels:
- student fit:
  - `target_student_job`
  - `possible_student_job`
  - `not_student_job`
- role family:
  - `data_engineering`
  - `analytics_engineering`
  - `analytics_bi`
  - `ml_ai_engineering`
  - `out_of_scope`

Rule: use deterministic weighted rules first, not LLM dependency.

### 5) Shortlist Layer
Purpose: decide what is eligible for Notion sync.

Default rule:
- city is in target set
- role family is in scope
- student fit is `target_student_job` or `possible_student_job`
- required fields are present

Recommended v1 strictness:
- sync only `target_student_job` by default
- keep `possible_student_job` in Supabase unless config says otherwise

### 6) Notion Sync Layer
Purpose: project a small subset into Notion.

Responsibilities:
- map canonical job data to Notion properties
- create/update pages
- preserve manual workflow fields
- stay idempotent

Suggested module split:
```text
src/notion/
├── client.py
├── mapper.py
├── sync.py
└── schema.py
```

Rules:
- Sync consumes shortlist outputs; it does not decide relevance itself.
- Use `Canonical Job Key` in Notion plus `notion_sync_state` in Supabase.
- Preserve `Priority`, `Review Status`, `Application Status`, and `Notes` unless explicitly told otherwise.

## Runtime flow
```text
load config
→ generate searches
→ run LinkedIn discovery
→ store discoveries
→ fetch details for new/changed jobs
→ normalize/upsert jobs
→ run classification
→ compute shortlist
→ sync shortlisted jobs to Notion
→ store run stats
```

## Failure handling
- discovery failures should fail the run clearly
- detail failures can be recorded per job
- classification failures should never silently drop jobs
- Notion sync failures should be recorded and retryable

## Boundaries to keep clean
- Scraper knows LinkedIn specifics, not product policy.
- Storage does not encode presentation logic.
- Classification is centralized and testable.
- Notion mapping does not leak into core normalization.

## Extension path
Easy later additions:
- StepStone adapter
- XING adapter
- more cities
- shortlist strictness changes
- better scoring/ranking
- notifications

Intentionally postponed:
- auto-apply flows
- dashboards/maps
- AI ranking
- browser-authenticated automation
- broad lifecycle engines

## Suggested repo shape
```text
src/
├── adapters/linkedin/
├── classifiers/
├── models/
├── storage/
├── notion/
├── orchestration/
└── utils/
```

## Testing
- unit: keyword logic, normalization, canonical key generation, shortlist
- parser: LinkedIn list/detail fixtures
- storage: upsert and dedupe behavior
- Notion: payload mapping, idempotency, create-vs-update
- smoke: tiny end-to-end config

## Operations
Use `uv` and simple scripts:
```bash
uv sync
uv run python -m scripts.run_pipeline
```

Log per run:
- search count
- discoveries count
- details count
- classified count
- shortlisted count
- synced count
- error count

## Final stance
The correct v1 architecture is a **narrow pipeline with strong boundaries**:
- one source
- one canonical store
- one classification layer
- one curated review surface
