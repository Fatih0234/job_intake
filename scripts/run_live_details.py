#!/usr/bin/env python3
"""Fetch live LinkedIn detail pages for unlinked discovery rows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.orchestration.live_details import LinkedInLiveDetailsRunner
from job_intake.storage.db import db_connection
from job_intake.storage.repositories import JobIntakeRepository

DEFAULT_REQUEST_DELAY_SECONDS = 0.75


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live LinkedIn detail-page fetching for unlinked discoveries.",
    )
    parser.add_argument(
        "--limit-discoveries",
        type=int,
        default=25,
        help="Limit the number of unlinked discovery rows to process.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SECONDS,
        help=(
            "Sleep between live detail requests to reduce LinkedIn throttling. "
            f"Defaults to {DEFAULT_REQUEST_DELAY_SECONDS:.2f} seconds."
        ),
    )
    args = parser.parse_args(argv)

    if args.limit_discoveries <= 0:
        parser.error("--limit-discoveries must be a positive integer.")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds must be zero or greater.")

    return args


def main() -> int:
    args = parse_args()
    configure_logging()

    with db_connection() as connection:
        repository = JobIntakeRepository(connection)
        runner = LinkedInLiveDetailsRunner(repository)

        try:
            summary = runner.run(
                limit_discoveries=args.limit_discoveries,
                request_delay_seconds=args.delay_seconds,
            )
        except Exception:
            connection.rollback()
            raise

        connection.commit()

    pprint(summary)
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
