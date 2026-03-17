"""CLI helpers for the DB inspection script."""

from __future__ import annotations

import argparse

from job_intake.storage.inspection import DEFAULT_SNAPSHOT_SECTION_NAMES


def parse_inspection_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect the latest pipeline-related database tables.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override the row limit used for each selected section.",
    )
    parser.add_argument(
        "--section",
        action="append",
        choices=DEFAULT_SNAPSHOT_SECTION_NAMES,
        default=None,
        help="Restrict output to one or more named sections. Repeat to include multiple sections.",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be a positive integer.")

    return args
