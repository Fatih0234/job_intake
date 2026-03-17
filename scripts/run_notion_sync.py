#!/usr/bin/env python3
"""Sync shortlisted canonical jobs from Supabase into the Notion shortlist database."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.notion.bootstrap import ensure_shortlist_workspace
from job_intake.notion.client import NotionFallbackClient
from job_intake.notion.sync import NotionSyncService
from job_intake.orchestration.notion_sync_runtime import NotionShortlistSyncRunner
from job_intake.settings import get_settings
from job_intake.storage import JobIntakeRepository, db_connection


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Notion sync for shortlisted target student jobs.",
    )
    parser.add_argument(
        "--limit-jobs",
        type=int,
        default=25,
        help="Limit the number of shortlisted jobs to process.",
    )
    args = parser.parse_args(argv)
    if args.limit_jobs <= 0:
        parser.error("--limit-jobs must be a positive integer.")
    return args


def main() -> int:
    args = parse_args()
    configure_logging()
    settings = get_settings()
    database_id = settings.notion_database_id_required

    fallback_client = NotionFallbackClient(settings)
    if not fallback_client.is_configured:
        raise RuntimeError(
            "NOTION_API_TOKEN is required for runtime Notion sync.",
        )
    workspace_client = fallback_client.workspace_client()
    ensure_shortlist_workspace(workspace_client, settings)

    with db_connection() as connection:
        repository = JobIntakeRepository(connection)
        sync_service = NotionSyncService(
            workspace_client,
            database_id=database_id,
        )
        runner = NotionShortlistSyncRunner(repository, sync_service=sync_service)

        try:
            summary = runner.run(limit_jobs=args.limit_jobs)
        except Exception:
            connection.rollback()
            raise

        connection.commit()

    pprint(summary)
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
