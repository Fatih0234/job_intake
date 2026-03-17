#!/usr/bin/env python3
"""Classify canonical jobs in Supabase that do not yet have classifications."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.orchestration.live_classification import LinkedInLiveClassificationRunner
from job_intake.storage import JobIntakeRepository, db_connection


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run DB-backed classification for unclassified canonical jobs.",
    )
    parser.add_argument(
        "--limit-jobs",
        type=int,
        default=100,
        help="Limit the number of unclassified jobs to process.",
    )
    args = parser.parse_args(argv)
    if args.limit_jobs <= 0:
        parser.error("--limit-jobs must be a positive integer.")
    return args


def main() -> int:
    args = parse_args()
    configure_logging()

    with db_connection() as connection:
        repository = JobIntakeRepository(connection)
        runner = LinkedInLiveClassificationRunner(repository)

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
