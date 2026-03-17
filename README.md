# Student Job Intake

Student Job Intake is a narrow Python pipeline for discovering student-compatible LinkedIn jobs in selected German cities, storing canonical data in Supabase, and syncing only shortlisted jobs into Notion.

The project now includes:
- typed settings and validated YAML config loading
- config-driven LinkedIn search definitions
- fixture-tested LinkedIn discovery and detail parsers
- canonical job normalization and stable dedupe keys
- deterministic student-fit, role-family, and shortlist logic
- repository helpers for canonical storage records
- schema-aware Notion bootstrap and idempotent sync helpers
- a fixture-backed pipeline entrypoint for local end-to-end verification

The binding product constraints live in:
- [`AGENTS.md`](/Volumes/T7/job_intake/AGENTS.md)
- [`PRD_v1.md`](/Volumes/T7/job_intake/PRD_v1.md)
- [`architecture.md`](/Volumes/T7/job_intake/architecture.md)

## Getting Started

### 1. Install Python and `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
```

### 2. Create local environment variables

```bash
cp .env.local.example .env.local
```

Needed for live storage or direct Notion API fallback work:
- `SUPABASE_DB_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NOTION_API_TOKEN` only when not using an MCP-backed Notion client

Optional IDs once the Notion workspace exists:
- `NOTION_PARENT_PAGE_ID`
- `NOTION_ROOT_PAGE_ID`
- `NOTION_DATABASE_ID`

### 3. Install dependencies

```bash
uv sync --group dev
```

## Local Commands

Bootstrap and setup check:

```bash
uv run python scripts/bootstrap_local.py
```

Offline smoke check:

```bash
uv run python scripts/smoke_check.py
```

Fixture-backed pipeline slice:

```bash
uv run python scripts/run_pipeline.py
```

Fixture-backed pipeline slice through the real Supabase repository path:

```bash
uv run python scripts/run_pipeline_db.py
```

Inspect the latest DB-backed pipeline state:

```bash
uv run python scripts/inspect_pipeline_db.py
```

Inspect only recent pipeline runs:

```bash
uv run python scripts/inspect_pipeline_db.py --section pipeline_runs --limit 3
```

Preview historical discovery linkage backfill:

```bash
uv run python scripts/backfill_job_discoveries.py
```

Apply the backfill:

```bash
uv run python scripts/backfill_job_discoveries.py --apply
```

Run live LinkedIn public search discovery for the configured searches:

```bash
uv run python scripts/run_live_discovery.py
```

Limit the first live pass to a smaller number of executable searches:

```bash
uv run python scripts/run_live_discovery.py --limit-searches 3
```

Run live LinkedIn detail fetching for unlinked discoveries:

```bash
uv run python scripts/run_live_details.py
```

Keep the first detail-fetch pass small:

```bash
uv run python scripts/run_live_details.py --limit-discoveries 10
```

Classify canonical jobs that do not yet have persisted classifications:

```bash
uv run python scripts/run_live_classification.py --limit-jobs 100
```

Sync shortlisted target jobs into the Notion shortlist database:

```bash
uv run python scripts/run_notion_sync.py --limit-jobs 100
```

## GitHub Actions Scheduler

The repo includes a single live-ingestion workflow at [`.github/workflows/live-ingestion.yml`](/Volumes/T7/job_intake/.github/workflows/live-ingestion.yml). It runs the same four-step live path used locally:

```bash
uv run python scripts/run_live_discovery.py
uv run python scripts/run_live_details.py --limit-discoveries 250
uv run python scripts/run_live_classification.py --limit-jobs 200
uv run python scripts/run_notion_sync.py --limit-jobs 100
```

Required GitHub Actions secret:
- `SUPABASE_DB_URL`
- `NOTION_API_TOKEN`
- `NOTION_DATABASE_ID`

Manual trigger:
- open the Actions tab in GitHub
- select `Live Ingestion`
- choose `Run workflow`

Default schedule:
- weekdays at `07:00` UTC
- GitHub Actions cron uses UTC, not local time

Tests:

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
```

Type-check:

```bash
uv run mypy src tests scripts
```

## Current Runtime Shape

The implemented local flow is:

```text
load config
-> build executable LinkedIn searches
-> parse discovery fixtures
-> parse detail fixtures
-> normalize canonical jobs
-> classify student fit and role family
-> decide shortlist eligibility
-> optionally persist and sync through injected services
```

The checked-in `scripts/run_pipeline.py` path is intentionally fixture-backed so the repo stays runnable without live LinkedIn, Supabase, or Notion access. The code paths for storage and Notion sync are real, but live credentials and clients still need to be supplied by the environment/runtime.

For the DB-backed runner:
- keep using fixture HTML only; it does not fetch live LinkedIn pages
- `uv run python scripts/run_pipeline_db.py` persists through the real repository layer and does not invoke Notion sync
- `uv run python scripts/inspect_pipeline_db.py` shows the latest rows from `pipeline_runs`, `search_definitions`, `jobs`, `job_classifications`, and `job_discoveries`
- add `--section ...` to restrict the snapshot to specific tables and `--limit N` to reduce row counts
- `uv run python scripts/backfill_job_discoveries.py` previews historical `job_discoveries` rows that can be linked by search-definition name and LinkedIn external job id
- add `--apply` only when you want to persist the historical linkage updates
- `uv run python scripts/run_live_discovery.py` fetches live LinkedIn public search result pages and stores discovery rows only
- the live discovery slice does not fetch detail pages, classify jobs, shortlist, or sync to Notion by itself
- `uv run python scripts/run_live_details.py` fetches live LinkedIn job detail pages for unlinked discovery rows and upserts canonical jobs
- `uv run python scripts/run_live_classification.py` classifies canonical jobs that do not yet have `job_classifications` rows
- `uv run python scripts/run_notion_sync.py` syncs shortlisted `target_student_job` rows into the configured Notion database and records sync state in Supabase
- `SUPABASE_DB_URL` must be a full pooler DSN in `.env.local`
- `NOTION_API_TOKEN` and `NOTION_DATABASE_ID` are required for runtime Notion sync
- do not point runtime code at `supabase/.temp/pooler-url`; that file is only a local CLI clue if you need to reconstruct the pooler host
- do not use the direct host `db.aashdnhoiqqdhpdedaab.supabase.co` on this machine

## Notion Notes

- Supabase remains canonical.
- Notion is only the downstream review workspace.
- The bootstrap layer verifies the expected root page and database shape.
- Sync only manages non-manual fields and preserves `Priority`, `Review Status`, `Application Status`, and `Notes`.

## Repository Layout

```text
configs/                  YAML search and keyword rules
docs/                     runbook and implementation notes
scripts/                  bootstrap, smoke, and local pipeline entrypoints
src/job_intake/           package source
supabase/migrations/      SQL migration baseline
tests/                    unit, parser, sync, and pipeline tests
```

## Supabase Project Pin

This repo is pinned to a single Supabase project:
- project ref: `aashdnhoiqqdhpdedaab`
- project URL: `https://aashdnhoiqqdhpdedaab.supabase.co`

When doing CLI-backed schema work:

```bash
supabase link --project-ref aashdnhoiqqdhpdedaab
```

If the remote schema may have changed before a new migration:

```bash
supabase db pull
```
