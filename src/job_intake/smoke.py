"""Offline smoke path for the repository foundation."""

from __future__ import annotations

from typing import Any

from job_intake.canonical import build_canonical_job_key, normalize_linkedin_job_url
from job_intake.config_loader import load_all_configs
from job_intake.orchestration import JobIntakePipeline, build_fixture_pipeline_inputs
from job_intake.search_definitions import build_executable_searches
from job_intake.settings import Settings, get_settings


def run_smoke_check(settings: Settings | None = None) -> dict[str, Any]:
    active_settings = settings or get_settings()
    configs = load_all_configs(active_settings)
    executable_searches = build_executable_searches(configs.linkedin_searches)
    pipeline = JobIntakePipeline()
    fixture_inputs = build_fixture_pipeline_inputs(active_settings)
    pipeline_summary = pipeline.run_fixture_slice(
        discovery_html_by_search_name=fixture_inputs.discovery_html_by_search_name,
        detail_html_by_url=fixture_inputs.detail_html_by_url,
    )

    fallback_url = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=1234567890"

    return {
        "settings_loaded": True,
        "configs_loaded": sorted(configs.as_dict().keys()),
        "search_definition_count": len(configs.linkedin_searches.search_definitions),
        "executable_search_count": len(executable_searches),
        "sample_search_url": executable_searches[0].search_url,
        "sample_external_key": build_canonical_job_key(external_job_id="1234567890"),
        "sample_fallback_key": build_canonical_job_key(job_url=fallback_url),
        "normalized_sample_url": normalize_linkedin_job_url(fallback_url),
        "pipeline_summary": {
            "searches": pipeline_summary.searches,
            "discoveries": pipeline_summary.discoveries,
            "details": pipeline_summary.details,
            "classified": pipeline_summary.classified,
            "shortlisted": pipeline_summary.shortlisted,
            "errors": pipeline_summary.errors,
        },
    }
