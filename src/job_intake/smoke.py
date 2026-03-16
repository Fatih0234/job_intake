"""Offline smoke path for the repository foundation."""

from __future__ import annotations

from typing import Any

from job_intake.canonical import build_canonical_job_key, normalize_linkedin_job_url
from job_intake.config_loader import load_all_configs
from job_intake.settings import Settings, get_settings


def run_smoke_check(settings: Settings | None = None) -> dict[str, Any]:
    active_settings = settings or get_settings()
    configs = load_all_configs(active_settings)

    fallback_url = "https://www.linkedin.com/jobs/view/1234567890/?trk=public_jobs_topcard-title"

    return {
        "settings_loaded": True,
        "configs_loaded": sorted(configs.keys()),
        "sample_external_key": build_canonical_job_key(external_job_id="1234567890"),
        "sample_fallback_key": build_canonical_job_key(job_url=fallback_url),
        "normalized_sample_url": normalize_linkedin_job_url(fallback_url),
    }

