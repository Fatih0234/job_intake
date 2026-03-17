#!/usr/bin/env python3
"""Inspect the latest database state written by the pipeline."""

from __future__ import annotations

from pprint import pprint

from job_intake.inspection_cli import parse_inspection_args
from job_intake.logging import configure_logging
from job_intake.storage import db_connection, require_database_dsn
from job_intake.storage.inspection import load_pipeline_snapshot, select_snapshot_queries


def main() -> int:
    args = parse_inspection_args()
    configure_logging()
    require_database_dsn()
    queries = select_snapshot_queries(section_names=args.section, limit=args.limit)

    with db_connection() as connection:
        snapshot = load_pipeline_snapshot(connection, queries=queries)

    print("Student Job Intake DB snapshot")
    print("=" * 29)

    for section_name, rows in snapshot.items():
        print()
        print(f"[{section_name}]")
        pprint(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
