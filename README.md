# Student Job Intake

Student Job Intake is a narrow, inspectable Python pipeline for discovering student-compatible LinkedIn jobs in selected German cities, storing canonical data in Supabase, and syncing only shortlisted jobs into Notion.

This repository currently contains the project foundation only:
- Python 3.12 + `uv` package scaffold
- typed settings and config loading
- Supabase migration baseline
- storage helpers and repository stubs
- Notion integration placeholders
- offline smoke check and starter tests

The product framing lives in:
- [`AGENTS.md`](/Volumes/T7/job_intake/AGENTS.md)
- [`PRD_v1.md`](/Volumes/T7/job_intake/PRD_v1.md)
- [`architecture.md`](/Volumes/T7/job_intake/architecture.md)

## Getting Started

### 1. Install Python and uv
Use Python 3.12+ and install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
```

### 2. Create local environment variables
Copy the example file and fill in the secrets you already have:

```bash
cp .env.local.example .env.local
```

Required later for real storage or sync work:
- `SUPABASE_DB_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NOTION_API_TOKEN` only if using the direct API fallback instead of Notion MCP

Optional bootstrap IDs you can fill once the Notion workspace exists:
- `NOTION_PARENT_PAGE_ID`
- `NOTION_ROOT_PAGE_ID`
- `NOTION_DATABASE_ID`

### 3. Install dependencies

```bash
uv sync --group dev
```

### 4. Run the smoke check
The smoke path is offline-first and does not require live LinkedIn, Notion, or database access.

```bash
uv run python scripts/smoke_check.py
```

### 5. Run tests

```bash
uv run pytest
```

### 6. Link the fixed Supabase project
This repo is pinned to a single Supabase project:
- project ref: `aashdnhoiqqdhpdedaab`
- project URL: `https://aashdnhoiqqdhpdedaab.supabase.co`

When you are ready for CLI-backed schema work:

```bash
supabase link --project-ref aashdnhoiqqdhpdedaab
```

If the remote schema may have changed before you add later migrations, pull first:

```bash
supabase db pull
```

## Local Commands

Bootstrap and setup check:

```bash
uv run python scripts/bootstrap_local.py
```

Lint:

```bash
uv run ruff check .
```

Type-check:

```bash
uv run mypy src tests
```

## Repository Layout

```text
configs/                  YAML search and keyword rules
scripts/                  local bootstrap and smoke entrypoints
src/job_intake/           package source
supabase/migrations/      SQL migration baseline
tests/                    offline unit and smoke tests
```

## Current Scope Boundary

This foundation intentionally does not implement:
- LinkedIn scraping logic
- classification heuristics beyond config scaffolding
- shortlist policy execution
- live Notion bootstrap or sync behavior

Those phases come next, on top of the interfaces defined here.

