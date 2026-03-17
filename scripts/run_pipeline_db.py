#!/usr/bin/env python3
"""Run the fixture-backed pipeline against the real Supabase repository path."""

from __future__ import annotations

from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.orchestration import JobIntakePipeline, build_fixture_pipeline_inputs
from job_intake.storage import JobIntakeRepository, db_connection


def main() -> int:
    configure_logging()
    fixture_inputs = build_fixture_pipeline_inputs()

    with db_connection() as connection:
        repository = JobIntakeRepository(connection)
        pipeline = JobIntakePipeline(repository=repository)

        try:
            summary = pipeline.run_fixture_slice(
                discovery_html_by_search_name=fixture_inputs.discovery_html_by_search_name,
                detail_html_by_url=fixture_inputs.detail_html_by_url,
            )
        except Exception:
            connection.rollback()
            raise

        if summary.errors:
            connection.rollback()
        else:
            connection.commit()

    pprint(summary)
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
