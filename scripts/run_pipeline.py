#!/usr/bin/env python3
"""Run a fixture-backed local pipeline slice."""

from __future__ import annotations

from pathlib import Path
from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.orchestration import JobIntakePipeline

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "linkedin"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def main() -> int:
    configure_logging()
    pipeline = JobIntakePipeline()
    first_detail_url = (
        "https://www.linkedin.com/jobs/view/4185654374/"
        "?trk=public_jobs_jserp-result_search-card"
    )
    summary = pipeline.run_fixture_slice(
        discovery_html_by_search_name={
            "berlin_data_engineering_student": read_fixture("list_search_results.html"),
        },
        detail_html_by_url={
            first_detail_url: read_fixture("job_detail.html"),
            "https://www.linkedin.com/jobs/view/4185654375/": read_fixture(
                "job_detail_missing_optional_fields.html"
            ),
        },
    )
    pprint(summary)
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
