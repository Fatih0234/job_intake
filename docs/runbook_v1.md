# Student Job Intake Runbook

## Goal

Run and verify the narrow v1 pipeline locally without depending on live LinkedIn, Supabase, or Notion services by default.

## Recommended Local Sequence

1. Install dependencies.

```bash
uv sync --group dev
```

2. Validate local config and expected secrets.

```bash
uv run python scripts/bootstrap_local.py
```

3. Run the offline smoke path.

```bash
uv run python scripts/smoke_check.py
```

4. Run the fixture-backed pipeline slice.

```bash
uv run python scripts/run_pipeline.py
```

5. Run the full test and static-check suite.

```bash
uv run pytest
uv run ruff check .
uv run mypy src tests scripts
```

## What The Fixture Pipeline Exercises

- config loading
- executable search generation
- LinkedIn discovery parsing
- LinkedIn detail parsing
- canonical key generation
- deterministic classification and shortlist logic
- optional storage/sync wiring through injected dependencies

## What Still Requires Live Environment Integration

- real LinkedIn fetching instead of fixture input
- real Postgres/Supabase persistence using `SUPABASE_DB_URL`
- real Notion bootstrap/sync using an MCP-backed client or the direct API fallback

## Scope Guardrails

- LinkedIn guest/public jobs only
- selected German cities only
- role families limited to data engineering, analytics engineering, analytics / BI, and ML / AI engineering
- Supabase canonical, Notion downstream only
- no broad multi-platform or automation expansion in v1
