#!/usr/bin/env python3
"""Run live LinkedIn public search discovery against configured searches."""

from __future__ import annotations

import argparse
from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.orchestration.live_discovery import LinkedInLiveDiscoveryRunner
from job_intake.storage.db import db_connection
from job_intake.storage.repositories import JobIntakeRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live LinkedIn public search discovery for configured searches.",
    )
    parser.add_argument(
        "--limit-searches",
        type=int,
        default=None,
        help="Limit the number of executable searches to fetch.",
    )
    args = parser.parse_args()

    if args.limit_searches is not None and args.limit_searches <= 0:
        parser.error("--limit-searches must be a positive integer.")

    return args


def main() -> int:
    args = parse_args()
    configure_logging()

    with db_connection() as connection:
        repository = JobIntakeRepository(connection)
        runner = LinkedInLiveDiscoveryRunner(repository)

        try:
            summary = runner.run(limit_searches=args.limit_searches)
        except Exception:
            connection.rollback()
            raise

        connection.commit()

    pprint(summary)
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
