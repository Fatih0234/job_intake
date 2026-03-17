#!/usr/bin/env python3
"""Preview or apply structured-description backfills from stored LinkedIn detail HTML."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.orchestration import DescriptionBackfillRunner, summarize_preview_rows
from job_intake.storage import JobIntakeRepository, db_connection, require_database_dsn


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill description_blocks on jobs from stored LinkedIn detail HTML.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the backfill. Without this flag the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--limit-jobs",
        type=int,
        default=100,
        help="Maximum number of jobs to preview or backfill.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Include jobs that already have description_blocks.",
    )
    args = parser.parse_args(argv)
    if args.limit_jobs <= 0:
        parser.error("--limit-jobs must be a positive integer.")
    return args


def main() -> int:
    args = parse_args()
    configure_logging()
    require_database_dsn()

    with db_connection() as connection:
        repository = JobIntakeRepository(connection)
        runner = DescriptionBackfillRunner(repository)

        preview_candidates = runner.preview_candidates(
            limit_jobs=args.limit_jobs,
            include_already_structured=args.force,
        )

        print("Description block backfill")
        print("=" * 26)
        print(f"Mode: {'apply' if args.apply else 'dry-run'}")
        pprint(
            {
                "candidate_jobs": len(preview_candidates),
                "limit_jobs": args.limit_jobs,
                "include_already_structured": args.force,
            }
        )
        print()
        print("[preview_rows]")
        pprint(summarize_preview_rows(preview_candidates))

        if not args.apply:
            connection.rollback()
            print()
            print("Dry run only. Re-run with --apply to persist these description updates.")
            return 0

        summary = runner.run(
            limit_jobs=args.limit_jobs,
            include_already_structured=args.force,
        )
        connection.commit()
        print()
        print("[applied]")
        pprint(summary)
        return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
