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
