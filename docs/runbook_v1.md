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

5. If you want to verify the real repository path against Supabase, run the DB-backed fixture slice.

```bash
uv run python scripts/run_pipeline_db.py
```

6. Run the full test and static-check suite.

```bash
uv run pytest
uv run ruff check .
uv run mypy src tests scripts
```

Optional inspection after a DB-backed run:

```bash
uv run python scripts/inspect_pipeline_db.py
```

Target a smaller inspection when the tables grow:

```bash
uv run python scripts/inspect_pipeline_db.py --section pipeline_runs --limit 3
uv run python scripts/inspect_pipeline_db.py --section jobs --section job_discoveries --limit 5
```

Preview the historical discovery-link backfill before applying it:

```bash
uv run python scripts/backfill_job_discoveries.py
```

Apply the backfill only after reviewing the preview:

```bash
uv run python scripts/backfill_job_discoveries.py --apply
```

Run the first live LinkedIn public discovery pass:

```bash
uv run python scripts/run_live_discovery.py
```

Keep the first live pass smaller if needed:

```bash
uv run python scripts/run_live_discovery.py --limit-searches 3
```

Run live detail fetching for the newest unlinked discoveries:

```bash
uv run python scripts/run_live_details.py
```

Start with a smaller detail-fetch batch if needed:

```bash
uv run python scripts/run_live_details.py --limit-discoveries 10
```

Classify canonical jobs that do not yet have stored classifications:

```bash
uv run python scripts/run_live_classification.py --limit-jobs 100
```

Sync shortlisted target jobs into the Notion shortlist database:

```bash
uv run python scripts/run_notion_sync.py --limit-jobs 100
```

## GitHub Actions Scheduler

The live ingestion scheduler is defined in [`.github/workflows/live-ingestion.yml`](/Volumes/T7/job_intake/.github/workflows/live-ingestion.yml).

It runs this ordered sequence in one job:

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

Manual run:
- GitHub repository `Actions` tab
- select `Live Ingestion`
- click `Run workflow`

Default schedule:
- weekdays at `07:00` UTC
- GitHub cron is evaluated in UTC

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

## DB-Backed Fixture Runner Notes

- `scripts/run_pipeline_db.py` stays fixture-backed and uses the real repository layer only.
- `scripts/inspect_pipeline_db.py` is read-only and prints the latest rows written to the main canonical tables.
- `scripts/inspect_pipeline_db.py` accepts repeatable `--section` filters and a shared `--limit` override for tighter snapshots.
- `scripts/backfill_job_discoveries.py` defaults to dry-run mode and only writes historical linkage updates when `--apply` is passed.
- `scripts/run_live_discovery.py` fetches public LinkedIn search pages for the configured executable searches and inserts discovery rows only.
- The live discovery slice is acquisition-only: no detail fetches, no job upserts, no classification, and no Notion sync.
- `scripts/run_live_details.py` fetches public LinkedIn job pages for unlinked discovery rows, upserts canonical jobs, and links those discovery rows to `job_id`.
- `scripts/run_live_classification.py` classifies canonical jobs that do not yet have persisted `job_classifications` rows.
- `scripts/run_notion_sync.py` syncs shortlisted `target_student_job` rows into the configured Notion database and records sync state in Supabase.
- Set `SUPABASE_DB_URL` in `.env.local` to a full Supabase pooler DSN before running it.
- Set `NOTION_API_TOKEN` and `NOTION_DATABASE_ID` in `.env.local` before running runtime Notion sync.
- Do not use the direct host `db.aashdnhoiqqdhpdedaab.supabase.co` on this machine.
- Do not make runtime code depend on `supabase/.temp/pooler-url`; that file is only a local CLI artifact that can help you find the pooler host while configuring `.env.local`.

## Scope Guardrails

- LinkedIn guest/public jobs only
- selected German cities only
- role families limited to data engineering, analytics engineering, analytics / BI, and ML / AI engineering
- Supabase canonical, Notion downstream only
- no broad multi-platform or automation expansion in v1
