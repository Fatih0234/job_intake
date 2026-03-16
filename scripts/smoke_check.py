#!/usr/bin/env python3
"""Run the offline smoke checks for the foundation scaffold."""

from __future__ import annotations

from pprint import pprint

from job_intake.smoke import run_smoke_check


def main() -> int:
    print("Student Job Intake smoke check")
    print("=" * 31)
    pprint(run_smoke_check())
    print("Smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

