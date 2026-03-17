#!/usr/bin/env python3
"""Preview or apply historical job discovery linkage backfills."""

from __future__ import annotations

import argparse
from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.storage import db_connection, require_database_dsn
from job_intake.storage.backfill import (
    apply_job_discovery_backfill,
    build_job_discovery_backfill_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill missing search_definition_id and job_id links on job_discoveries.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the backfill. Without this flag the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        default=10,
        help="Number of matchable rows to preview in dry-run and apply output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging()
    require_database_dsn()

    with db_connection() as connection:
        report = build_job_discovery_backfill_report(
            connection,
            preview_limit=args.preview_limit,
        )

        print("Job discovery backfill")
        print("=" * 22)
        print(f"Mode: {'apply' if args.apply else 'dry-run'}")
        pprint(
            {
                "candidate_rows": report.candidate_rows,
                "rows_missing_search_definition": report.rows_missing_search_definition,
                "rows_missing_job": report.rows_missing_job,
                "rows_matchable_search_definition": report.rows_matchable_search_definition,
                "rows_matchable_job": report.rows_matchable_job,
                "rows_unmatched_search_definition": report.rows_unmatched_search_definition,
                "rows_unmatched_job": report.rows_unmatched_job,
            },
        )
        print()
        print("[preview_rows]")
        pprint(report.preview_rows)

        if not args.apply:
            connection.rollback()
            print()
            print("Dry run only. Re-run with --apply to persist these linkage updates.")
            return 0

        result = apply_job_discovery_backfill(connection)
        connection.commit()
        print()
        print("[applied]")
        pprint(result)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
