# AGENTS.compact.md

## Mission
Build **v1 of a personal student-job intake system** for Fatih Karahan.

## Hard scope
- Source: **LinkedIn public/guest jobs only**
- Jobs: **student-compatible only**
- Geography: **selected German cities only**
- Role families only:
  - `data_engineering`
  - `analytics_engineering`
  - `analytics_bi`
  - `ml_ai_engineering`
- **Supabase** = canonical source of truth
- **Notion** = curated shortlist workspace
- **Notion MCP** = preferred Notion control plane

Do **not** turn v1 into a broad multi-platform, map-heavy, or automation-heavy system.

## Non-goals
Do not add unless explicitly requested:
- StepStone
- XING
- company-site crawling
- geocoding/maps
- Germany-wide expansion
- auto-application
- resume generation
- heavy orchestration frameworks
- LLM-first classification

## Core rules
- Keep boundaries clean:
  1. search definitions
  2. LinkedIn adapter
  3. storage
  4. classification
  5. shortlist
  6. Notion sync
- Scraping collects data; matching decides fit.
- Sync only a **subset** of jobs into Notion.
- Prefer deterministic rules before AI.
- Prefer **precision over recall** in v1.
- Keep code simple, typed, testable, and inspectable.

## Infrastructure
Use exactly one Supabase project:
- Name: `student-jobs`
- Ref: `aashdnhoiqqdhpdedaab`
- URL: `https://aashdnhoiqqdhpdedaab.supabase.co`

Rules:
- Use this project only.
- Run `supabase link --project-ref aashdnhoiqqdhpdedaab` before CLI work if needed.
- Run `supabase db pull` before migrations when remote schema may have changed.
- Keep secrets only in `.env.local` or local shell environment.
- Never expose `SUPABASE_SERVICE_ROLE_KEY` to client-side code.
- If a required secret is missing, stop and ask.

## Notion rules
### Ownership
- Supabase owns raw jobs, canonical jobs, classifications, shortlist state, and sync state.
- Notion owns review workflow, prioritization, notes, and application tracking.
- Do not treat Notion as canonical scraped-data storage.

### Control plane
Use **Notion MCP first** to:
- search the workspace
- create pages/databases
- create linked views
- evolve schema when needed

Use the direct Notion API only if MCP is unavailable or insufficient.

### Bootstrap behavior
If the Notion review workspace does not exist:
1. search for expected root/database
2. create them if missing
3. store created/discovered IDs locally
4. continue setup

### Defaults
- Root page: `Student Job Intake`
- Main database: `Student Jobs - Shortlist`

Suggested linked views/pages:
- `Now`
- `Data Engineering`
- `Analytics Engineering`
- `Analytics / BI`
- `ML / AI`
- `Berlin + Hamburg`
- `Posted Recently`
- `Need Resume Tailoring`

### Database properties
Ensure the main Notion database includes at least:
- `Job Title`
- `Company`
- `City`
- `Platform`
- `Role Family`
- `Student Fit`
- `Posted Text`
- `Job URL`
- `Shortlist Reason`
- `Priority`
- `Review Status`
- `Application Status`
- `Notes`
- `Source Search Name`
- `Canonical Job Key`
- `Synced At`
- `Last Seen At` (optional)

### Sync safety
- Prefer **one database + linked views**, not many duplicated databases.
- Preserve manual fields by default:
  - `Priority`
  - `Review Status`
  - `Application Status`
  - `Notes`
- Every Notion item must map to a canonical job via `Canonical Job Key`.
- Do not create duplicates across runs.
- Search before creating new pages/databases.

## Local config
Expected:
- `.env.local` = real local secrets/IDs
- `.env.local.example` = placeholders only

Never commit:
- `.env.local`
- service-role keys
- PATs
- Notion secrets

Useful local values:
- `NOTION_API_TOKEN` (fallback only)
- `NOTION_PARENT_PAGE_ID`
- `NOTION_ROOT_PAGE_ID`
- `NOTION_DATABASE_ID`
- `NOTION_MCP_ENABLED=true`

## Shortlist / sync policy
Sync only shortlisted jobs by default.

Recommended shortlist rule:
- city in target city set
- role family in scope
- student fit is `target_student_job` or `possible_student_job`
- minimum required fields present

Default stricter sync policy:
- sync only `target_student_job`
- keep `possible_student_job` in Supabase unless user requests broader sync

Notion is for:
- review
- status changes
- notes
- prioritization
- application tracking

Notion is **not** for:
- raw scraping archives
- canonical dedupe logic
- parser history
- full raw payload storage

## Git / build priorities
Suggested milestone order:
1. repo scaffold + config
2. Supabase schema + migrations
3. LinkedIn adapter
4. classification + shortlist logic
5. Notion MCP bootstrap
6. sync engine
7. tests + docs hardening

Priorities:
1. make the data path real
2. make Notion self-bootstrapping
3. make every stage inspectable
4. keep changes localized behind clean boundaries

## Tech requirements
- Python 3.12+
- `uv`

Preferred libs:
- Scrapy
- Playwright
- `scrapy-playwright`
- Pydantic
- PyYAML
- `python-dotenv`
- `httpx` or `requests`
- Supabase/Postgres client
- Notion Python SDK
- pytest

Avoid unless clearly needed:
- Airflow
- Celery
- queues
- heavy async orchestration
- LLM dependencies in core matching

## Testing minimum
- Unit tests: normalization, student-fit, role-family, shortlist
- Parser tests: LinkedIn list/detail using fixtures if possible
- Integration-ish tests: upserts, Notion payload mapping, sync idempotency
- Smoke test: tiny end-to-end local run

## Decision order when uncertain
Choose in this order:
1. simpler architecture
2. more inspectable implementation
3. better relevance quality
4. less Notion clutter
5. future extensibility without implementing it now

Biases:
- one database + linked views > many databases
- Notion MCP > direct API when available
- clean Notion > pushing more jobs

## Definition of done
v1 is done when:
- LinkedIn-only scraping works from config-defined searches
- canonical jobs are stored in Supabase
- jobs are classified for student-fit and role-family
- shortlist logic exists
- Notion root page/database can be bootstrapped through MCP
- shortlisted jobs sync to Notion without duplication
- manual workflow fields are preserved
- docs, tests, and runnable scripts exist

If it feels like a broad job platform, it is too big.
If it feels like a narrow pipeline with a clean Notion review layer, it is correct.
