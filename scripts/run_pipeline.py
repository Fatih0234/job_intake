#!/usr/bin/env python3
"""Run a fixture-backed local pipeline slice."""

from __future__ import annotations

from pprint import pprint

from job_intake.logging import configure_logging
from job_intake.orchestration import JobIntakePipeline, build_fixture_pipeline_inputs


def main() -> int:
    configure_logging()
    pipeline = JobIntakePipeline()
    fixture_inputs = build_fixture_pipeline_inputs()
    summary = pipeline.run_fixture_slice(
        discovery_html_by_search_name=fixture_inputs.discovery_html_by_search_name,
        detail_html_by_url=fixture_inputs.detail_html_by_url,
    )
    pprint(summary)
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
